from __future__ import annotations

import json
import mimetypes
from base64 import b64encode
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib import error, request

from backend.app.core.config import ArkChatConfig


class ArkChatProvider:
    """Thin HTTP client for the Ark chat/completions contract."""

    def __init__(self, config: ArkChatConfig) -> None:
        self.config = config

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: Optional[int] = None,
        temperature: float = 0.2,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        return self.chat_messages(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            on_delta=on_delta,
        )

    def analyze_video(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        video_path: str,
        content_type: Optional[str],
        max_tokens: Optional[int] = None,
        temperature: float = 0.1,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        video_url = self._build_video_data_url(video_path, content_type)
        return self.chat_messages(
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "video_url", "video_url": {"url": video_url}},
                    ],
                },
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            on_delta=on_delta,
        )

    def chat_messages(
        self,
        messages: List[Dict[str, Any]],
        *,
        max_tokens: Optional[int] = None,
        temperature: float = 0.2,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        if not self.config.is_configured:
            raise RuntimeError("ARK chat configuration is incomplete.")

        payload = {
            "model": self.config.endpoint_id,
            "messages": messages,
            "stream": bool(on_delta),
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if on_delta:
            return self._post_payload_streaming(payload, on_delta)
        return self._post_payload(payload)

    def _post_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = self._build_request(payload)
        try:
            with request.urlopen(req, timeout=120) as response:
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

    def _post_payload_streaming(
        self,
        payload: Dict[str, Any],
        on_delta: Callable[[str], None],
    ) -> Dict[str, Any]:
        req = self._build_request(payload)
        accumulated_text = ""
        finish_reason: Optional[str] = None

        try:
            with request.urlopen(req, timeout=120) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                for raw_line in response:
                    line = raw_line.decode(charset, errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if data == "[DONE]":
                        break

                    try:
                        event_json = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    delta_text = self._extract_stream_delta_text(event_json)
                    if delta_text:
                        accumulated_text += delta_text
                        on_delta(delta_text)

                    event_finish_reason = self._extract_finish_reason(event_json)
                    if event_finish_reason:
                        finish_reason = event_finish_reason
                        break
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ark request failed with HTTP {exc.code}: {message}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Ark request failed: {exc.reason}") from exc

        if not accumulated_text.strip():
            raise RuntimeError("Ark streaming response did not contain any text.")

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": accumulated_text.strip(),
                    },
                    "finish_reason": finish_reason,
                }
            ]
        }

    def _build_request(self, payload: Dict[str, Any]) -> request.Request:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        body = json.dumps(payload).encode("utf-8")
        return request.Request(
            self.config.base_url,
            data=body,
            headers=headers,
            method="POST",
        )

    @staticmethod
    def _extract_stream_delta_text(event_json: Dict[str, Any]) -> str:
        choices: List[Dict[str, Any]] = event_json.get("choices", [])
        if not choices:
            return ""

        delta = choices[0].get("delta", {})
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
            ]
            return "".join(text_parts)

        message = choices[0].get("message", {})
        message_content = message.get("content")
        if isinstance(message_content, str):
            return message_content
        return ""

    @staticmethod
    def _extract_finish_reason(event_json: Dict[str, Any]) -> Optional[str]:
        choices: List[Dict[str, Any]] = event_json.get("choices", [])
        if not choices:
            return None
        finish_reason = choices[0].get("finish_reason")
        return finish_reason if isinstance(finish_reason, str) and finish_reason else None

    @staticmethod
    def _build_video_data_url(video_path: str, content_type: Optional[str]) -> str:
        file_path = Path(video_path)
        if not file_path.exists():
            raise RuntimeError(f"Video file does not exist: {video_path}")

        detected_type = content_type or mimetypes.guess_type(file_path.name)[0] or "video/mp4"
        with file_path.open("rb") as video_file:
            encoded = b64encode(video_file.read()).decode("ascii")
        return f"data:{detected_type};base64,{encoded}"

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

    @staticmethod
    def extract_finish_reason(response_json: Dict[str, Any]) -> Optional[str]:
        choices: List[Dict[str, Any]] = response_json.get("choices", [])
        if not choices:
            return None
        finish_reason = choices[0].get("finish_reason")
        return finish_reason if isinstance(finish_reason, str) and finish_reason else None
