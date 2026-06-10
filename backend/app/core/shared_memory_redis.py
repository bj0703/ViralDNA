from __future__ import annotations
import copy
import json
import time
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Type, TypeVar

from backend.app.core.shared_memory import (
    SessionSharedMemory, WorkflowEvent, MemoryEntry, MemoryEntryMeta, SnapshotData
)
from backend.app.core.distributed_lock import DistributedLock
from backend.app.core.config import load_redis_config

REDIS_SHARED_MEM_TTL_SECONDS = 24 * 60 * 60  # 24h
REDIS_SNAPSHOT_TTL_SECONDS = 72 * 60 * 60  # 72h

_redis_client_instance: Optional[object] = None


def _get_redis_client():
    global _redis_client_instance
    if _redis_client_instance is not None:
        return _redis_client_instance
    config = load_redis_config()
    if not config.is_available:
        return None
    try:
        import redis
        _redis_client_instance = redis.from_url(config.redis_url)
        _redis_client_instance.ping()
        return _redis_client_instance
    except Exception:
        return None


class RedisMemoryStore:
    """
    完全透明兼容 SessionSharedMemory 接口，底层自动读写 Redis
    Redis 不可用时自动 fallback 回纯内存模式
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._redis = _get_redis_client()
        self._fallback_memory: Optional[SessionSharedMemory] = None
        if self._redis is None:
            self._fallback_memory = SessionSharedMemory(session_id=session_id, created_at=time.time())
        self._mem_key = f"job:{session_id}:shared_memory"
        self._events_key = f"job:{session_id}:events"
        self._lock = DistributedLock(f"lock:job:{session_id}")

    def _load_from_redis(self) -> Optional[Dict[str, Any]]:
        raw = self._redis.get(self._mem_key)
        if not raw:
            return None
        return json.loads(raw)

    def _save_to_redis(self, data: Dict[str, Any], ttl: int = REDIS_SHARED_MEM_TTL_SECONDS) -> None:
        self._redis.setex(self._mem_key, ttl, json.dumps(data, ensure_ascii=False))

    def _ensure_loaded(self) -> SessionSharedMemory:
        if self._fallback_memory is not None:
            return self._fallback_memory
        raw_data = self._load_from_redis()
        if raw_data is None:
            return SessionSharedMemory(session_id=self.session_id, created_at=time.time())
        d = raw_data
        mem = SessionSharedMemory(session_id=d.get("session_id", self.session_id), created_at=d.get("created_at", time.time()))
        mem.version = d.get("version", 1)
        mem.inputs = d.get("inputs", {"user_prompt": "", "uploaded_videos": [], "selected_reference_video_id": None, "requested_variant_id": None})
        mem.entries = {}
        for k, e_dict in d.get("entries", {}).items():
            mem.entries[k] = MemoryEntry(
                data=e_dict["data"],
                meta=MemoryEntryMeta(**e_dict["meta"]),
                is_ready=e_dict.get("is_ready", True)
            )
        mem.event_log = [WorkflowEvent(**e) for e in d.get("event_log", [])]
        mem.version_history = []
        return mem

    def _sync_back(self, mem: SessionSharedMemory) -> None:
        if self._fallback_memory is not None:
            return
        self._save_to_redis(mem.to_dict())

    @property
    def inputs(self):
        mem = self._ensure_loaded()
        return mem.inputs

    @property
    def version(self):
        mem = self._ensure_loaded()
        return mem.version

    @property
    def version_history(self):
        mem = self._ensure_loaded()
        return mem.version_history

    @property
    def entries(self):
        mem = self._ensure_loaded()
        return mem.entries

    def set_input_user_prompt(self, prompt: str) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.set_input_user_prompt(prompt)
            self._sync_back(mem)

    def set_selected_reference_video_id(self, video_id: Optional[str]) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.set_selected_reference_video_id(video_id)
            self._sync_back(mem)

    def set_requested_variant_id(self, variant_id: Optional[str]) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.set_requested_variant_id(variant_id)
            self._sync_back(mem)

    def set_input_user_prompt(self, prompt: str) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.set_input_user_prompt(prompt)
            self._sync_back(mem)

    def append_uploaded_video(self, video) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.append_uploaded_video(video)
            self._sync_back(mem)

    def remove_uploaded_video(self, saved_filename: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            mem = self._ensure_loaded()
            removed = mem.remove_uploaded_video(saved_filename)
            if removed is not None:
                self._sync_back(mem)
            return removed

    def set(self, key: str, data: Any, produced_by: str, confidence: float = 1.0, source_refs: List[str] = None) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.set(key, data, produced_by, confidence, source_refs)
            self._sync_back(mem)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            mem = self._ensure_loaded()
            return mem.get(key)

    def get_nested(self, key_path: str) -> Any:
        with self._lock:
            mem = self._ensure_loaded()
            return mem.get_nested(key_path)

    def append_event(self, event_type: str, agent_name: str, payload: Dict[str, Any] = None) -> None:
        evt = WorkflowEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            agent_name=agent_name,
            timestamp=time.time(),
            payload=payload or {}
        )
        with self._lock:
            mem = self._ensure_loaded()
            mem.event_log.append(evt)
            if self._redis is not None:
                self._redis.rpush(self._events_key, json.dumps(asdict(evt), ensure_ascii=False))
                self._redis.expire(self._events_key, REDIS_SHARED_MEM_TTL_SECONDS)
            self._sync_back(mem)

    def append_to_array(self, key: str, array_path: str, item: Any, agent_name: str) -> None:
        with self._lock:
            mem = self._ensure_loaded()
            mem.append_to_array(key, array_path, item, agent_name)
            self._sync_back(mem)

    def snapshot(self) -> int:
        with self._lock:
            mem = self._ensure_loaded()
            new_version = mem.snapshot()
            if self._redis is not None:
                snap_key = f"job:{self.session_id}:snapshots:{new_version}"
                latest_snap = mem.version_history[-1]
                self._redis.setex(snap_key, REDIS_SNAPSHOT_TTL_SECONDS, json.dumps(latest_snap.data_dict, ensure_ascii=False))
            self._sync_back(mem)
            return new_version

    def restore(self, target_version: int) -> bool:
        with self._lock:
            mem = self._ensure_loaded()
            ok = mem.restore(target_version)
            if ok:
                self._sync_back(mem)
            return ok

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            mem = self._ensure_loaded()
            return mem.to_dict()

    def get_new_events_since(self, offset: int) -> List[Dict[str, Any]]:
        if self._redis is not None:
            raw_events = self._redis.lrange(self._events_key, offset, -1) or []
            return [json.loads(e) for e in raw_events]
        else:
            mem = self._ensure_loaded()
            return [asdict(e) for e in mem.event_log[offset:]]


_memory_store_redis: Dict[str, RedisMemoryStore] = {}


def get_or_create_shared_memory_redis(session_id: str) -> RedisMemoryStore:
    if session_id not in _memory_store_redis:
        _memory_store_redis[session_id] = RedisMemoryStore(session_id)
    return _memory_store_redis[session_id]
