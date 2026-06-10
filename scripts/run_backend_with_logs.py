from __future__ import annotations

import atexit
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TeeStream:
    """Mirror console output to both the terminal and a log file."""

    def __init__(self, original: TextIO, log_file: TextIO) -> None:
        self._original = original
        self._log_file = log_file
        self.encoding = getattr(original, "encoding", "utf-8")

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._original.write(data)
        self._log_file.write(data)
        return len(data)

    def flush(self) -> None:
        self._original.flush()
        self._log_file.flush()

    def isatty(self) -> bool:
        return self._original.isatty()


def _resolve_log_path() -> Path:
    existing = os.environ.get("EMO_TRANSFER_BACKEND_LOG")
    if existing:
        return Path(existing)

    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"backend_{timestamp}.log"
    os.environ["EMO_TRANSFER_BACKEND_LOG"] = str(log_path)
    return log_path


def main() -> None:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    log_path = _resolve_log_path()
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    atexit.register(log_file.close)

    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)

    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    reload_enabled = os.environ.get("BACKEND_RELOAD", "1") != "0"

    print(f"[BOOT] Backend full log file: {log_path}")
    print(f"[BOOT] Starting uvicorn on http://{host}:{port} reload={reload_enabled}")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        app_dir=str(PROJECT_ROOT),
        reload=reload_enabled,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
