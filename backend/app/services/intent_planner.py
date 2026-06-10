from __future__ import annotations

import json
from typing import Any, Dict, List, TYPE_CHECKING

from backend.app.agents.orchestrator import AgentRegistry
from backend.app.core.shared_memory import SessionSharedMemory

if TYPE_CHECKING:
    from backend.app.providers.ark_chat import ArkChatProvider


LLM_INTENT_PLAN_SYSTEM_PROMPT = """你是智能意图规划专家，深度理解用户自然语言 + 当前系统状态，智能决策执行流程路径。

执行模式分为两条完全独立的主路径：
路径A【参考样例复刻模式】：用户上传了 is_reference 标记为 True 的样例视频，并且意图是复刻/迁移该样例的剪辑结构
  → 执行序列：ReferenceAnalyzerAgent → AssetIndexerAgent → SlotMatcherAgent → GapResolverAgent → EditPlannerAgent → FinalVideoRendererAgent

路径B【知识库预设风格模式】：用户没有上传参考样例视频，或者用户明确说出类似关键词"用/按照/参考/走XX风格/XX模式/知识库模板"这类要求
  → 执行序列：ReferenceAnalyzerAgent(内部自动检索知识库) → AssetIndexerAgent → SlotMatcherAgent → GapResolverAgent → EditPlannerAgent → FinalVideoRendererAgent

可用Agent注册表：
[
  {"name": "ReferenceAnalyzerAgent", "desc": "【自动双模式】有参考样例就分析视频结构，无参考样例自动从知识库检索成熟剪辑模板", "requirements": ["永远可以执行，内部自动双分支判断"]},
  {"name": "AssetIndexerAgent", "desc": "批量分析所有素材视频，打标签标记可用片段", "requirements": ["上传了至少1个素材视频"]},
  {"name": "SlotMatcherAgent", "desc": "把素材智能匹配到对应的结构槽位", "requirements": ["reference_analysis结果", "素材索引结果"]},
  {"name": "GapResolverAgent", "desc": "补齐所有未填满的缺口", "requirements": ["槽位匹配结果"]},
  {"name": "GeneratedAssetBuilderAgent", "desc": "实际执行GapResolver规划的所有AIGC动态资源生成", "requirements": ["缺口补齐结果"]},
  {"name": "EditPlannerAgent", "desc": "生成最终可编辑剪辑时间线", "requirements": ["动态资源生成完成"]},
  {"name": "FinalVideoRendererAgent", "desc": "调用FFmpeg渲染出最终视频", "requirements": ["剪辑时间线"]}
]

你的任务规则：
1. 深度理解用户自然语言的核心意图，不要死板只看上传文件数量。
2. 如果用户明确说出「用vlog旅拍风格/走口播带货模式/用教程教学模板」这类风格关键词，优先走路径B知识库模式。
3. 已经有对应输出结果的Agent可以跳过不用重复执行。
4. 用户明确要求的增量修改，只执行变化部分的下游依赖。
5. 输出严格JSON，只返回以下结构，绝对禁止任何多余文字解释：
{
  "selected_agent_names": ["Agent名称1", "Agent名称2"],
  "skip_reasons": {"被跳过的Agent名称": "跳过原因说明"},
  "confidence": 0.95
}
"""


class DynamicIntentPlanner:
    """动态意图规划器。

    优先使用 LLM 结合当前 shared_memory 生成执行计划；
    当 LLM 不可用或返回结果非法时，回退到本地规则规划。
    """

    @staticmethod
    def _rule_based_plan(user_prompt: str, shared_memory: SessionSharedMemory) -> List[str]:
        uploaded_videos = shared_memory.get_nested("inputs.uploaded_videos") or []
        ref_count = sum(1 for video in uploaded_videos if video.get("is_reference", False))
        asset_count = sum(1 for video in uploaded_videos if not video.get("is_reference", False))
        prompt_lower = user_prompt.lower()

        generate_video_keywords = ["生成视频", "输出视频", "渲染视频", "导出视频", "final video", "render"]
        want_final_video = any(keyword in prompt_lower for keyword in generate_video_keywords)

        plans: List[str] = []

        if ref_count == 0 and asset_count >= 1:
            # 没有参考样例但有素材：先走ReferenceAnalyzerAgent，内部自动执行知识库检索
            plans.append("ReferenceAnalyzerAgent")
            plans.append("AssetIndexerAgent")
            plans.append("SlotMatcherAgent")
            plans.append("GapResolverAgent")
            plans.append("GeneratedAssetBuilderAgent")
            plans.append("EditPlannerAgent")
            if want_final_video:
                plans.append("FinalVideoRendererAgent")
            return plans

        if ref_count >= 1 and asset_count >= 1:
            full_keywords = ["复刻", "全流程", "全部", "迁移", "完整"]
            if any(keyword in prompt_lower for keyword in full_keywords) or not any(
                keyword in prompt_lower for keyword in ["只分析", "仅分析", "只索引", "仅索引"]
            ):
                plans.extend(
                    [
                        "ReferenceAnalyzerAgent",
                        "AssetIndexerAgent",
                        "SlotMatcherAgent",
                        "GapResolverAgent",
                        "GeneratedAssetBuilderAgent",
                        "EditPlannerAgent",
                    ]
                )
                if want_final_video:
                    plans.append("FinalVideoRendererAgent")
                return plans

        if ref_count >= 1:
            single_keywords = ["只分析", "仅分析", "分析这个", "单样例"]
            if any(keyword in prompt_lower for keyword in single_keywords) or asset_count == 0:
                return ["ReferenceAnalyzerAgent"]

        if asset_count >= 1:
            index_keywords = ["只索引", "仅索引", "索引这些", "素材分类"]
            if any(keyword in prompt_lower for keyword in index_keywords) or ref_count == 0:
                return ["AssetIndexerAgent"]

        plans.append("ReferenceAnalyzerAgent")
        if asset_count >= 1:
            plans.append("AssetIndexerAgent")
        return plans

    @staticmethod
    def _build_context(shared_memory: SessionSharedMemory, user_prompt: str) -> Dict[str, Any]:
        uploaded_videos = shared_memory.get_nested("inputs.uploaded_videos") or []
        return {
            "current_state": {
                "reference_video_count": sum(1 for video in uploaded_videos if video.get("is_reference", False)),
                "asset_video_count": sum(1 for video in uploaded_videos if not video.get("is_reference", False)),
                "existing_keys": list(shared_memory.entries.keys()) if hasattr(shared_memory, "entries") else [],
                "selected_reference_video_id": shared_memory.get_nested("inputs.selected_reference_video_id"),
                "requested_variant_id": shared_memory.get_nested("inputs.requested_variant_id"),
                "has_edit_timeline": shared_memory.get("edit_timeline") is not None,
            },
            "user_prompt": user_prompt,
        }

    @staticmethod
    def _extract_json_object(raw_text: str) -> Dict[str, Any]:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("DynamicIntentPlanner could not find a JSON object in model output.")
        return json.loads(raw_text[start : end + 1])

    @staticmethod
    def _validate_selected_agent_names(selected_names: Any) -> List[str]:
        if not isinstance(selected_names, list):
            return []

        validated_names: List[str] = []
        for name in selected_names:
            agent_name = str(name).strip()
            if agent_name and AgentRegistry.get(agent_name) is not None and agent_name not in validated_names:
                validated_names.append(agent_name)
        return validated_names

    @staticmethod
    def plan(user_prompt: str, shared_memory: SessionSharedMemory) -> List[str]:
        from backend.app.dependencies import ark_chat_provider

        if ark_chat_provider and ark_chat_provider.config.is_configured:
            try:
                context_dict = DynamicIntentPlanner._build_context(shared_memory, user_prompt)
                user_content = json.dumps(context_dict, ensure_ascii=False)

                response_json = ark_chat_provider.chat(
                    LLM_INTENT_PLAN_SYSTEM_PROMPT,
                    user_content,
                    max_tokens=1000,
                    temperature=0.0,
                )
                raw_text = ark_chat_provider.extract_text(response_json)
                parsed = DynamicIntentPlanner._extract_json_object(raw_text)

                selected_names = parsed.get("selected_agent_names", [])
                confidence = float(parsed.get("confidence", 0.0))
                validated_names = DynamicIntentPlanner._validate_selected_agent_names(selected_names)

                if confidence >= 0.6 and validated_names:
                    print(f"[INFO] LLM智能意图规划成功: selected={validated_names}, confidence={confidence}")
                    shared_memory.append_event(
                        "llm_intent_plan",
                        "DynamicIntentPlanner",
                        {
                            "selected_names": validated_names,
                            "skip_reasons": parsed.get("skip_reasons", {}),
                            "confidence": confidence,
                            "raw_model_output": raw_text,
                        },
                    )
                    return validated_names
            except Exception as exc:
                print(f"[WARN] LLM意图规划失败，自动回退规则: {str(exc)}")
                shared_memory.append_event(
                    "llm_intent_plan_failed",
                    "DynamicIntentPlanner",
                    {
                        "error": str(exc),
                    },
                )

        return DynamicIntentPlanner._rule_based_plan(user_prompt, shared_memory)
