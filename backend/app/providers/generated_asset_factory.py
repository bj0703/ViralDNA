from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from dotenv import load_dotenv
import requests

from backend.app.core.config import load_ffmpeg_config

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


VISUAL_SUPPLEMENT_SKILL_ROOT = Path(__file__).resolve().parents[4] / "skill生成" / "VisualSupplementSkill"
sys.path.append(str(VISUAL_SUPPLEMENT_SKILL_ROOT))
DOTENV_PATH = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(DOTENV_PATH)


def generate_unique_asset_id() -> str:
    """生成全局唯一的生成素材ID，统一用 gen_ 前缀 + uuid"""
    return f"gen_{uuid.uuid4().hex[:16]}"


class GeneratedAssetFactory:
    """统一管理所有AI生成素材的生命周期，自动入库到共享记忆asset_index"""

    def __init__(self, job_id: str, base_dir: Optional[Path] = None):
        self.job_id = job_id
        if base_dir is None:
            project_root = Path(__file__).resolve().parents[3]
            self.base_dir = project_root / "data" / job_id / "generated_assets"
        else:
            self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        config = load_ffmpeg_config()
        if config.ffmpeg_path:
            return config.ffmpeg_path
        return "ffmpeg"

    def generate_unique_asset_path(self, asset_id: str, suffix: str = ".mp4") -> Path:
        """生成绝对路径，自动保证不覆盖已有文件"""
        return self.base_dir / f"{asset_id}{suffix}"

    def register_new_asset(
        self,
        shared_memory: SessionSharedMemory,
        asset_id: str,
        media_type: str,
        storage_path: str,
        duration_seconds: float,
        tags: list,
        global_description: str = "AI generated asset",
    ) -> Dict[str, Any]:
        """生成素材自动注册到共享记忆asset_index.assets，完全兼容AssetIndexer输出格式"""
        new_asset = {
            "schema_version": "1.0",
            "asset_id": asset_id,
            "material_id": asset_id,
            "media_type": media_type,
            "storage_path": storage_path,
            "_debug_full_path": storage_path,
            "duration": duration_seconds,
            "content_type": "aigc_generated",
            "tags": tags,
            "visual_description": global_description,
            "global_description": global_description,
            "confidence": 0.8,
            "source_type": "aigc_generated",
            "segments": [
                {
                    "segment_id": f"{asset_id}_s01",
                    "start": 0.0,
                    "end": duration_seconds,
                    "duration": duration_seconds,
                    "content_type": "generated_video",
                    "subjects": ["generated"],
                    "action": "auto",
                    "scene": "general",
                    "shot_size": "medium",
                    "camera_motion": "static",
                    "motion_intensity": 0.3,
                    "visual_quality": 0.85,
                    "lighting_quality": 0.85,
                    "subject_clarity": 0.9,
                    "orientation_fit": "9:16_safe",
                    "audio_available": False,
                    "best_for_roles": ["general"],
                    "best_for_slot_types": ["generated_filler"],
                    "can_reuse_by": ["crop", "speed_up", "freeze_frame"],
                    "risks": [],
                    "confidence": 0.85
                }
            ],
            "asset_level_risks": []
        }
        shared_memory.append_to_array("asset_index", "assets", new_asset, "GeneratedAssetFactory")
        print(f"[INFO] 新生成素材已注册: asset_id={asset_id}, path={storage_path}")
        return new_asset

    def generate_text_card(
        self,
        shared_memory: SessionSharedMemory,
        text_content: str,
        background_color: str = "#1a1a2e",
        text_color: str = "#ffffff",
        font_size: int = 80,
        duration_seconds: float = 1.5,
    ) -> Dict[str, Any]:
        """纯FFmpeg drawtext滤镜生成文字卡片视频，零图片依赖"""
        asset_id = generate_unique_asset_id()
        output_path = self.generate_unique_asset_path(asset_id, ".mp4")

        cmd = [
            self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "warning",
            "-f", "lavfi",
            "-i", f"color=c={background_color}:size=1920x1080:duration={duration_seconds}:rate=30",
            "-vf",
            (
                f"drawtext=fontfile=/Windows/Fonts/simhei.ttf:fontsize={font_size}:fontcolor={text_color}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:text='{text_content}'"
            ),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(output_path.resolve()),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except Exception:
            # 兜底：Windows找不到simhei时用默认字体
            cmd_fallback = [
                self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "warning",
                "-f", "lavfi",
                "-i", f"color=c=black:size=1920x1080:duration={duration_seconds}:rate=30",
                "-vf", f"drawtext=fontsize={font_size}:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:text='generated'",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                str(output_path.resolve()),
            ]
            subprocess.run(cmd_fallback, check=True, capture_output=True, timeout=120)

        return self.register_new_asset(
            shared_memory=shared_memory,
            asset_id=asset_id,
            media_type="video",
            storage_path=str(output_path.resolve()),
            duration_seconds=duration_seconds,
            tags=["aigc", "text_card", "generated"],
            global_description=f"文字卡片: {text_content}"
        )

    def generate_ken_burns(
        self,
        shared_memory: SessionSharedMemory,
        input_image_path: str,
        duration_seconds: float = 2.0,
        motion_direction: str = "zoom_in",
    ) -> Dict[str, Any]:
        """Python+OpenCV 原生实现 Ken Burns 视差动效，完全可控零死锁"""
        import cv2
        import numpy as np

        asset_id = generate_unique_asset_id()
        output_path = self.generate_unique_asset_path(asset_id, ".mp4")
        fps = 30
        total_frames = int(duration_seconds * fps)
        target_w, target_h = 1920, 1080

        img = cv2.imread(str(Path(input_image_path)))
        if img is None:
            raise RuntimeError(f"无法读取输入图片: {input_image_path}")

        src_h, src_w = img.shape[:2]

        # 先把图片放大4倍，细节足够多不会糊
        img_large = cv2.resize(img, (src_w * 4, src_h * 4), interpolation=cv2.INTER_LANCZOS4)
        lh, lw = img_large.shape[:2]

        # 计算初始和结束缩放比例（从1.0倍到1.5倍）
        zoom_start = 1.0
        zoom_end = 1.5 if motion_direction == "zoom_in" else 1.0 / 1.5

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (target_w, target_h))

        for frame_idx in range(total_frames):
            progress = frame_idx / max(total_frames - 1, 1)
            t = progress
            current_zoom = zoom_start * (1 - t) + zoom_end * t

            crop_w = int(lw / current_zoom)
            crop_h = int(lh / current_zoom)

            x1 = max(0, (lw - crop_w) // 2)
            y1 = max(0, (lh - crop_h) // 2)
            x2 = x1 + crop_w
            y2 = y1 + crop_h

            crop = img_large[y1:y2, x1:x2]
            out_frame = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            writer.write(out_frame)

        writer.release()

        # 用FFmpeg快速重编码为标准h264兼容格式
        temp_intermediate = output_path.parent / f"_temp_{asset_id}.mp4"
        output_path.rename(temp_intermediate)

        cmd_encode = [
            self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(temp_intermediate),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(output_path.resolve()),
        ]
        subprocess.run(cmd_encode, check=True, capture_output=True, timeout=120)

        try:
            temp_intermediate.unlink()
        except:
            pass

        return self.register_new_asset(
            shared_memory=shared_memory,
            asset_id=asset_id,
            media_type="video",
            storage_path=str(output_path.resolve()),
            duration_seconds=duration_seconds,
            tags=["aigc", "ken_burns", "static_to_video", motion_direction],
            global_description=f"Ken Burns动效: {Path(input_image_path).name}"
        )

    def generate_ai_video_by_prompt(
        self,
        shared_memory: SessionSharedMemory,
        mode: str,
        prompt_text: str,
        slot_role: str = "general",
        duration_seconds: float = 2.0,
        reference_image_url: Optional[str] = None,
        style_name: str = "modern_film",
    ) -> Dict[str, Any]:
        """调用 VisualSupplementSkill 生成 AI 视频补充片段，完全集成到 asset_index 注册体系。
        支持5种 mode: missing_hook / image_motion / transition_clip / product_motion / slot_fill
        """
        api_key = os.environ.get("DOUBAO_I2V_API_KEY", "")
        if not api_key:
            print("[WARN] DOUBAO_I2V_API_KEY 未配置，AI视频生成直接降级返回占位资源")
            asset_id = generate_unique_asset_id()
            return {
                "asset_id": asset_id,
                "status": "degraded_no_api_key",
                "warning": "API Key 未配置，跳过实际AI生成，仅返回占位记录"
            }

        model = os.environ.get("DOUBAO_I2V_MODEL", "doubao-seedance-1-5-pro-251215")
        base_url = os.environ.get("DOUBAO_I2V_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/contents/generations")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        VALID_MODES = ["missing_hook", "image_motion", "transition_clip", "product_motion", "slot_fill"]
        if mode not in VALID_MODES:
            mode = "slot_fill"

        payload = {
            "model": model,
            "content": [{"type": "text", "text": prompt_text}]
        }
        if reference_image_url:
            payload["content"].append({
                "type": "image_url",
                "image_url": {"url": reference_image_url}
            })

        print(f"[INFO] 提交AI视频生成任务: mode={mode}, duration={duration_seconds}s")
        resp_submit = requests.post(f"{base_url}/tasks", headers=headers, json=payload, timeout=60)
        resp_submit.raise_for_status()
        submit_data = resp_submit.json()
        task_id = submit_data.get("task_id", "")
        if not task_id:
            return {"status": "failed", "error": "未返回 task_id"}

        print(f"[INFO] 轮询生成任务: task_id={task_id}")
        start_poll = time.time()
        task_result = None
        while time.time() - start_poll < 300:
            resp_status = requests.get(f"{base_url}/tasks/{task_id}", headers=headers, timeout=30)
            resp_status.raise_for_status()
            task_result = resp_status.json()
            status = task_result.get("status", "")
            if status in ["succeeded", "failed"]:
                break
            time.sleep(3)

        if not task_result or task_result.get("status") != "succeeded":
            error_msg = str(task_result.get("error_detail", "生成失败")) if task_result else "轮询超时"
            print(f"[WARN] AI视频生成失败: {error_msg}")
            return {"status": "failed", "error": error_msg}

        video_url = task_result.get("output", {}).get("video_url", "")
        if not video_url:
            return {"status": "failed", "error": "未返回生成视频URL"}

        asset_id = generate_unique_asset_id()
        output_path = self.generate_unique_asset_path(asset_id, ".mp4")
        print(f"[INFO] 开始下载生成视频到本地: {asset_id}")
        resp_download = requests.get(video_url, stream=True, timeout=120)
        resp_download.raise_for_status()
        with open(str(output_path.resolve()), "wb") as f:
            for chunk in resp_download.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[INFO] AI视频生成成功并入库: asset_id={asset_id}, path={output_path}")
        return self.register_new_asset(
            shared_memory=shared_memory,
            asset_id=asset_id,
            media_type="video",
            storage_path=str(output_path.resolve()),
            duration_seconds=duration_seconds,
            tags=["aigc", "visual_supplement", f"mode={mode}", slot_role],
            global_description=f"AI生成补全素材: mode={mode}, style={style_name}"
        )
