from __future__ import annotations

import json
import math
import mimetypes
import os
import shutil
import subprocess
from typing import Dict, List, Optional

from backend.app.models.sample_analysis import SampleUpload
from backend.app.providers.base import (
    ProviderAnalysis,
    ProviderPaceSegment,
    ProviderSection,
    VideoAnalysisProvider,
)


class HeuristicVideoAnalysisProvider(VideoAnalysisProvider):
    """A local fallback provider that derives structure using file metadata and notes."""

    def analyze(self, upload: SampleUpload) -> ProviderAnalysis:
        file_size = os.path.getsize(upload.storage_path)
        duration_seconds, duration_is_estimated = self._probe_duration(upload.storage_path, file_size)
        transcript_overview = self._build_transcript_overview(upload.notes, upload.original_filename)
        hook, middle_segments, ending = self._build_script_structure(
            duration_seconds,
            transcript_overview,
            upload.original_filename,
        )
        pace_segments, overall_pace, shot_density_estimate, highlight_position_seconds = self._build_pace_structure(
            duration_seconds,
            transcript_overview,
            file_size,
        )

        availability = {
            "speech_overview": "available" if transcript_overview else "unavailable",
            "ending_cta": ending.status,
            "pace_metrics": "available" if highlight_position_seconds is not None else "estimated",
            "preview": "available" if mimetypes.guess_type(upload.original_filename)[0] else "unavailable",
        }
        confidence = {
            "script_structure": 0.82 if transcript_overview else 0.58,
            "pace_structure": 0.7 if not duration_is_estimated else 0.55,
            "transcript_overview": 0.9 if transcript_overview else 0.2,
        }
        warnings: List[str] = []
        if transcript_overview is None:
            warnings.append("未提供字幕或语音内容，脚本结构基于文件名和启发式规则估计。")
        if duration_is_estimated:
            warnings.append("未检测到 ffprobe，时长为估计值。")
        if ending.status != "available":
            warnings.append("未识别到明确 CTA，结果已标记为缺失。")

        return ProviderAnalysis(
            duration_seconds=duration_seconds,
            duration_is_estimated=duration_is_estimated,
            transcript_overview=transcript_overview,
            hook=hook,
            middle_segments=middle_segments,
            ending=ending,
            pace_segments=pace_segments,
            overall_pace=overall_pace,
            shot_density_estimate=shot_density_estimate,
            highlight_position_seconds=highlight_position_seconds,
            highlight_position_status="available" if highlight_position_seconds is not None else "estimated",
            confidence=confidence,
            availability=availability,
            warnings=warnings,
            raw_outputs={
                "provider": "heuristic-local",
                "notes_provided": bool(upload.notes),
                "filename_tokens": self._tokenize_filename(upload.original_filename),
            },
        )

    def _probe_duration(self, storage_path: str, file_size: int) -> (float, bool):
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path:
            try:
                result = subprocess.run(
                    [
                        ffprobe_path,
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_format",
                        storage_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                data = json.loads(result.stdout)
                duration = float(data.get("format", {}).get("duration", 0.0))
                if duration > 0:
                    return round(duration, 2), False
            except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
                pass

        estimated = max(6.0, min(90.0, round(file_size / 1_000_000 * 4.5, 2)))
        return estimated, True

    def _build_transcript_overview(self, notes: Optional[str], filename: str) -> Optional[str]:
        if notes:
            normalized = " ".join(notes.strip().split())
            return normalized[:240]
        return None

    def _build_script_structure(
        self,
        duration_seconds: float,
        transcript_overview: Optional[str],
        filename: str,
    ):
        hook_end = max(2.0, round(duration_seconds * 0.18, 2))
        ending_start = max(duration_seconds - max(3.0, duration_seconds * 0.2), hook_end)
        middle_span = max(0.0, ending_start - hook_end)
        tokens = self._tokenize_filename(filename)
        topic = "、".join(tokens[:3]) if tokens else "核心主题"
        hook_summary = "开头快速抛出主题与吸引点，建立观看预期。"
        if transcript_overview:
            hook_summary = f"开头围绕“{topic}”快速建立主题，并用一句摘要吸引注意力。"

        hook = ProviderSection(
            label="hook",
            summary=hook_summary,
            start_seconds=0.0,
            end_seconds=hook_end,
            confidence=0.83 if transcript_overview else 0.61,
        )

        middle_segments: List[ProviderSection] = []
        if middle_span > 0:
            segment_count = 2 if middle_span < 20 else 3
            segment_length = middle_span / segment_count
            for index in range(segment_count):
                start_seconds = round(hook_end + index * segment_length, 2)
                end_seconds = round(hook_end + (index + 1) * segment_length, 2)
                middle_segments.append(
                    ProviderSection(
                        label=f"middle-{index + 1}",
                        summary=f"中段第 {index + 1} 段承接主题，逐步展开卖点或情境。",
                        start_seconds=start_seconds,
                        end_seconds=end_seconds,
                        confidence=0.75 if transcript_overview else 0.56,
                    )
                )

        has_cta = self._has_cta_signal(transcript_overview, filename)
        ending = ProviderSection(
            label="ending",
            summary="结尾强化行动指令或进行收束。" if has_cta else "未识别到明确 CTA，建议后续迁移时补足结尾表达。",
            start_seconds=round(ending_start, 2),
            end_seconds=round(duration_seconds, 2),
            confidence=0.8 if has_cta else 0.38,
            status="available" if has_cta else "missing",
        )
        return hook, middle_segments, ending

    def _build_pace_structure(
        self,
        duration_seconds: float,
        transcript_overview: Optional[str],
        file_size: int,
    ):
        segment_edges = [0.0, round(duration_seconds * 0.33, 2), round(duration_seconds * 0.66, 2), round(duration_seconds, 2)]
        density_base = max(1.2, min(6.5, file_size / 2_000_000))
        pace_segments: List[ProviderPaceSegment] = []
        labels = ["开场", "中段", "结尾"]
        pace_names = ["快", "中", "快"]
        for index in range(3):
            pace_segments.append(
                ProviderPaceSegment(
                    label=labels[index],
                    start_seconds=segment_edges[index],
                    end_seconds=segment_edges[index + 1],
                    pace=pace_names[index],
                    shot_density_estimate=round(density_base + index * 0.4, 2),
                    confidence=0.72 if not transcript_overview else 0.78,
                )
            )

        highlight_position_seconds = round(duration_seconds * 0.72, 2) if duration_seconds >= 8 else round(duration_seconds * 0.5, 2)
        overall_pace = "高节奏" if density_base >= 3.5 else "中节奏"
        return pace_segments, overall_pace, round(density_base, 2), highlight_position_seconds

    def _tokenize_filename(self, filename: str) -> List[str]:
        name, _ = os.path.splitext(filename)
        normalized = name.replace("-", "_").replace(" ", "_")
        tokens = [token for token in normalized.split("_") if token]
        return tokens[:8]

    def _has_cta_signal(self, transcript_overview: Optional[str], filename: str) -> bool:
        signal_text = f"{transcript_overview or ''} {filename}".lower()
        keywords = ["buy", "shop", "link", "立即", "下单", "关注", "点击", "购买", "了解更多", "subscribe"]
        return any(keyword in signal_text for keyword in keywords)
