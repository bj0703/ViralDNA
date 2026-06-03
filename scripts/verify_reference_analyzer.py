from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.agents.reference_analyzer import ReferenceAnalyzerAgent
from backend.app.core.config import load_ark_chat_config
from backend.app.models.sample_analysis import SampleUpload
from backend.app.providers.ark_chat import ArkChatProvider
from backend.app.providers.heuristic_video_analysis import HeuristicVideoAnalysisProvider
from backend.app.providers.reference_analyzer import ReferenceAnalyzerAgentProvider


def main() -> None:
    sample_path = ROOT / "样例" / "抖音2026522-387724.mp4"
    upload = SampleUpload(
        original_filename=sample_path.name,
        saved_filename=sample_path.name,
        storage_path=str(sample_path),
        content_type="video/mp4",
        notes="请分析这个真实样例视频的脚本结构、节奏结构、包装与声音，并输出迁移建议。",
    )

    heuristic_provider = HeuristicVideoAnalysisProvider()
    heuristic_result = heuristic_provider.analyze(upload)

    agent_provider = ReferenceAnalyzerAgentProvider(
        agent=ReferenceAnalyzerAgent(ArkChatProvider(load_ark_chat_config())),
        heuristic_provider=heuristic_provider,
    )
    agent_result = agent_provider.analyze(upload)

    comparison = {
        "heuristic": {
            "duration_seconds": heuristic_result.duration_seconds,
            "hook": heuristic_result.hook.summary,
            "pace": heuristic_result.overall_pace,
            "warnings": heuristic_result.warnings,
        },
        "agent": {
            "duration_seconds": agent_result.duration_seconds,
            "hook": agent_result.hook.summary,
            "pace": agent_result.overall_pace,
            "warnings": agent_result.warnings,
            "raw_outputs": agent_result.raw_outputs,
        },
    }
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
