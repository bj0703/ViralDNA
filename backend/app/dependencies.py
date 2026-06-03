from __future__ import annotations

from backend.app.agents.reference_analyzer import ReferenceAnalyzerAgent
from backend.app.core.config import load_ark_chat_config
from backend.app.providers.ark_chat import ArkChatProvider
from backend.app.providers.heuristic_video_analysis import HeuristicVideoAnalysisProvider
from backend.app.providers.reference_analyzer import ReferenceAnalyzerAgentProvider
from backend.app.repositories.in_memory_sample_analysis import InMemorySampleAnalysisRepository
from backend.app.services.intent_routing import IntentRoutingService
from backend.app.services.sample_analysis import SampleAnalysisService


repository = InMemorySampleAnalysisRepository()
heuristic_provider = HeuristicVideoAnalysisProvider()
ark_chat_config = load_ark_chat_config()
ark_chat_provider = ArkChatProvider(ark_chat_config)
reference_analyzer_agent = ReferenceAnalyzerAgent(ark_chat_provider)
provider = ReferenceAnalyzerAgentProvider(
    agent=reference_analyzer_agent,
    heuristic_provider=heuristic_provider,
)
intent_routing_service = IntentRoutingService(
    ark_chat_provider=ark_chat_provider,
)
sample_analysis_service = SampleAnalysisService(
    repository=repository,
    provider=provider,
)
