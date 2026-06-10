from __future__ import annotations
import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.shared_memory import (
    SessionSharedMemory,
    StepStatus, JobStatus, EventType, AgentDependencyUnsatisfiedError
)
from backend.app.core.shared_memory_redis import get_or_create_shared_memory_redis
from backend.app.utils.orchestration_debug_logger import (
    create_run_directory,
    dump_json,
    install_agent_logging,
    install_shared_memory_logging,
    LOGS_ROOT,
)


@dataclass
class AgentRegistration:
    agent_name: str
    reads: List[str]
    writes: List[str]
    optional_reads: List[str] = field(default_factory=list)
    factory: Optional[Callable[[], BaseAgent]] = None


@dataclass
class AgentStepState:
    agent_name: str
    status: str = StepStatus.PENDING.value
    error_msg: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0


@dataclass
class ExecutionPlan:
    job_id: str
    agent_names: List[str]
    step_states: Dict[str, AgentStepState] = field(default_factory=dict)
    overall_status: str = JobStatus.QUEUED.value


class AgentRegistry:
    _agents: Dict[str, AgentRegistration] = {}

    @classmethod
    def register(cls, reg: AgentRegistration):
        cls._agents[reg.agent_name] = reg

    @classmethod
    def get(cls, name: str) -> Optional[AgentRegistration]:
        return cls._agents.get(name)

    @classmethod
    def list_all(cls) -> List[str]:
        return list(cls._agents.keys())


class WorkflowOrchestrator:
    _MAX_STREAM_CHARS = 320
    _MAX_RESULT_PREVIEW_LINES = 6
    _MAX_RESULT_PREVIEW_CHARS = 480

    def __init__(self, job_id: str, incremental_mode: bool = False, force_run_agent_names: List[str] = None):
        self.job_id = job_id
        self.shared_memory = get_or_create_shared_memory_redis(job_id)
        self.plan: ExecutionPlan = ExecutionPlan(
            job_id=job_id,
            agent_names=[]
        )
        self.incremental_mode = incremental_mode
        self.force_run_set = set(force_run_agent_names or [])
        # 不在__init__阶段创建任何目录，避免产生大量空垃圾目录
        self.run_dir = None

    def _check_dependency_satisfied(self, agent_name: str, shared_memory: SessionSharedMemory) -> bool:
        """检查Agent的所有read_keys依赖是否在共享记忆中已就绪，支持嵌套key路径"""
        reg = AgentRegistry.get(agent_name)
        if not reg:
            return False
        for read_key in reg.reads:
            val = shared_memory.get_nested(read_key)
            if val is None:
                return False
        return True

    def _should_skip_agent(self, agent_name: str) -> bool:
        """增量模式下检查是否可以直接跳过该Agent：所有write_keys都已存在且非空"""
        if agent_name in self.force_run_set:
            # 用户强制指定必须重跑，绝对不跳过
            return False
        if not self.incremental_mode:
            return False
        reg = AgentRegistry.get(agent_name)
        if not reg:
            return False
        for write_key in reg.writes:
            val = self.shared_memory.get_nested(write_key)
            if val is None:
                return False
        return True

    def _resolve_dependency_order(self, agent_names: List[str]) -> List[str]:
        """
        升级版拓扑排序：不检查运行时内存状态，只根据Agent之间的写/读声明推导先后顺序
        策略：B Agent的read_keys里有任意一个key被 A Agent的write_keys包含 → A必须排在B前面
        """
        name_to_reg = {}
        for name in agent_names:
            reg = AgentRegistry.get(name)
            if reg:
                name_to_reg[name] = reg

        adj: Dict[str, List[str]] = {name: [] for name in agent_names}
        in_degree: Dict[str, int] = {name: 0 for name in agent_names}

        for a_idx, a_name in enumerate(agent_names):
            if a_name not in name_to_reg:
                continue
            a_write_keys = set(name_to_reg[a_name].writes)
            for b_idx in range(a_idx + 1, len(agent_names)):
                b_name = agent_names[b_idx]
                if b_name not in name_to_reg:
                    continue
                b_read_keys = set(name_to_reg[b_name].reads)
                overlap = a_write_keys & b_read_keys
                if overlap:
                    if b_name not in adj[a_name]:
                        adj[a_name].append(b_name)
                        in_degree[b_name] += 1

        from collections import deque
        q = deque([name for name in agent_names if in_degree[name] == 0 and name in name_to_reg])
        sorted_names = []
        while q:
            cur = q.popleft()
            sorted_names.append(cur)
            for neighbor in adj[cur]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    q.append(neighbor)

        for name in agent_names:
            if name not in sorted_names and name in name_to_reg:
                sorted_names.append(name)

        return sorted_names

    def build_plan(self, agent_names: List[str]) -> ExecutionPlan:
        sorted_names = self._resolve_dependency_order(agent_names)
        self.plan.agent_names = sorted_names
        self.plan.step_states = {
            name: AgentStepState(agent_name=name)
            for name in sorted_names
        }
        self.plan.overall_status = JobStatus.PLANNING.value
        # 构建完执行计划立刻广播plan_ready事件，前端收到后动态生成对应数量Agent节点
        self.shared_memory.append_event("plan_ready", "", {
            "selected_agent_names": sorted_names
        })
        print(f"[INFO] 执行计划构建完成，广播plan_ready事件: selected_agent_names={sorted_names}")

        # 只有当执行计划非空（真的要跑完整Pipeline），才创建日志目录和注入装饰器
        if sorted_names and not self.run_dir:
            self.run_dir = create_run_directory(LOGS_ROOT)
            print(f"[DEBUG-LOG] 结构化调试日志目录已创建: {self.run_dir}")
            self.shared_memory = install_shared_memory_logging(self.shared_memory, self.run_dir)
            install_agent_logging(self.run_dir)
            print(f"[DEBUG-LOG] 调试日志装饰器已注入完成")
        return self.plan

    @staticmethod
    def _stringify_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        try:
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            return str(result)

    @classmethod
    def _build_result_preview(cls, result: Any) -> str:
        text = cls._stringify_result(result)
        if not text:
            return ""

        lines = text.splitlines()
        preview = "\n".join(lines[:cls._MAX_RESULT_PREVIEW_LINES])
        if len(lines) > cls._MAX_RESULT_PREVIEW_LINES or len(preview) > cls._MAX_RESULT_PREVIEW_CHARS:
            preview = preview[:cls._MAX_RESULT_PREVIEW_CHARS].rstrip()
            preview = f"{preview}\n..."
        return preview

    def _emit_result_deltas(self, agent_name: str, result_text: str, chunk_size: int = 48) -> None:
        if not result_text:
            return
        for start in range(0, len(result_text), chunk_size):
            chunk = result_text[start:start + chunk_size]
            self.shared_memory.append_event(EventType.STEP_DELTA.value, agent_name, {
                "delta": chunk,
            })

    async def run(self):
        """
        用asyncio.to_thread包装同步阻塞代码，避免阻塞FastAPI事件循环
        支持增量跳过模式
        """
        self.plan.overall_status = JobStatus.RUNNING.value

        for agent_name in self.plan.agent_names:
            step_state = self.plan.step_states[agent_name]

            # 增量模式跳过检测
            if self._should_skip_agent(agent_name):
                step_state.status = StepStatus.SKIPPED.value
                step_state.started_at = time.time()
                step_state.finished_at = time.time()
                self.shared_memory.append_event(EventType.STEP_SKIP.value, agent_name, {
                    "reason": "already_cached_incremental"
                })
                print(f"[INFO] 增量跳过Agent: {agent_name}, 结果已存在无需重跑")
                continue

            step_state.status = StepStatus.RUNNING.value
            step_state.started_at = time.time()

            reg = AgentRegistry.get(agent_name)
            self.shared_memory.append_event(EventType.STEP_START.value, agent_name, {
                "message": f"{agent_name} started",
            })

            should_run = True
            for required_read in reg.reads if reg else []:
                if self.shared_memory.get_nested(required_read) is None:
                    if required_read not in (reg.optional_reads if reg else []):
                        step_state.status = StepStatus.BLOCKED.value
                        step_state.error_msg = f"Missing required key: {required_read}"
                        step_state.finished_at = time.time()
                        self.shared_memory.append_event(EventType.STEP_FAIL.value, agent_name, {
                            "reason": "blocked_by_missing_key",
                            "key": required_read
                        })
                        should_run = False
                        break

            if should_run and reg and reg.factory:
                try:
                    agent_instance: BaseAgent = await asyncio.to_thread(reg.factory)
                    emitted_stream_text = False
                    streamed_chars = 0
                    stream_truncated = False

                    def _handle_agent_delta(delta: str) -> None:
                        nonlocal emitted_stream_text, streamed_chars, stream_truncated
                        if not delta:
                            return
                        if stream_truncated:
                            return

                        remaining = self._MAX_STREAM_CHARS - streamed_chars
                        if remaining <= 0:
                            stream_truncated = True
                            self.shared_memory.append_event(EventType.STEP_PHASE.value, agent_name, {
                                "phase": "observation",
                                "title": "继续执行中",
                                "detail": "中间文本过长，后续细节已省略，当前仅保留执行阶段提示。",
                            })
                            return

                        allowed_delta = delta[:remaining]
                        if allowed_delta:
                            emitted_stream_text = True
                            streamed_chars += len(allowed_delta)
                            self.shared_memory.append_event(EventType.STEP_DELTA.value, agent_name, {
                                "delta": allowed_delta,
                            })

                        if len(delta) > remaining:
                            stream_truncated = True
                            self.shared_memory.append_event(EventType.STEP_PHASE.value, agent_name, {
                                "phase": "observation",
                                "title": "继续执行中",
                                "detail": "中间文本过长，后续细节已省略，当前仅保留执行阶段提示。",
                            })

                    def _handle_agent_event(event_type: str, payload: Dict[str, Any]) -> None:
                        self.shared_memory.append_event(event_type, agent_name, payload)

                    agent_instance.set_stream_callback(_handle_agent_delta)
                    agent_instance.set_event_callback(_handle_agent_event)
                    result = await asyncio.to_thread(agent_instance.analyze, self.shared_memory)
                    result_text = self._stringify_result(result)
                    result_preview = self._build_result_preview(result)

                    for write_key in agent_instance.write_keys:
                        if "." not in write_key:
                            self.shared_memory.set(write_key, result, agent_name)

                    step_state.status = StepStatus.COMPLETED.value
                    if not emitted_stream_text:
                        self._emit_result_deltas(agent_name, self._build_result_preview(result_text))
                    self.shared_memory.append_event(EventType.STEP_WRITE.value, agent_name, {
                        "result_preview": result_preview,
                        "result_text": result_preview,
                        "result_type": type(result).__name__,
                        "result_truncated": result_preview != result_text,
                    })
                except Exception as e:
                    step_state.status = StepStatus.FAILED.value
                    step_state.error_msg = str(e)
                    self.shared_memory.append_event(EventType.STEP_FAIL.value, agent_name, {"error": str(e)})

            step_state.finished_at = time.time()

        all_completed = all(s.status in [StepStatus.COMPLETED.value] for s in self.plan.step_states.values())
        any_partial = any(s.status in [StepStatus.COMPLETED.value, StepStatus.SKIPPED.value, StepStatus.BLOCKED.value] for s in self.plan.step_states.values())

        if all_completed:
            self.plan.overall_status = JobStatus.COMPLETED.value
        elif any_partial:
            self.plan.overall_status = JobStatus.PARTIAL.value
        else:
            self.plan.overall_status = JobStatus.FAILED.value

        # 最终落盘：和旧的 debug 目录结构保持 100% 一致
        if self.run_dir:
            final_snapshot = self.shared_memory.to_dict()
            for top_key in ["reference_analysis", "asset_index", "slot_matches", "resolved_gaps", "generated_assets", "edit_timeline", "final_video_meta"]:
                val = final_snapshot.get(top_key)
                if val is not None:
                    dump_json(self.run_dir / f"{top_key}.json", val)

            dump_json(self.run_dir / "plan.json", {
                "job_id": self.plan.job_id,
                "agent_names": self.plan.agent_names,
                "overall_status": self.plan.overall_status,
            })
            dump_json(self.run_dir / "final_status.json", {
                "job_id": self.plan.job_id,
                "overall_status": self.plan.overall_status,
                "step_states": {n: asdict(s) for n, s in self.plan.step_states.items()},
                "final_snapshot_keys": list(final_snapshot.keys()),
            })
            print(f"[DEBUG-LOG] 全部调试文件已落盘到: {self.run_dir}")

        return self.plan

    def get_status(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "version": self.shared_memory.version,
            "overall_status": self.plan.overall_status,
            "step_states": {
                name: asdict(state)
                for name, state in self.plan.step_states.items()
            },
            "shared_memory": self.shared_memory.to_dict()
        }
