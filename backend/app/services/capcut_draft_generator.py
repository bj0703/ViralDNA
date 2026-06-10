from __future__ import annotations

import os
import sys
import uuid
import time
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("CapCutDraftGeneratorService")

VECTCUT_ROOT_PATH = Path(__file__).parent.parent.parent.parent / "VectCutAPI"
logger.info(f"[CAPCUT_INIT] 尝试添加 VectCutAPI 路径到 sys.path: {VECTCUT_ROOT_PATH}")
sys.path.append(str(VECTCUT_ROOT_PATH))
logger.info(f"[CAPCUT_INIT] sys.path 已更新，当前长度: {len(sys.path)}")


TRANSITION_MAP: Dict[str, Any] = {
    "cut": None,
    "dissolve": None,
    "fade": None,
    "fade_in": None,
    "fade_out": None,
    "blur": None,
    "zoom": None,
    "mask_reveal": None,
    "flash_black": None,
    "overlay": None,
}


class CapCutDraftGeneratorService:
    """将 edit_timeline 转换成完整可导入剪映/CapCut的草稿文件夹适配器。
    直接本地调用 pyJianYingDraft 库，无需HTTP跨进程。
    """

    def __init__(self, vectcut_root: Optional[str] = None):
        logger.info("[CAPCUT_INIT] CapCutDraftGeneratorService 初始化开始")
        if vectcut_root:
            self._vectcut_root = Path(vectcut_root)
            logger.info(f"[CAPCUT_INIT] 使用传入的 vectcut_root: {vectcut_root}")
        else:
            self._vectcut_root = VECTCUT_ROOT_PATH
            logger.info(f"[CAPCUT_INIT] 使用默认 vectcut_root: {self._vectcut_root}")
        
        self._template_dir = self._vectcut_root / "template_jianying"
        logger.info(f"[CAPCUT_INIT] 检查模板目录1: {self._template_dir}, 存在? {self._template_dir.exists()}")
        if not self._template_dir.exists():
            self._template_dir = self._vectcut_root / "template"
            logger.info(f"[CAPCUT_INIT] 回退模板目录2: {self._template_dir}, 存在? {self._template_dir.exists()}")
        
        if not self._template_dir.exists():
            logger.warning(f"[CAPCUT_INIT] 警告：所有候选模板目录都不存在，后续duplicate_as_template可能失败")
        
        logger.info("[CAPCUT_INIT] CapCutDraftGeneratorService 初始化完成")
        self._assets_base: Dict[str, Any] = {}

    def _calc_9_16_center_crop(self, src_w: int, src_h: int) -> Tuple[float, float, float, float]:
        """从 16:9 源视频居中裁剪成 9:16 竖屏。
        返回 (scale_x, scale_y, offset_x, offset_y)
        """
        logger.debug(f"[CAPCUT_CROP] 计算居中裁剪 src_w={src_w}, src_h={src_h}")
        target_ratio = 9.0 / 16.0
        src_ratio = src_w / max(src_h, 1)
        if src_ratio > target_ratio:
            crop_w = int(src_h * target_ratio)
            crop_h = src_h
            scale_x = src_w / crop_w
            scale_y = 1.0
            offset_x = (1.0 - 1.0 / scale_x) * 0.5
            offset_y = 0.0
        else:
            crop_w = src_w
            crop_h = int(src_w / target_ratio)
            scale_x = 1.0
            scale_y = src_h / crop_h
            offset_x = 0.0
            offset_y = (1.0 - 1.0 / scale_y) * 0.5
        result = (scale_x, scale_y, offset_x, offset_y)
        logger.debug(f"[CAPCUT_CROP] 裁剪结果: scale_x={scale_x:.4f}, scale_y={scale_y:.4f}, offset_x={offset_x:.4f}, offset_y={offset_y:.4f}")
        return result

    def _calc_16_9_pad(self, src_w: int, src_h: int) -> Tuple[float, float, float, float]:
        """将任意比例的源视频等比缩放到 16:9 横板画布内，不足的地方填充黑边。
        画布尺寸假设为 1920x1080。
        返回 (scale_x, scale_y, offset_x, offset_y)
        """
        logger.debug(f"[CAPCUT_PAD] 计算16:9填充黑边 src_w={src_w}, src_h={src_h}")
        canvas_w, canvas_h = 1920, 1080
        target_ratio = 16.0 / 9.0
        src_ratio = src_w / max(src_h, 1)

        scale = min(canvas_w / src_w, canvas_h / src_h)
        scale_x = scale
        scale_y = scale

        scaled_w = src_w * scale
        scaled_h = src_h * scale

        if src_ratio > target_ratio:
            offset_x = 0.0
            offset_y = (1.0 - scaled_h / canvas_h) * 0.5
        elif src_ratio < target_ratio:
            offset_x = (1.0 - scaled_w / canvas_w) * 0.5
            offset_y = 0.0
        else:
            offset_x = 0.0
            offset_y = 0.0

        result = (scale_x, scale_y, offset_x, offset_y)
        logger.debug(f"[CAPCUT_PAD] 填充黑边结果: scale_x={scale_x:.4f}, scale_y={scale_y:.4f}, offset_x={offset_x:.4f}, offset_y={offset_y:.4f}")
        return result

    def _normalize_transition(self, name: str):
        logger.debug(f"[CAPCUT_TRANSITION] 归一化转场名称: {name}")
        from pyJianYingDraft.metadata.transition_meta import Transition_type
        TRANSITION_MAP_LOCAL: Dict[str, Any] = {
            "cut": Transition_type.none if hasattr(Transition_type, 'none') else Transition_type.__members__.get('none', None),
            "dissolve": Transition_type.dissolve,
            "fade": Transition_type.dissolve,
            "fade_in": Transition_type.fade_white,
            "fade_out": Transition_type.fade_white,
            "blur": Transition_type.blur,
            "zoom": Transition_type.zoom,
            "mask_reveal": Transition_type.mask,
            "flash_black": Transition_type.flash,
            "overlay": Transition_type.overlay,
        }
        name_lower = str(name).lower().strip()
        result = TRANSITION_MAP_LOCAL.get(name_lower)
        final_result = result if result is not None else Transition_type.__members__.get('none', None)
        logger.debug(f"[CAPCUT_TRANSITION] 映射结果: {final_result}")
        return final_result

    def generate_draft_from_timeline(
        self,
        edit_timeline: Dict[str, Any],
        variant_id: str = "structure",
        output_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        主入口：接收 EditPlannerAgent 输出的 edit_timeline，生成完整剪映草稿。
        
        :param edit_timeline: EditPlannerAgent 输出结果
        :param variant_id: 使用哪个变体版本，默认 structure
        :param output_root: 草稿输出根目录，默认在 VectCutAPI 下
        :return: 生成结果，包含 draft_id、draft_folder、draft_path
        """
        logger.info("[CAPCUT_MAIN] 剪映草稿生成流程开始")
        logger.info(f"[CAPCUT_MAIN] 输入参数: variant_id={variant_id}, output_root={output_root}")
        logger.info(f"[CAPCUT_MAIN] edit_timeline 类型: {type(edit_timeline)}, 顶层keys: {list(edit_timeline.keys()) if isinstance(edit_timeline, dict) else '非dict'}")

        try:
            import pyJianYingDraft as draft
            logger.info("[CAPCUT_MAIN] pyJianYingDraft 库导入成功")
        except Exception as e:
            logger.error(f"[CAPCUT_MAIN] pyJianYingDraft 库导入失败! 异常栈:\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": f"pyJianYingDraft 库导入失败: {str(e)}",
                "draft_id": None,
                "draft_folder": None,
                "draft_path": None,
            }

        variant_data: Dict[str, Any] = {}
        if "timeline" in edit_timeline:
            variant_data = edit_timeline
            logger.info("[CAPCUT_MAIN] edit_timeline直接包含timeline字段，使用顶层作为variant_data")
        else:
            variants = edit_timeline.get("variants", {})
            logger.info(f"[CAPCUT_MAIN] 找到variants字典，包含keys: {list(variants.keys())}")
            variant_data = variants.get(variant_id, {})
            if not variant_data:
                logger.warning(f"[CAPCUT_MAIN] 未找到指定variant_id={variant_id}，尝试遍历查找第一个包含timeline的变体")
                for v in variants.values():
                    if isinstance(v, dict) and v.get("timeline"):
                        variant_data = v
                        logger.info(f"[CAPCUT_MAIN] 找到备选变体，timeline长度={len(variant_data.get('timeline', []))}")
                        break

        timeline = variant_data.get("timeline", []) if isinstance(variant_data.get("timeline"), list) else []
        logger.info(f"[CAPCUT_MAIN] 解析得到timeline长度: {len(timeline)}")
        if not timeline:
            logger.error("[CAPCUT_MAIN] timeline为空，直接返回失败")
            return {
                "success": False,
                "error": "timeline 为空，无法生成草稿",
                "draft_id": None,
                "draft_folder": None,
                "draft_path": None,
            }

        timeline_meta = variant_data.get("timeline_meta", {}) if isinstance(variant_data.get("timeline_meta"), dict) else {}
        width = int(timeline_meta.get("resolution", "1080x1920").split("x")[0])
        height = int(timeline_meta.get("resolution", "1080x1920").split("x")[1])
        total_duration_sec = float(timeline_meta.get("duration", 15.0))
        logger.info(f"[CAPCUT_MAIN] 分辨率: {width}x{height}, 总时长: {total_duration_sec}秒")

        draft_id = f"dfd_emo_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        logger.info(f"[CAPCUT_MAIN] 生成草稿ID: {draft_id}")

        if output_root:
            output_dir = Path(output_root) / draft_id
        else:
            output_dir = self._vectcut_root / draft_id
        logger.info(f"[CAPCUT_MAIN] 草稿输出目录: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[CAPCUT_MAIN] 输出目录创建完成，存在? {output_dir.exists()}")

        assets_dir = output_dir / "assets" / "video"
        assets_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[CAPCUT_MAIN] 素材目录创建完成: {assets_dir}")

        logger.info(f"[CAPCUT_MAIN] 开始创建 Script_file 对象 width={width}, height={height}")
        script = draft.Script_file(width, height)
        logger.info(f"[CAPCUT_MAIN] Script_file 创建完成")

        logger.info(f"[CAPCUT_MAIN] 开始实例化 Draft_folder, vectcut_root={self._vectcut_root}")
        draft_folder = draft.Draft_folder(str(self._vectcut_root))
        logger.info(f"[CAPCUT_MAIN] 开始复制模板 draft_id={draft_id}, template_dir={self._template_dir}")
        draft_folder.duplicate_as_template(str(self._template_dir), draft_id)
        logger.info(f"[CAPCUT_MAIN] 模板复制完成")

        added_material_ids: List[str] = []

        for idx, clip in enumerate(timeline):
            if not isinstance(clip, dict):
                logger.warning(f"[CAPCUT_CLIP] 第{idx}个clip不是dict类型，跳过")
                continue

            clip_id = clip.get("clip_id", f"clip_{idx+1:03d}")
            asset_full_path = str(clip.get("asset_full_path", ""))
            logger.info(f"[CAPCUT_CLIP] 处理第{idx+1}/{len(timeline)}个clip, clip_id={clip_id}, asset_path={asset_full_path}")
            
            if not asset_full_path or not os.path.exists(asset_full_path):
                logger.warning(f"[CAPCUT_CLIP] 素材路径不存在，跳过: asset_full_path={asset_full_path}, exists={os.path.exists(asset_full_path)}")
                continue

            source_in_sec = float(clip.get("source_in", 0.0) or 0.0)
            source_out_sec = float(clip.get("source_out", 3.0) or 3.0)
            target_start_sec = float(clip.get("start", 0.0) or 0.0)
            target_end_sec = float(clip.get("end", target_start_sec + (source_out_sec - source_in_sec)) or 0.0)
            speed = float((clip.get("transform", {}) if isinstance(clip.get("transform"), dict) else {}).get("speed", 1.0) or 1.0)
            transition_out = str(clip.get("transition_out", "cut"))
            logger.debug(f"[CAPCUT_CLIP] 时间参数: source_in={source_in_sec}, source_out={source_out_sec}, target_start={target_start_sec}, target_end={target_end_sec}, speed={speed}, transition={transition_out}")

            material_name = Path(asset_full_path).name
            material_id = f"vid_{idx+1:03d}_{Path(material_name).stem}"
            logger.debug(f"[CAPCUT_CLIP] material_name={material_name}, material_id={material_id}")

            script.add_material(
                draft.Video_segment,
                material_id,
                local_file_path=asset_full_path,
            )
            logger.info(f"[CAPCUT_CLIP] 素材添加到script完成: material_id={material_id}")
            added_material_ids.append(material_id)

            source_duration_us = int((source_out_sec - source_in_sec) * 1_000_000)
            target_duration_us = int((target_end_sec - target_start_sec) * 1_000_000)
            video_seg = draft.Video_segment(
                material_id,
                source_timerange=draft.Timerange(
                    int(source_in_sec * 1_000_000),
                    source_duration_us,
                ),
                target_timerange=draft.Timerange(
                    int(target_start_sec * 1_000_000),
                    target_duration_us,
                ),
                speed=draft.Speed(speed),
            )
            logger.debug(f"[CAPCUT_CLIP] Video_segment 实例化完成")

            transform = clip.get("transform", {}) if isinstance(clip.get("transform"), dict) else {}
            crop_mode = str(transform.get("crop", "16:9_pad"))
            logger.debug(f"[CAPCUT_CLIP] crop_mode={crop_mode}")
            if crop_mode == "9:16_center":
                scale_x, scale_y, offset_x, offset_y = self._calc_9_16_center_crop(width, height)
                video_seg.set_scale(scale_x, scale_y)
                video_seg.set_transform(offset_x, offset_y)
            elif crop_mode == "16:9_pad":
                scale_x, scale_y, offset_x, offset_y = self._calc_16_9_pad(width, height)
                video_seg.set_scale(scale_x, scale_y)
                video_seg.set_transform(offset_x, offset_y)

            if idx > 0 and transition_out != "cut":
                prev_seg_idx = len(script.tracks["video_main"].segments) - 1
                if prev_seg_idx >= 0:
                    logger.info(f"[CAPCUT_CLIP] 添加转场 transition_out={transition_out}")
                    transition_obj = draft.Transition(
                        self._normalize_transition(transition_out),
                        duration=int(0.5 * 1_000_000),
                    )
                    video_seg.add_transition(transition_obj)

            script.tracks["video_main"].add_segment(video_seg)
            logger.info(f"[CAPCUT_CLIP] segment添加到video_main轨道完成")

        logger.info(f"[CAPCUT_MAIN] 全部clip处理完毕，有效添加素材数量: {len(added_material_ids)}")

        draft_info_path = output_dir / "draft_info.json"
        logger.info(f"[CAPCUT_MAIN] 开始dump Script_file到 {draft_info_path}")
        script.dump(str(draft_info_path))
        logger.info(f"[CAPCUT_MAIN] draft_info.json dump完成，文件存在? {draft_info_path.exists()}")

        final_result = {
            "success": True,
            "draft_id": draft_id,
            "draft_folder": str(output_dir),
            "draft_path": str(output_dir),
            "clip_count": len(added_material_ids),
            "material_ids": added_material_ids,
            "total_duration_sec": total_duration_sec,
            "capcut_import_tip": (
                "请将此文件夹完整复制到剪映草稿目录："
                "Windows → C:\\Users\\<用户名>\\AppData\\Local\\JianYingJianJi\\User Data\\Projects\\com.lveditor.jianying\\local_files\\"
            ),
        }
        logger.info(f"[CAPCUT_MAIN] 剪映草稿生成流程全部成功完成，最终返回结果: success=True, draft_id={draft_id}")
        return final_result
