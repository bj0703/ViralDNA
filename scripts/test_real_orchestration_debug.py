from __future__ import annotations

import argparse
import asyncio
import atexit
import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.agents.asset_indexer import AssetIndexerAgent  # noqa: E402
from backend.app.agents.base_agent import BaseAgent  # noqa: E402
from backend.app.agents.edit_planner import EditPlannerAgent  # noqa: E402
from backend.app.agents.final_video_renderer import FinalVideoRendererAgent  # noqa: E402
from backend.app.agents.gap_resolver import GapResolverAgent  # noqa: E402
from backend.app.agents.orchestrator import (  # noqa: E402
    AgentRegistration,
    AgentRegistry,
    WorkflowOrchestrator,
)
from backend.app.agents.reference_analyzer import ReferenceAnalyzerAgent  # noqa: E402
from backend.app.agents.slot_matcher import SlotMatcherAgent  # noqa: E402
from backend.app.core.config import (  # noqa: E402
    load_ark_chat_config,
    load_ffmpeg_config,
    load_redis_config,
)
from backend.app.core.shared_memory import UploadedVideo  # noqa: E402
from backend.app.providers.ark_chat import ArkChatProvider  # noqa: E402


DEFAULT_REFERENCE_PATH = PROJECT_ROOT / "样例" / "9a0c337f1884af28cbb77d4077214039.mp4"
DEFAULT_ASSET_DIR = PROJECT_ROOT / "素材" / "缠绕的心"
DEFAULT_PROMPT = "使用参考样例的视频结构和节奏，从上传素材中匹配可用镜头，生成四个版本的剪辑方案并输出最终视频。"
DEFAULT_AGENT_NAMES = [
    "ReferenceAnalyzerAgent",
    "AssetIndexerAgent",
    "SlotMatcherAgent",
    "GapResolverAgent",
    "EditPlannerAgent",
    "FinalVideoRendererAgent",
]
DEFAULT_VARIANT_ID = "structure"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


class TeeStream:
    def __init__(self, original: Any, log_file: Any) -> None:
        self._original = original
        self._log_file = log_file
        self.encoding = getattr(original, "encoding", "utf-8")

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._original.write(data)
        self._log_file.write(data)
        return len(data)

    def flush(self) -> None:
        self._original.flush()
        self._log_file.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._original, "isatty", lambda: False)())


def restore_standard_streams() -> None:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def print_banner(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def print_json_block(title: str, payload: Any) -> None:
    print(f"[DETAIL] {title}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label}不存在: {path}")


def discover_asset_videos(asset_dir: Path) -> List[Path]:
    videos = [
        path for path in asset_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    videos.sort()
    return videos


def create_run_directory(base_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_dir / f"agent_orchestration_debug_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def setup_log_tee(run_dir: Path) -> Path:
    log_path = run_dir / "run.log"
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    atexit.register(log_file.close)
    atexit.register(restore_standard_streams)
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)
    return log_path


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def capture_shared_memory_snapshot(shared_memory: Any) -> Dict[str, Any]:
    snapshot = shared_memory.to_dict()
    entries = snapshot.get("entries", {})
    return {
        "session_id": snapshot.get("session_id"),
        "version": snapshot.get("version"),
        "inputs": snapshot.get("inputs", {}),
        "entry_keys": list(entries.keys()),
        "entries": {key: value.get("data") for key, value in entries.items()},
        "event_log_count": len(snapshot.get("event_log", [])),
    }


def collect_dependency_inputs(shared_memory: Any, key_paths: Iterable[str]) -> Dict[str, Any]:
    return {key_path: shared_memory.get_nested(key_path) for key_path in key_paths}


def parse_agent_names(raw_value: str) -> List[str]:
    names = [item.strip() for item in raw_value.split(",") if item.strip()]
    return names or list(DEFAULT_AGENT_NAMES)


def append_uploaded_videos(
    orchestrator: WorkflowOrchestrator,
    reference_path: Path,
    asset_paths: Iterable[Path],
) -> None:
    orchestrator.shared_memory.append_uploaded_video(
        UploadedVideo(
            original_filename=reference_path.name,
            saved_filename=reference_path.name,
            storage_path=str(reference_path),
            content_type="video/mp4",
            file_size_bytes=reference_path.stat().st_size,
            is_reference=True,
            notes="reference sample",
        )
    )

    for asset_path in asset_paths:
        orchestrator.shared_memory.append_uploaded_video(
            UploadedVideo(
                original_filename=asset_path.name,
                saved_filename=asset_path.name,
                storage_path=str(asset_path),
                content_type="video/mp4",
                file_size_bytes=asset_path.stat().st_size,
                is_reference=False,
                notes="material asset",
            )
        )


def wrap_shared_memory_debug(orchestrator: WorkflowOrchestrator, run_dir: Path) -> Tuple[Any, Path]:
    shared_memory = orchestrator.shared_memory
    state_dir = run_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    event_counter = {"value": 0}

    original_append_event = shared_memory.append_event
    original_set = shared_memory.set
    original_append_to_array = shared_memory.append_to_array
    original_snapshot = shared_memory.snapshot

    def logging_append_event(event_type: str, agent_name: str, payload: Dict[str, Any] = None) -> None:
        event_counter["value"] += 1
        event_id = event_counter["value"]
        payload = payload or {}
        print(f"[EVENT {event_id:03d}] type={event_type} agent={agent_name or '-'}")
        if payload:
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))
        original_append_event(event_type, agent_name, payload)

    def logging_set(
        key: str,
        data: Any,
        produced_by: str,
        confidence: float = 1.0,
        source_refs: List[str] = None,
    ) -> None:
        print(f"[MEMORY SET] key={key} produced_by={produced_by} confidence={confidence}")
        print_json_block(f"memory.set payload for {key}", data)
        original_set(key, data, produced_by, confidence, source_refs)
        print_json_block("shared_memory state after set", capture_shared_memory_snapshot(shared_memory))
        dump_json(state_dir / f"{key}.json", shared_memory.get(key))
        dump_json(state_dir / "shared_memory_latest.json", shared_memory.to_dict())

    def logging_append_to_array(key: str, array_path: str, item: Any, agent_name: str) -> None:
        print(f"[MEMORY APPEND] key={key} array_path={array_path} agent={agent_name}")
        print_json_block(f"memory.append item for {key}.{array_path}", item)
        original_append_to_array(key, array_path, item, agent_name)
        print_json_block("shared_memory state after append", capture_shared_memory_snapshot(shared_memory))
        dump_json(state_dir / f"{key}.json", shared_memory.get(key))
        dump_json(state_dir / "shared_memory_latest.json", shared_memory.to_dict())

    def logging_snapshot() -> int:
        version = original_snapshot()
        print(f"[SNAPSHOT] version={version}")
        dump_json(state_dir / f"shared_memory_snapshot_v{version}.json", shared_memory.to_dict())
        return version

    shared_memory.append_event = logging_append_event
    shared_memory.set = logging_set
    shared_memory.append_to_array = logging_append_to_array
    shared_memory.snapshot = logging_snapshot
    return shared_memory, state_dir


def install_agent_logging(run_dir: Path) -> None:
    agent_log_dir = run_dir / "agents"
    agent_log_dir.mkdir(parents=True, exist_ok=True)

    for agent_name, registration in list(AgentRegistry._agents.items()):
        original_factory = registration.factory
        if original_factory is None:
            continue

        def make_factory_wrapper(
            current_agent_name: str,
            current_registration: AgentRegistration,
            wrapped_factory: Any,
        ):
            def factory() -> BaseAgent:
                agent_instance = wrapped_factory()
                if getattr(agent_instance, "_debug_logging_wrapped", False):
                    return agent_instance

                original_analyze = agent_instance.analyze

                def wrapped_analyze(memory: Any) -> Dict[str, Any]:
                    print_banner(f"Agent 开始: {current_agent_name}")
                    dependency_inputs = collect_dependency_inputs(
                        memory,
                        list(current_registration.reads) + list(current_registration.optional_reads),
                    )
                    print_json_block(f"{current_agent_name} dependency inputs", dependency_inputs)
                    print_json_block(
                        f"{current_agent_name} shared_memory before analyze",
                        capture_shared_memory_snapshot(memory),
                    )
                    dump_json(agent_log_dir / f"{current_agent_name}_inputs.json", dependency_inputs)
                    dump_json(
                        agent_log_dir / f"{current_agent_name}_memory_before.json",
                        memory.to_dict(),
                    )

                    result = original_analyze(memory)

                    print_json_block(f"{current_agent_name} analyze result", result)
                    print_json_block(
                        f"{current_agent_name} shared_memory after analyze",
                        capture_shared_memory_snapshot(memory),
                    )
                    dump_json(agent_log_dir / f"{current_agent_name}_result.json", result)
                    dump_json(
                        agent_log_dir / f"{current_agent_name}_memory_after.json",
                        memory.to_dict(),
                    )

                    write_results = {
                        write_key: memory.get_nested(write_key)
                        for write_key in current_registration.writes
                    }
                    print_json_block(f"{current_agent_name} write key materialized values", write_results)
                    dump_json(agent_log_dir / f"{current_agent_name}_writes.json", write_results)
                    print_banner(f"Agent 结束: {current_agent_name}")
                    return result

                agent_instance.analyze = wrapped_analyze  # type: ignore[method-assign]
                agent_instance._debug_logging_wrapped = True
                return agent_instance

            return factory

        registration.factory = make_factory_wrapper(agent_name, registration, original_factory)


def summarize_final_outputs(final_video_meta: Dict[str, Any]) -> List[Tuple[str, str, bool]]:
    outputs: List[Tuple[str, str, bool]] = []
    for item in final_video_meta.get("outputs", []):
        outputs.append(
            (
                str(item.get("variant_id", "")),
                str(item.get("output_path", "")),
                bool(item.get("success", False)),
            )
        )
    return outputs


def build_runtime_dependencies() -> Dict[str, Any]:
    ark_chat_config = load_ark_chat_config()
    ffmpeg_config = load_ffmpeg_config()
    redis_config = load_redis_config()
    ark_chat_provider = ArkChatProvider(ark_chat_config)
    return {
        "ark_chat_config": ark_chat_config,
        "ffmpeg_config": ffmpeg_config,
        "redis_config": redis_config,
        "ark_chat_provider": ark_chat_provider,
    }


def describe_environment(deps: Dict[str, Any]) -> Dict[str, Any]:
    ffmpeg_config = deps["ffmpeg_config"]
    redis_config = deps["redis_config"]
    ark_chat_config = deps["ark_chat_config"]
    return {
        "ark_chat_configured": ark_chat_config.is_configured,
        "ark_base_url": ark_chat_config.base_url,
        "ark_endpoint_id": ark_chat_config.endpoint_id,
        "ffmpeg_available": ffmpeg_config.is_available,
        "ffmpeg_path": ffmpeg_config.ffmpeg_path or shutil.which("ffmpeg"),
        "redis_enabled": redis_config.redis_enabled,
        "redis_url": redis_config.redis_url,
    }


def register_runtime_agents(deps: Dict[str, Any]) -> List[str]:
    ark_chat_provider = deps["ark_chat_provider"]

    agent_instances: Dict[str, BaseAgent] = {
        "ReferenceAnalyzerAgent": ReferenceAnalyzerAgent(ark_chat_provider),
        "AssetIndexerAgent": AssetIndexerAgent(ark_chat_provider),
        "SlotMatcherAgent": SlotMatcherAgent(ark_chat_provider),
        "GapResolverAgent": GapResolverAgent(ark_chat_provider),
        "EditPlannerAgent": EditPlannerAgent(ark_chat_provider),
        "FinalVideoRendererAgent": FinalVideoRendererAgent(),
    }

    AgentRegistry._agents.clear()
    registrations = [
        AgentRegistration(
            agent_name="ReferenceAnalyzerAgent",
            reads=["inputs.uploaded_videos"],
            writes=["reference_analysis"],
            optional_reads=[],
            factory=lambda instance=agent_instances["ReferenceAnalyzerAgent"]: instance,
        ),
        AgentRegistration(
            agent_name="AssetIndexerAgent",
            reads=["inputs.uploaded_videos"],
            writes=["asset_index"],
            optional_reads=["reference_analysis"],
            factory=lambda instance=agent_instances["AssetIndexerAgent"]: instance,
        ),
        AgentRegistration(
            agent_name="SlotMatcherAgent",
            reads=["reference_analysis", "asset_index"],
            writes=["slot_matches"],
            optional_reads=[],
            factory=lambda instance=agent_instances["SlotMatcherAgent"]: instance,
        ),
        AgentRegistration(
            agent_name="GapResolverAgent",
            reads=["slot_matches", "asset_index"],
            writes=["resolved_gaps"],
            optional_reads=[],
            factory=lambda instance=agent_instances["GapResolverAgent"]: instance,
        ),
        AgentRegistration(
            agent_name="EditPlannerAgent",
            reads=["reference_analysis", "asset_index", "slot_matches", "resolved_gaps"],
            writes=["edit_timeline"],
            optional_reads=[],
            factory=lambda instance=agent_instances["EditPlannerAgent"]: instance,
        ),
        AgentRegistration(
            agent_name="FinalVideoRendererAgent",
            reads=["edit_timeline", "inputs.uploaded_videos"],
            writes=["final_video_meta"],
            optional_reads=["asset_index"],
            factory=lambda instance=agent_instances["FinalVideoRendererAgent"]: instance,
        ),
    ]
    for registration in registrations:
        AgentRegistry.register(registration)

    return list(agent_instances.keys())


def validate_requested_agents(agent_names: List[str]) -> None:
    available_agents = set(AgentRegistry.list_all())
    unknown = [name for name in agent_names if name not in available_agents]
    if unknown:
        raise ValueError(f"未知 agent: {unknown}, 可用: {sorted(available_agents)}")


async def run_debug_pipeline(
    reference_path: Path,
    asset_dir: Path,
    prompt: str,
    run_dir: Path,
    selected_agent_names: List[str],
    requested_variant_id: Optional[str],
) -> Dict[str, Any]:
    job_id = f"debug-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    asset_paths = discover_asset_videos(asset_dir)
    if not asset_paths:
        raise RuntimeError(f"素材目录内没有可用视频: {asset_dir}")

    deps = build_runtime_dependencies()
    environment = describe_environment(deps)
    registered_agents = register_runtime_agents(deps)
    validate_requested_agents(selected_agent_names)

    print_banner("环境状态")
    print_json_block("runtime environment", environment)

    print_banner("输入信息")
    print(f"job_id: {job_id}")
    print(f"reference: {reference_path}")
    print(f"asset_dir: {asset_dir}")
    print(f"asset_count: {len(asset_paths)}")
    print(f"requested_variant_id: {requested_variant_id or '(all variants)'}")
    print(f"selected_agents: {selected_agent_names}")
    for idx, asset_path in enumerate(asset_paths, start=1):
        size_mb = round(asset_path.stat().st_size / 1024 / 1024, 2)
        print(f"  [{idx:02d}] {asset_path.name} ({size_mb} MB)")

    orchestrator = WorkflowOrchestrator(job_id=job_id, incremental_mode=False)
    shared_memory, state_dir = wrap_shared_memory_debug(orchestrator, run_dir)
    shared_memory.set_input_user_prompt(prompt)
    if requested_variant_id:
        shared_memory.set_requested_variant_id(requested_variant_id)
    append_uploaded_videos(orchestrator, reference_path, asset_paths)
    dump_json(state_dir / "shared_memory_initial.json", shared_memory.to_dict())
    dump_json(run_dir / "environment.json", environment)

    print_banner("Agent 注册表")
    print(
        json.dumps(
            {
                "registered_agent_names": registered_agents,
                "registered_agent_count": len(registered_agents),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    install_agent_logging(run_dir)

    print_banner("构建执行计划")
    plan = orchestrator.build_plan(selected_agent_names)
    if not plan.agent_names:
        raise RuntimeError(
            "Execution plan is empty. None of the requested agent names were resolved in AgentRegistry. "
            f"requested={selected_agent_names}, registered={registered_agents}"
        )
    print(
        json.dumps(
            {
                "job_id": plan.job_id,
                "agent_names": plan.agent_names,
                "overall_status": plan.overall_status,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    dump_json(
        run_dir / "plan.json",
        {
            "job_id": plan.job_id,
            "agent_names": plan.agent_names,
            "overall_status": plan.overall_status,
        },
    )

    print_banner("开始执行完整 Agent 链路")
    completed_plan = await orchestrator.run()
    status = orchestrator.get_status()
    dump_json(run_dir / "final_status.json", status)
    dump_json(state_dir / "shared_memory_final.json", shared_memory.to_dict())

    print_banner("执行结果汇总")
    print(
        json.dumps(
            {
                "overall_status": completed_plan.overall_status,
                "step_states": {
                    name: {
                        "status": state.status,
                        "error_msg": state.error_msg,
                        "started_at": state.started_at,
                        "finished_at": state.finished_at,
                    }
                    for name, state in completed_plan.step_states.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    for key in [
        "reference_analysis",
        "asset_index",
        "slot_matches",
        "resolved_gaps",
        "edit_timeline",
        "final_video_meta",
    ]:
        dump_json(run_dir / f"{key}.json", shared_memory.get(key))

    final_video_meta = shared_memory.get("final_video_meta") or {}
    outputs = summarize_final_outputs(final_video_meta)
    if outputs:
        print_banner("最终视频输出")
        for variant_id, output_path, success in outputs:
            print(f"variant={variant_id:<12} success={success!s:<5} output={output_path}")

    print_banner("调试产物路径")
    print(f"log_file: {run_dir / 'run.log'}")
    print(f"plan: {run_dir / 'plan.json'}")
    print(f"status: {run_dir / 'final_status.json'}")
    print(f"state_dir: {state_dir}")

    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the backend agent orchestration pipeline with explicit agent registration and verbose logs."
    )
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE_PATH, help="参考样例视频路径")
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR, help="素材目录路径")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="写入共享记忆的用户需求")
    parser.add_argument("--log-dir", type=Path, default=PROJECT_ROOT / "logs", help="日志根目录")
    parser.add_argument(
        "--agents",
        default=",".join(DEFAULT_AGENT_NAMES),
        help="逗号分隔的 agent 名称列表",
    )
    parser.add_argument(
        "--variant",
        default=DEFAULT_VARIANT_ID,
        help="只渲染指定版本；传空字符串表示渲染全部版本",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_exists(args.reference, "参考样例")
    ensure_exists(args.asset_dir, "素材目录")

    requested_variant_id = args.variant.strip() or None
    selected_agent_names = parse_agent_names(args.agents)

    run_dir = create_run_directory(args.log_dir)
    log_path = setup_log_tee(run_dir)
    print(f"[BOOT] Full orchestration debug log: {log_path}")

    status = asyncio.run(
        run_debug_pipeline(
            reference_path=args.reference,
            asset_dir=args.asset_dir,
            prompt=args.prompt,
            run_dir=run_dir,
            selected_agent_names=selected_agent_names,
            requested_variant_id=requested_variant_id,
        )
    )
    print(f"[DONE] orchestration overall_status={status['overall_status']}")


if __name__ == "__main__":
    main()
