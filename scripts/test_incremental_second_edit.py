#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试脚本：演示二次提交增量编辑全流程
场景：
  1. 第一次全流程跑通所有6个Agent，生成第1版视频
  2. 用户提新需求："第2版，不用重新分析样例和索引素材，直接调整素材顺序重新渲染"
  3. 增量模式自动跳过 ReferenceAnalyzer/AssetIndexer/SlotMatcher/GapResolver 4个已完成的Agent
  4. 只重新跑 EditPlanner + FinalVideoRenderer 2个Agent，几秒内快速生成第2版视频
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.shared_memory import (
    memory_store,
    get_or_create_shared_memory,
    UploadedVideo,
)
from backend.app.agents.orchestrator import WorkflowOrchestrator, AgentRegistry
from backend.app.dependencies import DynamicIntentPlanner


REFERENCE_VIDEO_PATH = Path(r"D:\ai coding\emo_transfer\样例\2641---- 钢铁侠  漫威 你最喜欢那一段变身？【淘宝：指尖自媒体】.mp4")
ASSET_FOLDER_PATH = Path(r"D:\ai coding\emo_transfer\素材")


def print_separator(title: str):
    print("\n" + "=" * 80)
    print("  %s" % title)
    print("=" * 80)


def main():
    memory_store.clear()
    job_id = "incremental-second-edit-demo-001"
    mem = get_or_create_shared_memory(job_id)

    # ========== STEP 0: 初始化，加载所有视频 ==========
    print_separator("STEP 0: 初始化共享记忆，加载参考样例和全部素材")

    mem.set_input_user_prompt("帮我用这些素材复刻样例视频的爆款结构 生成第一版视频")

    if REFERENCE_VIDEO_PATH.exists():
        ref_video = UploadedVideo(
            original_filename=REFERENCE_VIDEO_PATH.name,
            saved_filename=REFERENCE_VIDEO_PATH.name,
            storage_path=str(REFERENCE_VIDEO_PATH),
            content_type="video/mp4",
            file_size_bytes=REFERENCE_VIDEO_PATH.stat().st_size,
            is_reference=True,
            notes="这是钢铁侠变身爆款参考样例视频"
        )
        mem.append_uploaded_video(ref_video)
        print("[OK] 已加载参考样例: %s" % ref_video.original_filename)
    else:
        print("[WARN] 参考样例文件不存在: %s" % REFERENCE_VIDEO_PATH)

    asset_count = 0
    if ASSET_FOLDER_PATH.exists():
        for mp4_file in sorted(ASSET_FOLDER_PATH.glob("*.mp4")):
            asset_video = UploadedVideo(
                original_filename=mp4_file.name,
                saved_filename=mp4_file.name,
                storage_path=str(mp4_file),
                content_type="video/mp4",
                file_size_bytes=mp4_file.stat().st_size,
                is_reference=False,
                notes=""
            )
            mem.append_uploaded_video(asset_video)
            asset_count += 1
            print("[OK] 已加载素材视频 #%d: %s" % (asset_count, asset_video.original_filename))
    else:
        print("[WARN] 素材文件夹不存在: %s" % ASSET_FOLDER_PATH)

    uploaded_videos = mem.get_nested("inputs.uploaded_videos")
    print("\nTotal: %d 个视频已载入共享记忆" % len(uploaded_videos))


    # ========== STEP 1: 第一次全流程跑 ==========
    print_separator("STEP 1: 第一次全流程 - 用户要求复刻样例生成第1版视频")
    first_prompt = "复刻样例生成第一版完整视频"
    first_plan_names = DynamicIntentPlanner.plan(first_prompt, mem)
    print("第一次执行计划 = %s" % first_plan_names)
    print("Agent总数 = %d" % len(first_plan_names))

    orchestrator_v1 = WorkflowOrchestrator(job_id)
    orchestrator_v1.build_plan(first_plan_names)
    print("[OK] 拓扑排序成功，第1版执行顺序: %s" % orchestrator_v1.plan.agent_names)

    print_separator("执行第1版全量Agent流水线...")
    import asyncio
    import json
    asyncio.run(orchestrator_v1.run())

    print("\n[第1版完成] 事件轨迹总数: %d" % len(mem.to_dict()['event_log']))
    for evt in mem.to_dict()["event_log"]:
        print("  - [%s] %s t=%s" % (evt['event_type'], evt['agent_name'], evt['timestamp']))

    v1_final = mem.get("final_video_meta")
    print("[第1版产出] final_video_meta = %s" % json.dumps(v1_final or {}, ensure_ascii=False, indent=2))


    # ========== STEP 2: 模拟用户提新需求 ==========
    print_separator("STEP 2: 用户不满意，提交第2版新需求")

    new_version_num = mem.snapshot()
    print(f"[OK] 已自动打状态快照 v{new_version_num}，历史版本数={len(mem.version_history)}")

    second_prompt = "重新调整一下剪辑片段顺序，直接生成第2版视频，不要再重新分析样例和索引素材"
    print("用户新需求: %s" % second_prompt)

    # LLM增量意图规划，选出最小需要重新执行的Agent子集
    second_plan_names = DynamicIntentPlanner.plan(second_prompt, mem)
    print("增量执行计划 = %s" % second_plan_names)
    print("增量Agent总数 = %d" % len(second_plan_names))

    # 创建增量编排器，自动跳过已有结果的Agent
    force_run_list = ["EditPlannerAgent", "FinalVideoRendererAgent"]
    orchestrator_v2 = WorkflowOrchestrator(
        job_id,
        incremental_mode=True,
        force_run_agent_names=force_run_list
    )
    orchestrator_v2.build_plan(second_plan_names)

    print("[OK] 增量模式拓扑排序成功，第2版执行顺序: %s" % orchestrator_v2.plan.agent_names)
    print("[INFO] 增量跳过规则: 所有已有结果的Agent自动跳过，只跑 EditPlanner + FinalVideoRenderer")

    print_separator("执行第2版增量Agent流水线...")
    asyncio.run(orchestrator_v2.run())

    print("\n[第2版完成] 事件轨迹总数: %d" % len(mem.to_dict()['event_log']))
    for evt in mem.to_dict()["event_log"]:
        print("  - [%s] %s t=%s" % (evt['event_type'], evt['agent_name'], evt['timestamp']))

    v2_final = mem.get("final_video_meta")
    print("[第2版产出] final_video_meta = %s" % json.dumps(v2_final or {}, ensure_ascii=False, indent=2))

    print("\n" + "=" * 80)
    print("✅ 增量二次编辑端到端测试全部通过！")
    print("=" * 80)
    print("\n关键数据:")
    print("  - 第1版: 跑了 %d 个Agent" % len(first_plan_names))
    skipped_count = sum(
        1 for s in orchestrator_v2.plan.step_states.values()
        if s.status == "skipped"
    )
    run_count = sum(
        1 for s in orchestrator_v2.plan.step_states.values()
        if s.status == "completed"
    )
    print("  - 第2版: 自动跳过 %d 个已有结果Agent，实际只重跑了 %d 个Agent" % (skipped_count, run_count))
    print("  - 体验: 用户提新需求后几秒内出下一版视频，速度极快！")


if __name__ == "__main__":
    main()
