from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.app.agents.reference_analyzer import ReferenceAnalyzerAgent
from backend.app.models.sample_analysis import SampleUpload
from backend.app.providers.base import (
    ProviderAnalysis,
    ProviderPaceSegment,
    ProviderSection,
    VideoAnalysisProvider,
)
from backend.app.providers.heuristic_video_analysis import HeuristicVideoAnalysisProvider


class ReferenceAnalyzerAgentProvider(VideoAnalysisProvider):
    """Use ReferenceAnalyzerAgent first, then fall back to heuristic analysis."""

    def __init__(
        self,
        agent: ReferenceAnalyzerAgent,
        heuristic_provider: Optional[HeuristicVideoAnalysisProvider] = None,
    ) -> None:
        self.agent = agent
        self.heuristic_provider = heuristic_provider or HeuristicVideoAnalysisProvider()

    def analyze(self, upload: SampleUpload) -> ProviderAnalysis:
        heuristic_result = self.heuristic_provider.analyze(upload)
        if not self.agent.is_available():
            heuristic_result.warnings.append("ReferenceAnalyzerAgent 未配置，已回退到启发式分析。")
            heuristic_result.raw_outputs["provider"] = "reference-analyzer-fallback"
            return heuristic_result

        context = self._build_context(upload, heuristic_result)
        try:
            agent_output = self.agent.analyze(context)
            return self._map_agent_output(upload, heuristic_result, agent_output)
        except Exception as exc:
            heuristic_result.warnings.append(f"ReferenceAnalyzerAgent 失败，已回退到启发式分析：{exc}")
            heuristic_result.raw_outputs["provider"] = "reference-analyzer-fallback"
            heuristic_result.raw_outputs["agent_error"] = str(exc)
            return heuristic_result

    def _build_context(self, upload: SampleUpload, heuristic_result: ProviderAnalysis) -> Dict[str, Any]:
        fallback_paragraphs = [
            {
                "type": "hook",
                "start_time": heuristic_result.hook.start_seconds,
                "end_time": heuristic_result.hook.end_seconds,
                "content_summary": heuristic_result.hook.summary,
            }
        ]
        fallback_paragraphs.extend(
            {
                "type": "develop",
                "start_time": section.start_seconds,
                "end_time": section.end_seconds,
                "content_summary": section.summary,
            }
            for section in heuristic_result.middle_segments
        )
        fallback_paragraphs.append(
            {
                "type": "cta" if heuristic_result.ending.status == "available" else "develop",
                "start_time": heuristic_result.ending.start_seconds,
                "end_time": heuristic_result.ending.end_seconds,
                "content_summary": heuristic_result.ending.summary,
            }
        )
        return {
            "filename": upload.original_filename,
            "storage_path": upload.storage_path,
            "file_size_bytes": os.path.getsize(upload.storage_path),
            "duration_seconds": heuristic_result.duration_seconds,
            "notes": upload.notes,
            "heuristic": {
                "transcript_overview": heuristic_result.transcript_overview,
                "hook_summary": heuristic_result.hook.summary,
                "middle_summaries": [section.summary for section in heuristic_result.middle_segments],
                "ending_summary": heuristic_result.ending.summary,
                "overall_pace": heuristic_result.overall_pace,
                "highlight_position_seconds": heuristic_result.highlight_position_seconds,
                "fallback_type_label": "生活记录",
                "fallback_paragraphs": fallback_paragraphs,
            },
        }

    def _map_agent_output(
        self,
        upload: SampleUpload,
        heuristic_result: ProviderAnalysis,
        agent_output: Dict[str, Any],
    ) -> ProviderAnalysis:
        basic = agent_output["video_basic_info"]
        script = agent_output["script_structure"]
        rhythm = agent_output["rhythm_structure"]
        packaging = agent_output["packaging_and_sound"]
        migration = agent_output["migration_suggestion"]

        hook = self._find_first_paragraph(script.get("paragraphs", []), "hook", heuristic_result.hook)
        ending = self._find_last_paragraph(script.get("paragraphs", []), heuristic_result.ending)
        middle_segments = self._build_middle_segments(script.get("paragraphs", []), heuristic_result.middle_segments)
        pace_segments = self._build_pace_segments(rhythm, heuristic_result)

        warnings = list(heuristic_result.warnings)
        warnings.append("ReferenceAnalyzerAgent 已参与样例分析，当前结果基于大模型结构化输出映射。")

        raw_outputs: Dict[str, Any] = {
            "provider": "reference-analyzer-agent",
            "agent_output": agent_output,
            "heuristic_baseline": heuristic_result.raw_outputs,
            "comparison": self._comparison_summary(heuristic_result, script, rhythm),
            "packaging_and_sound": packaging,
            "migration_suggestion": migration,
        }

        return ProviderAnalysis(
            duration_seconds=float(basic.get("core_content_effective_duration_seconds") or heuristic_result.duration_seconds),
            duration_is_estimated=heuristic_result.duration_is_estimated,
            transcript_overview=upload.notes or script.get("summary"),
            hook=hook,
            middle_segments=middle_segments,
            ending=ending,
            pace_segments=pace_segments,
            overall_pace=self._normalize_pace_label(rhythm.get("shot_switch_pacing", heuristic_result.overall_pace)),
            shot_density_estimate=float(rhythm.get("avg_shot_duration_seconds") or heuristic_result.shot_density_estimate),
            highlight_position_seconds=self._pick_highlight(rhythm.get("highlight_position_seconds"), heuristic_result.highlight_position_seconds),
            highlight_position_status="available",
            confidence={
                "script_structure": 0.9,
                "pace_structure": 0.84,
                "transcript_overview": 0.78 if upload.notes else 0.6,
            },
            availability={
                "speech_overview": "available" if upload.notes else "estimated",
                "ending_cta": ending.status,
                "pace_metrics": "available",
                "preview": "available",
            },
            warnings=warnings,
            raw_outputs=raw_outputs,
        )

    def _find_first_paragraph(
        self,
        paragraphs: List[Dict[str, Any]],
        paragraph_type: str,
        fallback: ProviderSection,
    ) -> ProviderSection:
        for paragraph in paragraphs:
            if paragraph.get("type") == paragraph_type:
                return ProviderSection(
                    label=paragraph_type,
                    summary=str(paragraph.get("content_summary") or fallback.summary),
                    start_seconds=float(paragraph.get("start_time") or fallback.start_seconds),
                    end_seconds=float(paragraph.get("end_time") or fallback.end_seconds),
                    confidence=0.9,
                )
        return fallback

    def _find_last_paragraph(
        self,
        paragraphs: List[Dict[str, Any]],
        fallback: ProviderSection,
    ) -> ProviderSection:
        for paragraph in reversed(paragraphs):
            if paragraph.get("type") in {"cta", "develop"}:
                summary = str(paragraph.get("content_summary") or fallback.summary)
                status = "available" if paragraph.get("type") == "cta" else fallback.status
                return ProviderSection(
                    label="ending",
                    summary=summary,
                    start_seconds=float(paragraph.get("start_time") or fallback.start_seconds),
                    end_seconds=float(paragraph.get("end_time") or fallback.end_seconds),
                    confidence=0.86 if status == "available" else 0.62,
                    status=status,
                )
        return fallback

    def _build_middle_segments(
        self,
        paragraphs: List[Dict[str, Any]],
        fallback_sections: List[ProviderSection],
    ) -> List[ProviderSection]:
        develops = [paragraph for paragraph in paragraphs if paragraph.get("type") == "develop"]
        if not develops:
            return fallback_sections
        segments: List[ProviderSection] = []
        for index, paragraph in enumerate(develops, start=1):
            segments.append(
                ProviderSection(
                    label=f"middle-{index}",
                    summary=str(paragraph.get("content_summary") or f"中段第 {index} 段"),
                    start_seconds=float(paragraph.get("start_time") or 0.0),
                    end_seconds=float(paragraph.get("end_time") or 0.0),
                    confidence=0.84,
                )
            )
        return segments

    def _build_pace_segments(
        self,
        rhythm: Dict[str, Any],
        fallback: ProviderAnalysis,
    ) -> List[ProviderPaceSegment]:
        highlight_positions = rhythm.get("highlight_position_seconds")
        paragraphs = fallback.pace_segments
        if not paragraphs:
            return []
        pace_text = str(rhythm.get("shot_switch_pacing") or fallback.overall_pace)
        normalized_pace = self._normalize_pace_label(pace_text)
        return [
            ProviderPaceSegment(
                label=segment.label,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                pace=normalized_pace,
                shot_density_estimate=float(rhythm.get("avg_shot_duration_seconds") or segment.shot_density_estimate),
                confidence=0.8,
            )
            for segment in paragraphs
        ]

    def _normalize_pace_label(self, value: str) -> str:
        if "快" in value:
            return "快"
        if "慢" in value:
            return "慢"
        return "中"

    def _pick_highlight(self, values: Any, fallback: Optional[float]) -> Optional[float]:
        if isinstance(values, list) and values:
            try:
                return float(values[0])
            except (TypeError, ValueError):
                return fallback
        return fallback

    def _comparison_summary(
        self,
        heuristic_result: ProviderAnalysis,
        script: Dict[str, Any],
        rhythm: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "heuristic_hook_summary": heuristic_result.hook.summary,
            "agent_script_summary": script.get("summary"),
            "heuristic_overall_pace": heuristic_result.overall_pace,
            "agent_pace_description": rhythm.get("shot_switch_pacing"),
            "known_risk": "当前 agent 通过 chat/completions 基于上下文推断，不是直接的视频像素流理解。",
        }
