from __future__ import annotations

import json
from typing import Any, Dict, Optional

from backend.app.providers.ark_chat import ArkChatProvider


class IntentRoutingService:
    def __init__(self, ark_chat_provider: Optional[ArkChatProvider]) -> None:
        self.ark_chat_provider = ark_chat_provider

    def detect_intent(self, text: str, target_video_id: Optional[str]) -> Dict[str, Any]:
        normalized_text = text.strip()
        if not normalized_text:
            return self._fallback_result(
                intent="video-analysis",
                target_video_id=target_video_id,
                confidence=0.1,
                reason="empty-text",
            )

        if self.ark_chat_provider and self.ark_chat_provider.config.is_configured:
            try:
                return self._detect_with_ark(normalized_text, target_video_id)
            except RuntimeError:
                pass
        return self._detect_with_rules(normalized_text, target_video_id)

    def _detect_with_ark(self, text: str, target_video_id: Optional[str]) -> Dict[str, Any]:
        system_prompt = (
            "你是一个视频分析工作台的意图识别器。"
            "请只返回JSON，不要返回额外解释。"
            "可用 intent 只有：video-analysis、script-structure-analysis、pace-analysis、highlight-detection、export-structured-result。"
            "输出字段必须包含：intent、analysis_scope、target_video_id、fallback_behavior、confidence。"
        )
        user_prompt = (
            f"target_video_id={target_video_id or ''}\n"
            f"user_text={text}\n"
            "请识别用户意图，analysis_scope 可用 full/script/pace/highlight/export。"
        )
        response_json = self.ark_chat_provider.chat(system_prompt, user_prompt, max_tokens=300, temperature=0.0)
        content = self.ark_chat_provider.extract_text(response_json)
        parsed = json.loads(content)
        return {
            "intent": parsed.get("intent", "video-analysis"),
            "analysis_scope": parsed.get("analysis_scope", "full"),
            "target_video_id": parsed.get("target_video_id") or target_video_id,
            "fallback_behavior": parsed.get("fallback_behavior", "default-to-video-analysis"),
            "confidence": float(parsed.get("confidence", 0.7)),
            "source": "ark-chat",
            "raw_model_output": content,
        }

    def _detect_with_rules(self, text: str, target_video_id: Optional[str]) -> Dict[str, Any]:
        lowered = text.lower()
        if "节奏" in text or "pace" in lowered:
            return self._fallback_result("pace-analysis", target_video_id, 0.82, "keyword-match")
        if "hook" in lowered or "脚本" in text or "结构" in text:
            return self._fallback_result("script-structure-analysis", target_video_id, 0.84, "keyword-match")
        if "高光" in text or "highlight" in lowered:
            return self._fallback_result("highlight-detection", target_video_id, 0.84, "keyword-match")
        if "导出" in text or "json" in lowered:
            return self._fallback_result("export-structured-result", target_video_id, 0.8, "keyword-match")
        return self._fallback_result("video-analysis", target_video_id, 0.66, "default-fallback")

    def _fallback_result(
        self,
        intent: str,
        target_video_id: Optional[str],
        confidence: float,
        reason: str,
    ) -> Dict[str, Any]:
        scope_by_intent = {
            "video-analysis": "full",
            "script-structure-analysis": "script",
            "pace-analysis": "pace",
            "highlight-detection": "highlight",
            "export-structured-result": "export",
        }
        return {
            "intent": intent,
            "analysis_scope": scope_by_intent[intent],
            "target_video_id": target_video_id,
            "fallback_behavior": "default-to-video-analysis" if intent == "video-analysis" else "keep-detected-intent",
            "confidence": confidence,
            "source": "local-rules",
            "raw_model_output": None,
            "reason": reason,
        }
