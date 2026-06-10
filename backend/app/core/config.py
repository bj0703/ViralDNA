from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


def _load_project_env() -> None:
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_project_env()


@dataclass
class ArkChatConfig:
    api_key: str
    endpoint_id: str
    base_url: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.endpoint_id and self.base_url)


def load_ark_chat_config() -> ArkChatConfig:
    return ArkChatConfig(
        api_key=os.getenv("ARK_API_KEY", "").strip(),
        endpoint_id=os.getenv("ARK_ENDPOINT_ID", "ep-20260508213828-7ntjl").strip(),
        base_url=os.getenv(
            "ARK_BASE_URL",
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        ).strip(),
    )


@dataclass
class FFmpegConfig:
    ffmpeg_path: str

    @property
    def is_available(self) -> bool:
        if self.ffmpeg_path:
            return Path(self.ffmpeg_path).exists()
        return shutil.which("ffmpeg") is not None


def load_ffmpeg_config() -> FFmpegConfig:
    custom_path = os.getenv("FFMPEG_PATH", "").strip()
    return FFmpegConfig(ffmpeg_path=custom_path)


@dataclass
class RedisConfig:
    redis_url: str
    redis_enabled: bool

    @property
    def is_available(self) -> bool:
        return bool(self.redis_url and self.redis_url != "disabled")


def load_redis_config() -> RedisConfig:
    url = os.getenv("REDIS_URL", "disabled").strip()
    enabled = url != "disabled"
    return RedisConfig(redis_url=url, redis_enabled=enabled)
