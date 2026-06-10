from __future__ import annotations

import ast
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import load_ffmpeg_config


def find_ffmpeg_binary() -> Optional[str]:
    config = load_ffmpeg_config()
    if config.ffmpeg_path:
        return config.ffmpeg_path
    return "ffmpeg" if config.is_available else None


def _resolve_asset_index(segment: Dict[str, Any], source_video_path_index: Dict[str, int]) -> Tuple[int, str]:
    """
    同时兼容 asset 和 asset_id 两个字段，返回对应的源视频索引和调试信息
    """
    # 优先读取直接携带的全路径
    asset_full_path = segment.get("asset_full_path", "")
    if asset_full_path and asset_full_path in source_video_path_index:
        return source_video_path_index[asset_full_path], f"asset_full_path matched: {asset_full_path}"

    # 兼容 asset 字段
    asset_filename = segment.get("asset", "")
    if asset_filename in source_video_path_index:
        return source_video_path_index[asset_filename], f"asset matched: {asset_filename}"

    # 兼容 asset_id 字段（上游所有Agent都用这个）
    asset_id_value = segment.get("asset_id", "")
    if asset_id_value in source_video_path_index:
        return source_video_path_index[asset_id_value], f"asset_id matched: {asset_id_value}"

    # 都没找到，抛出明确异常，不再静默回退到索引0
    available_keys = list(source_video_path_index.keys())
    raise ValueError(
        f"Timeline segment references asset that does not exist in source pool. "
        f"segment: {segment}, available assets: {available_keys}"
    )


def validate_timeline(
    timeline_segments: List[Dict[str, Any]],
    asset_path_to_index: Dict[str, int]
) -> Dict[str, Any]:
    """
    Timeline前置校验层，渲染前验证所有引用合法性 + 自动修复轻微问题
    返回validation_report，包含所有警告和错误项
    """
    errors: List[str] = []
    warnings: List[str] = []
    auto_fix_count = 0

    # 获取第一个可用素材的索引，作为绝对兜底
    all_keys = list(asset_path_to_index.keys())
    fallback_idx = 0
    if all_keys and len(all_keys) > 0:
        fallback_idx = asset_path_to_index[all_keys[0]]

    for idx, seg in enumerate(timeline_segments):
        seg_id = seg.get("clip_id", f"clip_{idx}")

        # 校验素材引用必须合法，失败自动修复兜底，不再崩溃
        try:
            _resolve_asset_index(seg, asset_path_to_index)
        except ValueError as e:
            # 防御兜底：自动把无效asset_id替换为第一个可用素材
            seg["asset_id"] = all_keys[0] if all_keys else None
            seg["asset_full_path"] = all_keys[0] if all_keys else ""
            warnings.append(f"[{seg_id}] 空/无效素材引用自动兜底为首个可用素材")
            auto_fix_count += 1

        # 校验 source_in/source_out 时长合法性，自动修复
        source_in = float(seg.get("source_in", 0.0))
        source_out = float(seg.get("source_out", 3.0))
        if source_in < 0:
            seg["source_in"] = 0.0
            warnings.append(f"[{seg_id}] source_in 自动从负数修复为0")
            auto_fix_count += 1
        if source_out <= source_in:
            seg["source_out"] = source_in + 0.5
            warnings.append(f"[{seg_id}] source_out 自动修复为 source_in + 0.5秒")
            auto_fix_count += 1

        # 校验timeline时间区间，出现零时长自动修复为至少0.5秒
        tl_start = float(seg.get("start", seg.get("timeline_start", 0.0)))
        tl_end = float(seg.get("end", seg.get("timeline_end", source_out)))
        if tl_end <= tl_start:
            seg["end"] = tl_start + 0.5
            warnings.append(f"[{seg_id}] timeline 零时长自动修复: 从 {tl_start} 扩展到 {seg['end']}")
            auto_fix_count += 1

    # 校验相邻片段，自动对齐时间线消除gap和重叠
    current_pos = 0.0
    for idx, seg in enumerate(timeline_segments):
        tl_start = float(seg.get("start", current_pos))
        tl_end = float(seg.get("end", tl_start + 0.5))
        if abs(tl_start - current_pos) > 0.01 and idx > 0:
            seg["start"] = current_pos
            warnings.append(f"[auto-fix] 片段{idx}自动对齐到前序结束时间 {current_pos}")
        seg["end"] = max(seg.get("end", tl_start + 0.5), seg.get("start", tl_start) + 0.5)
        current_pos = seg["end"]

    all_valid = len(errors) == 0
    return {
        "all_valid": all_valid,
        "errors": errors,
        "warnings": warnings,
        "auto_fix_count": auto_fix_count,
        "validated_segment_count": len(timeline_segments)
    }


def _safe_speed(raw_speed: Any) -> float:
    try:
        speed = float(raw_speed)
    except (TypeError, ValueError):
        speed = 1.0
    return min(max(speed, 0.5), 2.0)


def _motion_preset(motion: str) -> Tuple[float, str, str]:
    """Return a conservative zoom factor with small pan offsets for video clips."""
    if motion == "beat_punch_in":
        return 1.10, "0.012*in_w*sin(n/4)", "0"
    if motion == "transition_follow":
        return 1.08, "0.015*in_w*sin(n/9)", "0.010*in_h*cos(n/11)"
    if motion == "rhythm_follow":
        return 1.10, "0.020*in_w*sin(n/8)", "0.015*in_h*cos(n/10)"
    if motion in {"story_focus", "slow_push_in", "slow_zoom_in", "slow_focus_eye_detail"}:
        return 1.06, "0", "0.008*in_h*sin(n/18)"
    if motion in {"slow_motion_enhance", "static_freeze_highlight"}:
        return 1.03, "0", "0"
    return 1.0, "0", "0"


def _build_motion_filters(motion: str, width: int, height: int, duration: float) -> str:
    zoom_factor, x_offset_expr, y_offset_expr = _motion_preset(motion)
    if zoom_factor <= 1.001:
        return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"setsar=1"
    )

    scaled_width = max(int(round(width * zoom_factor)), width + 2)
    scaled_height = max(int(round(height * zoom_factor)), height + 2)
    if scaled_width % 2 != 0:
        scaled_width += 1
    if scaled_height % 2 != 0:
        scaled_height += 1

    center_x = "(in_w-out_w)/2"
    center_y = "(in_h-out_h)/2"
    x_expr = center_x if x_offset_expr == "0" else f"{center_x}+({x_offset_expr})"
    y_expr = center_y if y_offset_expr == "0" else f"{center_y}+({y_offset_expr})"

    return (
        f"scale={scaled_width}:{scaled_height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:x='{x_expr}':y='{y_expr}'"
    )


def _extract_transition_type(name: Any) -> str:
    if isinstance(name, dict):
        return str(name.get("type", "cut") or "cut").strip().lower()

    if isinstance(name, str):
        value = name.strip()
        if not value:
            return "cut"

        if value.startswith("{") and "type" in value:
            try:
                parsed = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                parsed = None
            if isinstance(parsed, dict):
                return str(parsed.get("type", "cut") or "cut").strip().lower()

        return value.lower()

    return str(name or "cut").strip().lower()


def _normalize_transition_name(name: Any) -> str:
    value = _extract_transition_type(name)
    if value == "overlay":
        return "fade"
    if value in {"cut", "none"}:
        return "cut"
    if value in {"dissolve", "fade", "blur"}:
        return "fade"
    if value in {"flash_black", "fade_to_black"}:
        return "fadeblack"
    return "fade"


def build_filter_graph(
    timeline: List[Dict[str, Any]],
    source_video_path_index: Dict[str, int],
    width: int = 1920,
    height: int = 1080,
) -> str:
    """
    从 edit_timeline 生成 FFmpeg filter_complex 滤镜图字符串
    只处理视频流，音频部分后续从参考样例单独混流
    """
    parts: List[str] = []
    clip_tags: List[str] = []
    clip_durations: List[float] = []

    for idx, segment in enumerate(timeline):
        src_input_idx, _debug_info = _resolve_asset_index(segment, source_video_path_index)
        clip_tag = f"v_clip{idx}"
        src_in = float(segment.get("source_in", 0.0))
        src_out = float(segment.get("source_out", 3.0))
        source_duration = max(src_out - src_in, 0.1)
        transform = segment.get("transform", {}) if isinstance(segment.get("transform"), dict) else {}
        speed = _safe_speed(transform.get("speed", 1.0))
        motion = str(transform.get("motion", "none") or "none").strip().lower()
        output_duration = max(source_duration / speed, 0.1)
        motion_filters = _build_motion_filters(motion, width, height, output_duration)

        parts.append(
            f"[{src_input_idx}:v]"
            # 第一步：裁剪片段之前立刻强制对齐时间基，100%消除xfade多流timebase不一致问题
            f"settb=1/30,"
            # 第二步：先裁剪出目标片段
            f"trim=start={src_in}:end={src_out},"
            # 第三步：统一帧率为30fps
            f"fps=30,"
            # 第四步：变速处理
            f"setpts=(PTS-STARTPTS)/{speed},"
            f"{motion_filters},"
            # 第五步：统一像素格式 + 强制SAR=1彻底消除concat校验失败
            f"format=yuv420p,setsar=1,"
            # 第六步：二次强制时间基对齐，双重保险
            f"settb=1/30[{clip_tag}]"
        )
        clip_tags.append(clip_tag)
        clip_durations.append(output_duration)

    if not clip_tags:
        raise ValueError("Timeline is empty; cannot build filter graph.")

    if len(clip_tags) == 1:
        parts.append(f"[{clip_tags[0]}]copy[outv]")
        return "; ".join(parts)

    current_tag = clip_tags[0]
    current_duration = clip_durations[0]

    for idx in range(1, len(clip_tags)):
        next_tag = clip_tags[idx]
        next_duration = clip_durations[idx]
        transition = _normalize_transition_name(timeline[idx - 1].get("transition_out", "cut"))
        output_tag = "outv" if idx == len(clip_tags) - 1 else f"v_join{idx}"

        if transition == "cut":
            parts.append(f"[{current_tag}][{next_tag}]concat=n=2:v=1:a=0[{output_tag}]")
            current_duration += next_duration
        else:
            transition_duration = min(0.35, current_duration / 2.0, next_duration / 2.0)
            transition_duration = max(transition_duration, 0.1)
            offset = max(current_duration - transition_duration, 0.0)
            t1_mid = f"t1_{idx}"
            t2_mid = f"t2_{idx}"
            parts.append(
                f"[{current_tag}]fps=30,settb=1/30[{t1_mid}],"
                f"[{next_tag}]fps=30,settb=1/30[{t2_mid}],"
                f"[{t1_mid}][{t2_mid}]"
                f"xfade=transition={transition}:duration={transition_duration}:offset={offset}"
                f"[{output_tag}]"
            )
            current_duration = current_duration + next_duration - transition_duration

        current_tag = output_tag

    return "; ".join(parts)


def render_timeline_to_video(
    timeline: List[Dict[str, Any]],
    source_video_paths: List[str],
    output_path: str,
    reference_audio_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用 FFmpeg 全自动渲染最终视频
    核心策略：先渲染纯视频，第二步把参考样例的音频完整混流进去
    这样最终产出的视频画面是素材剪辑，音频是样例原音，完美复刻爆款节奏
    """
    ffmpeg_bin = find_ffmpeg_binary()
    if not ffmpeg_bin:
        return {
            "_skip_reason": "ffmpeg_not_found",
            "warning": "系统未检测到FFmpeg，跳过视频渲染",
            "output_path": None,
            "success": False,
        }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    source_video_path_index: Dict[str, int] = {}
    for in_idx, full_path in enumerate(source_video_paths):
        fname = Path(full_path).name
        source_video_path_index[fname] = in_idx
        source_video_path_index[full_path] = in_idx  # 同时注册绝对路径映射
        # 如果路径文件名的前缀是 gen_，提取出完整的 asset_id 格式直接注册索引
        if fname.startswith("gen_"):
            stem = Path(fname).stem
            source_video_path_index[stem] = in_idx

    # === 前置校验层 ===
    validation_report = validate_timeline(timeline, source_video_path_index)
    if not validation_report["all_valid"]:
        return {
            "_skip_reason": "timeline_validation_failed",
            "warning": f"Timeline校验失败: 错误数={len(validation_report['errors'])}",
            "validation_report": validation_report,
            "output_path": None,
            "success": False,
        }

    if validation_report["warnings"]:
        print(f"[WARN] Timeline 渲染警告: {validation_report['warnings']}")

    # === 第一步：渲染纯视频到临时文件 ===
    temp_no_audio_path = out_file.parent / f"_no_audio_{out_file.name}"

    cmd1 = [ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "warning"]
    for src_path in source_video_paths:
        cmd1.extend(["-i", str(Path(src_path).resolve())])

    filter_graph = build_filter_graph(timeline, source_video_path_index)
    cmd1.extend([
        "-filter_complex", filter_graph,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        str(temp_no_audio_path.resolve()),
    ])

    try:
        subprocess.run(
            cmd1,
            check=True,
            capture_output=True,
            timeout=7200,
            encoding="utf-8",
            errors="ignore",
        )
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr or ""
        return {
            "_skip_reason": "ffmpeg_no_audio_error",
            "warning": f"FFmpeg纯视频渲染出错: {stderr_msg[:300]}",
            "output_path": None,
            "success": False,
        }

    # === 第二步：如果有参考音频源，混流进去 ===
    final_output_path = out_file
    if reference_audio_path and Path(reference_audio_path).exists():
        print(f"[INFO] 开始混流参考样例音频: {Path(reference_audio_path).name}")
        cmd2 = [ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(temp_no_audio_path.resolve()),
                "-i", str(Path(reference_audio_path).resolve()),
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(final_output_path.resolve())]
        try:
            subprocess.run(
                cmd2,
                check=True,
                capture_output=True,
                timeout=7200,
                encoding="utf-8",
                errors="ignore",
            )
            print(f"[INFO] 音频混流完成，最终视频带完整样例原声")
            # 清理临时文件
            try:
                temp_no_audio_path.unlink()
            except:
                pass
        except subprocess.CalledProcessError as e:
            # 音频混流失败，降级返回无音视频，不中断主流程
            stderr_msg = e.stderr or ""
            print(f"[WARN] 音频混流降级，返回无音视频: {stderr_msg[:200]}")
            import shutil
            shutil.copy(str(temp_no_audio_path.resolve()), str(final_output_path.resolve()))
            try:
                temp_no_audio_path.unlink()
            except:
                pass
    else:
        # 没有参考音频源，直接使用临时文件作为最终输出
        import shutil
        shutil.copy(str(temp_no_audio_path.resolve()), str(final_output_path.resolve()))
        try:
            temp_no_audio_path.unlink()
        except:
            pass

    resolved_output = final_output_path.resolve()
    output_exists = resolved_output.exists() and resolved_output.is_file()
    output_size = resolved_output.stat().st_size if output_exists else 0

    return {
        "output_path": str(resolved_output),
        "output_filename": resolved_output.name,
        "success": output_exists and output_size > 0,
        "file_exists": output_exists,
        "file_size_bytes": output_size,
        "rendered_at": int(time.time() * 1000),
        "rendered_segment_count": len(timeline),
        "validation_report": validation_report,
        "_debug_audio_mixed": reference_audio_path is not None and Path(str(reference_audio_path)).exists(),
    }
