from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib import error, request

from backend.app.core.config import ArkChatConfig


class ArkChatProvider:
    """Thin HTTP client for the confirmed Ark chat/completions contract."""

    def __init__(self, config: ArkChatConfig) -> None:
        self.config = config

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 400,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        if not self.config.is_configured:
            raise RuntimeError("ARK chat configuration is incomplete.")

        payload = {
            "model": self.config.endpoint_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.config.base_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw = response.read().decode(charset)
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ark request failed with HTTP {exc.code}: {message}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Ark request failed: {exc.reason}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ark returned non-JSON content.") from exc

    @staticmethod
    def extract_text(response_json: Dict[str, Any]) -> str:
        choices: List[Dict[str, Any]] = response_json.get("choices", [])
        if not choices:
            raise RuntimeError("Ark response did not contain choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ark response message content was empty.")
        return content.strip()
