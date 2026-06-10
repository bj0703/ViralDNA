from __future__ import annotations
from typing import Any, Dict
from backend.app.agents.orchestrator import AgentRegistration, AgentRegistry


class AssetAnalyzerAgent:
    """
    素材分析 Agent
    读取用户上传的素材列表，生成素材索引
    """
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "assets": [],
            "asset_count": 0,
            "index_version": "0.1-contract"
        }


AgentRegistry.register(AgentRegistration(
    agent_name="AssetAnalyzerAgent",
    reads=[],
    writes=["asset_index"],
    optional_reads=[],
    factory=lambda: AssetAnalyzerAgent()
))


class SlotMatcherAgent:
    """
    槽位匹配 Agent
    将素材分配到样例结构槽位，输出匹配结果和缺口列表
    """
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "matches": [],
            "gaps": [],
            "match_score": 0
        }


AgentRegistry.register(AgentRegistration(
    agent_name="SlotMatcherAgent",
    reads=["reference_analysis", "asset_index"],
    writes=["slot_matches", "gaps"],
    optional_reads=[],
    factory=lambda: SlotMatcherAgent()
))


class GapResolverAgent:
    """
    缺口补齐 Agent
    按优先级智能补齐所有识别出的缺口
    """
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resolved_items": [],
            "strategies_applied": []
        }


AgentRegistry.register(AgentRegistration(
    agent_name="GapResolverAgent",
    reads=["gaps"],
    writes=["resolved_gaps"],
    optional_reads=[],
    factory=lambda: GapResolverAgent()
))


class EditPlannerAgent:
    """
    时间线生成 Agent
    产出最终可编辑的完整时间线草案
    """
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timeline": [],
            "total_duration": 0.0,
            "version": "0.1-contract"
        }


AgentRegistry.register(AgentRegistration(
    agent_name="EditPlannerAgent",
    reads=["slot_matches", "resolved_gaps"],
    writes=["edit_timeline"],
    optional_reads=[],
    factory=lambda: EditPlannerAgent()
))
