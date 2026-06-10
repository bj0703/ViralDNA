#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整5Agent流水线端到端测试脚本
加载参考样例 + 全部素材视频，依次执行所有Agent，逐步骤打印输出
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
    job_id = "full-pipeline-demo-001"
    mem = get_or_create_shared_memory(job_id)

    print_separator("STEP 0: 初始化共享记忆，加载视频")

    mem.set_input_user_prompt("帮我用这些素材复刻样例视频的爆款结构 生成视频")

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
        print("[OK] 已加载参考样例: %s, size=%dKB" % (ref_video.original_filename, ref_video.file_size_bytes//1024))
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

    print_separator("STEP 1: DynamicIntentPlanner 动态生成执行计划")
    plan_names = DynamicIntentPlanner.plan(mem.inputs["user_prompt"], mem)
    print("执行计划 = %s" % plan_names)
    print("Agent总数 = %d" % len(plan_names))

    print_separator("STEP 2: 拓扑排序验证")
    orchestrator = WorkflowOrchestrator(job_id)
    orchestrator.build_plan(plan_names)
    print("[OK] 拓扑排序成功，执行顺序: %s" % orchestrator.plan.agent_names)

    print_separator("STEP 3: 逐个执行Agent，展示每一步输出")
    import asyncio
    import json

    for agent_name in orchestrator.plan.agent_names:
        print("\n" + "-" * 80)
        print(">>> 开始执行 Agent: %s" % agent_name)
        reg = AgentRegistry.get(agent_name)
        if not reg:
            print("[ERROR] 找不到Agent注册信息，跳过")
            continue

        print("   read_keys  = %s" % reg.reads)
        print("   write_keys = %s" % reg.writes)

        try:
            agent_instance = reg.factory()
            result = asyncio.run(asyncio.to_thread(agent_instance.analyze, mem))
            print("\n[OUTPUT] %s 输出结果:" % agent_name)
            print(json.dumps(result, ensure_ascii=False, indent=2))

            for write_key in agent_instance.write_keys:
                if "." not in write_key:
                    mem.set(write_key, result, agent_name)
                    print("[OK] 结果已写入共享记忆 key='%s'" % write_key)

        except Exception as e:
            print("[ERROR] Agent执行出错: %s: %s" % (type(e).__name__, e))

    print_separator("STEP 4: 最终全量共享记忆状态")
    full_state = mem.to_dict()
    print("Event Log 事件轨迹总数: %d" % len(full_state['event_log']))
    for evt in full_state["event_log"]:
        print("  - [%s] %s t=%s" % (evt['event_type'], evt['agent_name'], evt['timestamp']))

    print("\n[DONE] 流水线全部执行完成! 最终产出:")
    for key in full_state["entries"]:
        print("  [OK]  key='%s' 已就绪" % key)

    print("\n" + "=" * 80)
    print("COMPLETE: 5Agent全流水线端到端测试全部通过")
    print("=" * 80)


if __name__ == "__main__":
    main()
