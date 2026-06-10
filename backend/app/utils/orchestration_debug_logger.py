from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_ROOT = PROJECT_ROOT / "logs"


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def capture_shared_memory_snapshot(memory: SessionSharedMemory) -> Dict[str, Any]:
    return memory.to_dict()


def create_run_directory(logs_root: Path = LOGS_ROOT) -> Path:
    now = datetime.now()
    run_id = f"agent_orchestration_debug_{now.strftime('%Y%m%d_%H%M%S')}"
    run_dir = logs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def setup_log_tee(run_dir: Path) -> Path:
    log_path = run_dir / "run.log"
    log_path.touch(exist_ok=True)
    return log_path


def install_shared_memory_logging(
    shared_memory: SessionSharedMemory,
    run_dir: Path,
) -> SessionSharedMemory:
    state_dir = run_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    original_set = shared_memory.set
    original_append_to_array = shared_memory.append_to_array
    original_snapshot = shared_memory.snapshot

    def logging_set(
        key: str,
        data: Any,
        produced_by: str = "",
        confidence: float = 0.75,
        source_refs: Any = None,
    ) -> None:
        original_set(key, data, produced_by, confidence, source_refs)
        dump_json(state_dir / f"{key}.json", shared_memory.get(key))
        dump_json(state_dir / "shared_memory_latest.json", shared_memory.to_dict())

    def logging_append_to_array(
        key: str,
        array_path: str,
        item: Any,
        agent_name: str = "",
    ) -> None:
        original_append_to_array(key, array_path, item, agent_name)
        dump_json(state_dir / f"{key}.json", shared_memory.get(key))
        dump_json(state_dir / "shared_memory_latest.json", shared_memory.to_dict())

    def logging_snapshot() -> int:
        version = original_snapshot()
        dump_json(state_dir / f"shared_memory_snapshot_v{version}.json", shared_memory.to_dict())
        return version

    shared_memory.set = logging_set
    shared_memory.append_to_array = logging_append_to_array
    shared_memory.snapshot = logging_snapshot

    dump_json(state_dir / "shared_memory_initial.json", shared_memory.to_dict())
    return shared_memory


def install_agent_logging(run_dir: Path) -> None:
    # 延迟导入：彻底打破 orchestrator 循环依赖
    if not run_dir:
        # 目录为空时直接跳过，不修改Agent注册表，避免产生空垃圾目录
        return
    from backend.app.agents.orchestrator import AgentRegistry
    agent_log_dir = run_dir / "agents"
    agent_log_dir.mkdir(parents=True, exist_ok=True)

    for agent_name, registration in list(AgentRegistry._agents.items()):
        original_factory = registration.factory
        if original_factory is None:
            continue

        def make_factory_wrapper(
            current_agent_name: str,
            current_registration: Any,
            wrapped_factory: Any,
        ):
            def factory():
                agent_instance = wrapped_factory()
                if getattr(agent_instance, "_debug_logging_wrapped", False):
                    return agent_instance

                original_analyze = agent_instance.analyze

                def wrapped_analyze(memory: Any) -> Dict[str, Any]:
                    dependency_inputs = {}
                    all_reads = list(current_registration.reads) + list(current_registration.optional_reads)
                    for read_key in all_reads:
                        val = memory.get_nested(read_key)
                        if val is not None:
                            dependency_inputs[read_key] = val

                    dump_json(agent_log_dir / f"{current_agent_name}_inputs.json", dependency_inputs)
                    dump_json(agent_log_dir / f"{current_agent_name}_memory_before.json", memory.to_dict())

                    result = original_analyze(memory)

                    dump_json(agent_log_dir / f"{current_agent_name}_result.json", result)
                    dump_json(agent_log_dir / f"{current_agent_name}_memory_after.json", memory.to_dict())

                    write_results = {
                        write_key: memory.get_nested(write_key)
                        for write_key in current_registration.writes
                    }
                    dump_json(agent_log_dir / f"{current_agent_name}_writes.json", write_results)
                    return result

                agent_instance.analyze = wrapped_analyze
                agent_instance._debug_logging_wrapped = True
                return agent_instance

            return factory

        registration.factory = make_factory_wrapper(agent_name, registration, original_factory)
