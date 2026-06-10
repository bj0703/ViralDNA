#!/usr/bin/env python3
"""测试完整版 Ken Burns 视差放大动效"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.shared_memory import SessionSharedMemory
from backend.app.providers.generated_asset_factory import GeneratedAssetFactory

job_id = "test_real_ken_burns_001"
mem = SessionSharedMemory(session_id=job_id, created_at=0.0)
factory = GeneratedAssetFactory(job_id=job_id)

print("[INFO] 开始生成 3秒 Ken Burns 放大动效视频...")
img_path = Path(r"D:\ai coding\emo_transfer\data\keyframes\61-aorignal.jpg")
result = factory.generate_ken_burns(
    shared_memory=mem,
    input_image_path=str(img_path),
    duration_seconds=3.0,
    motion_direction="zoom_in"
)

print(f"[OK] 完成! asset_id={result['asset_id']}")
out_p = Path(result['storage_path'])
print(f"[OK] 输出文件: {out_p}")
print(f"[OK] 文件大小: {round(out_p.stat().st_size / 1024, 1)} KB")
print("[DONE] 打开视频可以看到从 1x 平滑放大到 2.2x 的完整 Ken Burns 视差运动效果")
