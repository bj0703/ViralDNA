from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


class BaseAgent(ABC):
    """Common base class for workflow agents."""

    read_keys: List[str]
    write_keys: List[str]

    def __init__(self) -> None:
        self._stream_callback: Optional[Callable[[str], None]] = None
        self._event_callback: Optional[Callable[[str, Dict[str, object]], None]] = None

    def set_stream_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        self._stream_callback = callback

    def set_event_callback(
        self,
        callback: Optional[Callable[[str, Dict[str, object]], None]],
    ) -> None:
        self._event_callback = callback

    def emit_stream_delta(self, delta: str) -> None:
        if self._stream_callback and delta:
            self._stream_callback(delta)

    def emit_phase(
        self,
        phase: str,
        title: str,
        detail: str = "",
        data: Optional[Dict[str, object]] = None,
    ) -> None:
        if self._event_callback:
            payload: Dict[str, object] = {
                "phase": phase,
                "title": title,
                "detail": detail,
            }
            if data:
                payload["data"] = data
            self._event_callback("step_phase", payload)

    @abstractmethod
    def analyze(self, shared_memory: SessionSharedMemory) -> dict:
        raise NotImplementedError
