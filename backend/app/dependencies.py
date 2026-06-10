from __future__ import annotations

from backend.app.agents.asset_indexer import AssetIndexerAgent
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.downstream_contracts import *
from backend.app.agents.edit_planner import EditPlannerAgent
from backend.app.agents.final_video_renderer import FinalVideoRendererAgent
from backend.app.agents.gap_resolver import GapResolverAgent
from backend.app.agents.orchestrator import AgentRegistry, AgentRegistration
from backend.app.agents.reference_analyzer import ReferenceAnalyzerAgent
from backend.app.agents.slot_matcher import SlotMatcherAgent
from backend.app.core.config import load_ark_chat_config, load_ffmpeg_config
from backend.app.core.shared_memory import UploadedVideo
from backend.app.providers.ark_chat import ArkChatProvider
from backend.app.providers.heuristic_video_analysis import HeuristicVideoAnalysisProvider
from backend.app.providers.reference_analyzer import ReferenceAnalyzerAgentProvider
from backend.app.repositories.in_memory_sample_analysis import InMemorySampleAnalysisRepository
from backend.app.services.intent_planner import DynamicIntentPlanner
from backend.app.services.intent_routing import IntentRoutingService
from backend.app.services.sample_analysis import SampleAnalysisService


repository = InMemorySampleAnalysisRepository()
heuristic_provider = HeuristicVideoAnalysisProvider()
ark_chat_config = load_ark_chat_config()
ark_chat_provider = ArkChatProvider(ark_chat_config)
ffmpeg_config = load_ffmpeg_config()

reference_analyzer_agent = ReferenceAnalyzerAgent(ark_chat_provider)
asset_indexer_agent = AssetIndexerAgent(ark_chat_provider)
slot_matcher_agent = SlotMatcherAgent(ark_chat_provider)
gap_resolver_agent = GapResolverAgent(ark_chat_provider)
edit_planner_agent = EditPlannerAgent(ark_chat_provider)
final_video_renderer_agent = FinalVideoRendererAgent()

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


AgentRegistry.register(AgentRegistration(
    agent_name="ReferenceAnalyzerAgent",
    reads=["inputs.uploaded_videos"],
    writes=["reference_analysis"],
    optional_reads=[],
    factory=lambda: reference_analyzer_agent
))

AgentRegistry.register(AgentRegistration(
    agent_name="AssetIndexerAgent",
    reads=["inputs.uploaded_videos"],
    writes=["asset_index"],
    optional_reads=["reference_analysis"],
    factory=lambda: asset_indexer_agent
))

AgentRegistry.register(AgentRegistration(
    agent_name="SlotMatcherAgent",
    reads=["reference_analysis", "asset_index"],
    writes=["slot_matches"],
    optional_reads=[],
    factory=lambda: slot_matcher_agent
))

AgentRegistry.register(AgentRegistration(
    agent_name="GapResolverAgent",
    reads=["slot_matches"],
    writes=["resolved_gaps"],
    optional_reads=[],
    factory=lambda: gap_resolver_agent
))

AgentRegistry.register(AgentRegistration(
    agent_name="EditPlannerAgent",
    reads=["reference_analysis", "asset_index", "slot_matches", "resolved_gaps"],
    writes=["edit_timeline"],
    optional_reads=[],
    factory=lambda: edit_planner_agent
))

AgentRegistry.register(AgentRegistration(
    agent_name="FinalVideoRendererAgent",
    reads=["edit_timeline", "inputs.uploaded_videos"],
    writes=["final_video_meta"],
    optional_reads=[],
    factory=lambda: final_video_renderer_agent
))
