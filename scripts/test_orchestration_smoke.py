"""
动态Agent编排器冒烟测试
验证共享记忆、事件日志、编排器注册等所有核心契约
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

# 关键：显式导入这两个模块，触发所有 Agent 注册代码执行
import backend.app.agents.downstream_contracts
import backend.app.dependencies

from backend.app.agents.orchestrator import WorkflowOrchestrator, AgentRegistry
from backend.app.core.shared_memory import (
    SessionSharedMemory, MemoryEntryMeta, get_or_create_shared_memory,
    StepStatus, JobStatus
)


def test_shared_memory_basics():
    """测试共享记忆的基础读写"""
    print("→ 测试 1: 共享记忆基础读写 ...")
    mem = SessionSharedMemory(session_id="test-session-001", created_at=0.0)
    mem.set("reference_analysis", {"test": 1}, "test_agent")
    data = mem.get("reference_analysis")
    assert data is not None
    assert data.get("test") == 1
    print("  ✓ 通过")


def test_event_log_append_only():
    """测试 append-only 事件日志"""
    print("→ 测试 2: Append-Only 事件日志 ...")
    mem = SessionSharedMemory(session_id="test-session-002", created_at=0.0)
    mem.append_event("step_start", "TestAgentA", {"detail": "开始执行"})
    mem.append_event("step_write", "TestAgentA", {"detail": "写入结果"})
    assert len(mem.event_log) == 2
    assert mem.event_log[0].event_type == "step_start"
    print("  ✓ 通过")


def test_agent_registry_list():
    """测试Agent注册表"""
    print("→ 测试 3: Agent 注册表 ...")
    all_agents = AgentRegistry.list_all()
    print(f"  已注册Agent数量: {len(all_agents)}")
    print(f"  Agent列表: {all_agents}")
    assert len(all_agents) >= 5
    print("  ✓ 通过")


def test_orchestrator_build_plan():
    """测试编排器构建执行计划"""
    print("→ 测试 4: 编排器构建执行计划 ...")
    orchestrator = WorkflowOrchestrator(job_id="test-job-001")
    plan = orchestrator.build_plan(["ReferenceAnalyzerAgent", "AssetAnalyzerAgent"])
    assert len(plan.agent_names) >= 1
    print(f"  计划生成成功，Agent顺序: {plan.agent_names}")
    print("  ✓ 通过")


async def test_full_orchestration_flow():
    """完整异步编排流程测试"""
    print("→ 测试 5: 完整异步编排流程 ...")
    orchestrator = WorkflowOrchestrator(job_id="async-test-001")
    orchestrator.build_plan(["ReferenceAnalyzerAgent"])
    await orchestrator.run()
    status = orchestrator.get_status()
    assert status["overall_status"] != JobStatus.QUEUED.value
    print(f"  最终状态: {status['overall_status']}")
    print("  ✓ 通过")


def main():
    print("=" * 60)
    print("  爆款结构迁移引擎 - 编排器冒烟测试套件")
    print("=" * 60)
    
    test_shared_memory_basics()
    test_event_log_append_only()
    test_agent_registry_list()
    test_orchestrator_build_plan()
    asyncio.run(test_full_orchestration_flow())
    
    print("\n" + "=" * 60)
    print("  ✅ 所有冒烟测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    main()
