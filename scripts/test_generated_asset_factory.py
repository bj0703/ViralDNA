#!/usr/bin/env python3
"""
逐个测试 GeneratedAssetFactory 的每一个生成工具
覆盖测试点：
1. 唯一asset_id生成
2. 文字卡片生成器 text_card
3. Ken Burns视差动效生成器
4. 生成素材自动写入asset_index共享记忆
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.shared_memory import SessionSharedMemory
from backend.app.providers.generated_asset_factory import GeneratedAssetFactory, generate_unique_asset_id


def main():
    print("="*80)
    print("  Generated Asset Factory 逐个工具专项测试")
    print("="*80)

    # 1. 初始化测试环境
    test_job_id = "test_gen_asset_factory_001"
    mem = SessionSharedMemory(session_id=test_job_id, created_at=0.0)
    factory = GeneratedAssetFactory(job_id=test_job_id)

    print(f"\n[测试初始化] job_id={test_job_id}, 输出目录: {factory.base_dir}")

    # ===== 测试1：唯一asset_id生成 =====
    print("\n" + "="*80)
    print("  测试1: 唯一asset_id生成")
    print("="*80)
    aid1 = generate_unique_asset_id()
    aid2 = generate_unique_asset_id()
    aid3 = generate_unique_asset_id()
    print(f"  生成的asset_id #1: {aid1}")
    print(f"  生成的asset_id #2: {aid2}")
    print(f"  生成的asset_id #3: {aid3}")
    assert aid1 != aid2 != aid3, "三个asset_id必须完全不重复"
    assert aid1.startswith("gen_"), "asset_id必须以gen_开头"
    print("[OK] 测试1通过：所有asset_id格式正确，全局唯一")

    # ===== 测试2：文字卡片生成器 =====
    print("\n" + "="*80)
    print("  测试2: Text Card 文字卡片生成器")
    print("="*80)
    text_card_asset = factory.generate_text_card(
        shared_memory=mem,
        text_content="战甲自动穿戴",
        background_color="#1a1a2e",
        text_color="#ffd700",
        font_size=90,
        duration_seconds=2.0
    )
    print(f"  新生成asset_id: {text_card_asset['asset_id']}")
    print(f"  输出视频路径: {text_card_asset['storage_path']}")
    output_file = Path(text_card_asset["storage_path"])
    assert output_file.exists(), "生成的文字卡片文件必须存在"
    assert output_file.stat().st_size > 1024 * 10, "生成文件大小必须大于10KB"
    print(f"  文件大小: {round(output_file.stat().st_size / 1024, 1)} KB")
    print("[OK] 测试2通过：文字卡片视频生成成功")

    # 检查是否已经自动写入asset_index
    asset_index = mem.get("asset_index")
    print(f"\n  asset_index.assets 总数: {len(asset_index['assets'])}")
    found_in_index = any(a.get("asset_id") == text_card_asset["asset_id"] for a in asset_index["assets"])
    assert found_in_index, "生成的素材必须自动出现在asset_index中"
    print("[OK] 生成素材已自动注册写入共享记忆asset_index")

    # ===== 测试3：生成第二个文字卡片 =====
    print("\n" + "="*80)
    print("  测试3: 第二个文字卡片生成器（不同内容）")
    print("="*80)
    text_card_asset2 = factory.generate_text_card(
        shared_memory=mem,
        text_content="高燃变身时刻",
        background_color="#0a0a33",
        text_color="#ff4444",
        font_size=80,
        duration_seconds=1.5
    )
    print(f"  新生成asset_id: {text_card_asset2['asset_id']}")
    print(f"  输出视频路径: {text_card_asset2['storage_path']}")
    output_file2 = Path(text_card_asset2["storage_path"])
    assert output_file2.exists()
    asset_index = mem.get("asset_index")
    print(f"  asset_index.assets 总数现在: {len(asset_index['assets'])}")
    assert len(asset_index["assets"]) == 2, "asset_index现在必须有2个生成素材"
    print("[OK] 测试3通过：第二个文字卡片生成成功，asset_index自动追加")

    # ===== 测试4：Ken Burns视差动效生成器 =====
    print("\n" + "="*80)
    print("  测试4: Ken Burns 视差动效生成器")
    print("="*80)
    # 直接使用用户提供的关键帧图片
    test_image_path = Path(r"D:\ai coding\emo_transfer\data\keyframes\61-aorignal.jpg")
    ken_burns_asset = factory.generate_ken_burns(
        shared_memory=mem,
        input_image_path=str(test_image_path),
        duration_seconds=2.5,
        motion_direction="zoom_in"
    )
    print(f"  新生成asset_id: {ken_burns_asset['asset_id']}")
    print(f"  输出Ken Burns视频路径: {ken_burns_asset['storage_path']}")
    kb_output_file = Path(ken_burns_asset['storage_path'])
    assert kb_output_file.exists(), "生成的Ken Burns视频文件必须存在"
    print(f"  Ken Burns视频文件大小: {round(kb_output_file.stat().st_size / 1024, 1)} KB")
    asset_index = mem.get("asset_index")
    print(f"  asset_index.assets 总数现在: {len(asset_index['assets'])}")
    assert len(asset_index['assets']) == 3, "asset_index现在必须有3个生成素材"
    print("[OK] 测试4通过：Ken Burns视差动效视频生成成功，自动注册到asset_index")

    # ===== 测试5：展示最终asset_index完整内容 =====
    print("\n" + "="*80)
    print("  最终 asset_index 完整内容")
    print("="*80)
    import json
    print(json.dumps(asset_index, ensure_ascii=False, indent=2))

    print("\n" + "="*80)
    print("  [DONE] 所有 GeneratedAssetFactory 专项测试全部通过！")
    print("="*80)
    print(f"\n生成的所有视频文件位置:")
    for a in asset_index["assets"]:
        p = Path(a["storage_path"])
        print(f"  - {p.name} -> {p}")


if __name__ == "__main__":
    main()
