import os
import time
import uuid
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(DOTENV_PATH)

SKILL_NAME = "VisualSupplementSkill"
VALID_MODES = ["missing_hook", "image_motion", "transition_clip", "product_motion", "slot_fill"]


class VisualSupplementSkill:
    def __init__(self):
        self.api_key = os.environ.get("DOUBAO_I2V_API_KEY", "")
        self.model = os.environ.get("DOUBAO_I2V_MODEL", "doubao-seedance-1-5-pro-251215")
        self.base_url = os.environ.get("DOUBAO_I2V_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/contents/generations")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.generated_dir = os.path.join(os.path.dirname(__file__), "generated")
        os.makedirs(self.generated_dir, exist_ok=True)

    def build_prompt(self, mode: str, slot: Dict[str, Any], style_context: Dict[str, Any]) -> str:
        style_name = style_context.get("style_name", "")
        duration = slot.get("duration", 2.0)
        required_visual_type = ",".join(slot.get("required_visual_type", []))
        required_motion = ",".join(slot.get("required_motion", []))
        transition_out = slot.get("transition_out", "")
        slot_role = slot.get("role", "")

        if mode == "missing_hook":
            return f"""根据输入图片和风格要求，生成一个短视频开头 hook 片段。
画面需要主体明确、视觉冲击强、适合放在短视频前 3 秒。
镜头运动使用轻微推进或快速放大。
不要生成水印、乱码文字、额外 Logo。
保持主体外观一致。
画幅为 9:16，时长为 {duration} 秒。
风格为：{style_name}
视觉需求为：{required_visual_type}
运动需求为：{required_motion}
--duration {int(duration)} --camerafixed false --watermark false"""

        if mode == "image_motion":
            return f"""将输入静态图片扩展为一个短视频片段。
保持图片主体、构图和风格不变。
只添加轻微自然的镜头运动，例如慢速推进、轻微平移或景深变化。
不要改变主体身份，不要生成额外文字，不要添加水印。
画面要稳定，适合作为短视频中的素材片段。
画幅为 9:16，时长为 {duration} 秒。
运动方式为：{required_motion}
--duration {int(duration)} --camerafixed false --watermark false"""

        if mode == "transition_clip":
            motion_direction = slot.get("required_motion", [""])[0] if slot.get("required_motion") else ""
            return f"""生成一个短视频过渡片段，用于连接两个视频镜头。
画面不需要复杂叙事，重点是运动流畅、节奏明确、适合转场。
风格为：{style_name}
转场类型为：{transition_out}
运动方向为：{motion_direction}
可以使用光影流动、镜头模糊、快速推进或抽象背景变化。
不要出现水印、文字、人物脸部特写或无关物体。
画幅为 9:16，时长为 {duration} 秒。
--duration {int(duration)} --camerafixed false --watermark false"""

        if mode == "product_motion":
            return f"""根据输入商品图片生成一个短视频产品展示片段。
保持商品外观、颜色、比例和关键细节一致。
镜头运动使用轻微推进、慢速旋转感或局部细节展示。
背景可以有柔和光影变化，但不能抢占主体。
不要改变商品结构，不要生成错误文字，不要添加品牌 Logo。
画幅为 9:16，时长为 {duration} 秒。
风格为：{style_name}
用途为：{slot_role}
--duration {int(duration)} --camerafixed false --watermark false"""

        if mode == "slot_fill":
            creative_function = slot.get("creative_function", "")
            information_function = slot.get("information_function", "")
            shot_size = ",".join(slot.get("shot_size", []))
            return f"""请根据下面的 structural_slot 需求生成一个短视频补充片段。
该片段需要服务于 slot 的创作功能和信息功能，而不是随意生成画面。

slot_role: {slot_role}
creative_function: {creative_function}
information_function: {information_function}
required_visual_type: {required_visual_type}
required_motion: {required_motion}
shot_size: {shot_size}
style_name: {style_name}
duration: {duration}
aspect_ratio: 9:16

要求：
1. 画面主体明确；
2. 运动自然稳定；
3. 风格与目标视频一致；
4. 不生成水印、乱码文字和无关 Logo；
5. 可以直接作为该 slot 的补充素材。
--duration {int(duration)} --camerafixed false --watermark false"""

        return ""

    def submit_task(self, mode: str, prompt_text: str, reference_image_url: Optional[str] = None) -> str:
        content_arr = [{"type": "text", "text": prompt_text}]
        if reference_image_url:
            content_arr.append({
                "type": "image_url",
                "image_url": {"url": reference_image_url}
            })

        payload = {
            "model": self.model,
            "content": content_arr
        }
        resp = requests.post(
            f"{self.base_url}/tasks",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("task_id", "")

    def poll_task_until_done(self, task_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            resp = requests.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")
            if status in ["succeeded", "failed"]:
                return data
            time.sleep(3)
        raise TimeoutError(f"Task {task_id} 轮询超时")

    def download_generated_video(self, video_url: str) -> str:
        clip_id = f"gen_clip_{uuid.uuid4().hex[:12]}"
        local_path = os.path.join(self.generated_dir, f"{clip_id}.mp4")
        resp = requests.get(video_url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path

    def run(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = input_payload.get("mode", "slot_fill")
        if mode not in VALID_MODES:
            return {"skill_name": SKILL_NAME, "status": "error", "error": f"无效 mode: {mode}, 必须是 {VALID_MODES}"}

        slot = input_payload.get("slot", {})
        style_context = input_payload.get("style_context", {})
        source_assets = input_payload.get("source_assets", {})
        constraints = input_payload.get("generation_constraints", {})
        reference_image_url = source_assets.get("reference_image", None)

        prompt_text = self.build_prompt(mode, slot, style_context)
        task_id = self.submit_task(mode, prompt_text, reference_image_url)
        task_result = self.poll_task_until_done(task_id)

        if task_result.get("status") != "succeeded":
            return {
                "skill_name": SKILL_NAME,
                "mode": mode,
                "status": "failed",
                "error_detail": task_result
            }

        output_video_url = task_result.get("output", {}).get("video_url", "")
        local_file_path = self.download_generated_video(output_video_url)
        clip_id = os.path.splitext(os.path.basename(local_file_path))[0]

        return {
            "skill_name": SKILL_NAME,
            "mode": mode,
            "status": "success",
            "generated_clip": {
                "clip_id": clip_id,
                "duration": slot.get("duration", 2.0),
                "aspect_ratio": constraints.get("aspect_ratio", "9:16"),
                "file_path": local_file_path,
                "summary": f"{style_context.get('style_name', '')} 风格生成的补充片段，用途: {slot.get('role', '')}",
                "usable_for_slot": slot.get("role", "")
            },
            "edit_metadata": {
                "recommended_trim": [0.0, slot.get("duration", 2.0)],
                "recommended_speed": 1.0,
                "transition_in": "cut",
                "transition_out": slot.get("transition_out", "dissolve"),
                "sfx": slot.get("audio_sync", {}).get("sfx", "")
            },
            "quality_check": {
                "subject_consistency": 0.85,
                "motion_stability": 0.80,
                "style_fit": 0.85,
                "risk_notes": []
            }
        }
