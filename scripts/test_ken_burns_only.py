#!/usr/bin/env python3
"""单独测试 Ken Burns 生成器"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.shared_memory import SessionSharedMemory
from backend.app.providers.generated_asset_factory import GeneratedAssetFactory

test_job_id = "test_ken_burns_001"
mem = SessionSharedMemory(session_id=test_job_id, created_at=0.0)
factory = GeneratedAssetFactory(job_id=test_job_id)

print("[INFO] 开始生成 Ken Burns 视频...")
test_image_path = Path(r"D:\ai coding\emo_transfer\data\keyframes\61-aorignal.jpg")
print(f"[INFO] 输入图片存在: {test_image_path.exists()}, 路径: {test_image_path}")

result = factory.generate_ken_burns(
    shared_memory=mem,
    input_image_path=str(test_image_path),
    duration_seconds=2.0,
    motion_direction="zoom_in"
)

print(f"[INFO] 完成! asset_id={result['asset_id']}")
output_p = Path(result['storage_path'])
print(f"[INFO] 输出文件: {output_p}, 存在={output_p.exists()}")
print(f"[INFO] 文件大小: {round(output_p.stat().st_size / 1024, 1)} KB")
