from __future__ import annotations
import copy
import time
import uuid
import threading
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum


class MemoryKey(Enum):
    REFERENCE_ANALYSIS = "reference_analysis"
    ASSET_INDEX = "asset_index"
    SLOT_MATCHES = "slot_matches"
    GAPS = "gaps"
    RESOLVED_GAPS = "resolved_gaps"
    EDIT_TIMELINE = "edit_timeline"


class EventType(Enum):
    STEP_START = "step_start"
    STEP_PHASE = "step_phase"
    STEP_DELTA = "step_delta"
    STEP_WRITE = "step_write"
    STEP_WARNING = "step_warning"
    STEP_GAP = "step_gap"
    STEP_SKIP = "step_skip"
    STEP_FAIL = "step_fail"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    FAILED = "failed"


class JobStatus(Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentDependencyUnsatisfiedError(RuntimeError):
    """Agent依赖的前置条件永远无法满足时抛出的明确异常"""
    pass


@dataclass
class UploadedVideo:
    """上传视频数据结构，明确标记样例/素材"""
    original_filename: str
    saved_filename: str
    storage_path: str
    content_type: Optional[str]
    file_size_bytes: int
    is_reference: bool = False
    notes: Optional[str] = None


@dataclass
class MemoryEntryMeta:
    produced_by: str
    produced_at: float
    confidence: float = 1.0
    source_refs: List[str] = field(default_factory=list)


@dataclass
class MemoryEntry:
    data: Any
    meta: MemoryEntryMeta
    is_ready: bool = True


@dataclass
class WorkflowEvent:
    event_id: str
    event_type: str
    agent_name: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotData:
    version: int
    created_at: float
    data_dict: Dict[str, Any]


@dataclass
class SessionSharedMemory:
    session_id: str
    created_at: float
    entries: Dict[str, MemoryEntry] = field(default_factory=dict)
    event_log: List[WorkflowEvent] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=lambda: {
        "user_prompt": "",
        "uploaded_videos": [],
        "selected_reference_video_id": None,
        "requested_variant_id": None,
    })
    version: int = 1
    version_history: List[SnapshotData] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False, compare=False)

    def set_input_user_prompt(self, prompt: str):
        """设置用户原始自然语言输入"""
        with self._lock:
            self.inputs["user_prompt"] = prompt

    def set_selected_reference_video_id(self, video_id: Optional[str]):
        """设置当前选中的参考样例视频ID，供后续参考分析优先使用"""
        with self._lock:
            self.inputs["selected_reference_video_id"] = video_id

    def append_uploaded_video(self, video: UploadedVideo):
        """追加一个上传视频到inputs.uploaded_videos数组"""
        video_dict = {
            "original_filename": video.original_filename,
            "saved_filename": video.saved_filename,
            "storage_path": video.storage_path,
            "content_type": video.content_type,
            "file_size_bytes": video.file_size_bytes,
            "is_reference": video.is_reference,
            "notes": video.notes,
        }
        with self._lock:
            self.inputs["uploaded_videos"].append(video_dict)

    def set_requested_variant_id(self, variant_id: Optional[str]):
        with self._lock:
            self.inputs["requested_variant_id"] = variant_id

    def remove_uploaded_video(self, saved_filename: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            videos = self.inputs.get("uploaded_videos", [])
            for index, video in enumerate(videos):
                if video.get("saved_filename") == saved_filename:
                    return videos.pop(index)
        return None

    def set(self, key: str, data: Any, produced_by: str, confidence: float = 1.0, source_refs: List[str] = None):
        """写入一级key到共享记忆"""
        with self._lock:
            self.entries[key] = MemoryEntry(
                data=data,
                meta=MemoryEntryMeta(
                    produced_by=produced_by,
                    produced_at=time.time(),
                    confidence=confidence
                ),
                is_ready=True
            )

    def get(self, key: str) -> Optional[Any]:
        """读取一级key"""
        entry = self.entries.get(key)
        if entry and entry.is_ready:
            return entry.data
        return None

    def get_nested(self, key_path: str) -> Any:
        """
        支持点号分隔的嵌套key路径穿透取值
        示例: get_nested("inputs.uploaded_videos") → 直接返回inputs子域下的uploaded_videos
        """
        parts = key_path.split(".")
        if not parts:
            return None

        first_key = parts[0]
        if first_key == "inputs":
            current = self.inputs
        else:
            entry = self.entries.get(first_key)
            if not entry or not entry.is_ready:
                return None
            current = entry.data

        for part in parts[1:]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def append_event(self, event_type: str, agent_name: str, payload: Dict[str, Any] = None):
        evt = WorkflowEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            agent_name=agent_name,
            timestamp=time.time(),
            payload=payload or {}
        )
        with self._lock:
            self.event_log.append(evt)

    def _ensure_asset_index_initialized(self, agent_name: str):
        """确保 asset_index 结构已初始化，如果不存在则初始化空数组"""
        if "asset_index" not in self.entries:
            self.entries["asset_index"] = MemoryEntry(
                data={"assets": []},
                meta=MemoryEntryMeta(
                    produced_by=agent_name,
                    produced_at=time.time()
                ),
                is_ready=True
            )

    def append_to_array(self, key: str, array_path: str, item: Any, agent_name: str):
        """
        追加新条目到现有数组（如 asset_index.assets）
        参数：
            key: 一级键（如 "asset_index"）
            array_path: 数组在 data 中的嵌套路径（如 "assets"）
            item: 要追加的条目
            agent_name: 产生该条目的 agent 名称
        """
        with self._lock:
            self._ensure_asset_index_initialized(agent_name)

            # 找到数组位置
            entry = self.entries.get(key)
            if not entry:
                return

            # 解析嵌套路径找到数组
            parts = array_path.split(".")
            current = entry.data
            for part in parts[:-1]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return

            last_part = parts[-1]
            if isinstance(current, dict) and last_part in current and isinstance(current[last_part], list):
                current[last_part].append(item)

            # 更新 produced_at
            entry.meta.produced_at = time.time()

    def snapshot(self) -> int:
        """全量深拷贝当前状态，存入version_history，返回新的版本号"""
        with self._lock:
            snapshot_dict = {
                "session_id": self.session_id,
                "created_at": self.created_at,
                "inputs": copy.deepcopy(self.inputs),
                "entries": copy.deepcopy({k: asdict(v) for k, v in self.entries.items()}),
                "event_log": [asdict(e) for e in self.event_log]
            }
            new_version = self.version + 1
            self.version_history.append(SnapshotData(
                version=new_version,
                created_at=time.time(),
                data_dict=snapshot_dict
            ))
            # 自动清理：最多保留最近3个版本
            if len(self.version_history) > 3:
                self.version_history = self.version_history[-3:]
            self.version = new_version
            print(f"[INFO] 共享记忆已打快照 v{new_version}, 历史版本数={len(self.version_history)}")
            return new_version

    def restore(self, target_version: int) -> bool:
        """从历史快照恢复到指定版本号，成功返回True"""
        with self._lock:
            for snap in reversed(self.version_history):
                if snap.version == target_version:
                    d = snap.data_dict
                    self.inputs = copy.deepcopy(d["inputs"])
                    self.entries = {
                        k: MemoryEntry(
                            data=e["data"],
                            meta=MemoryEntryMeta(**e["meta"]),
                            is_ready=e.get("is_ready", True)
                        )
                        for k, e in d["entries"].items()
                    }
                    self.event_log = [WorkflowEvent(**e) for e in d["event_log"]]
                    self.version = target_version
                    print(f"[INFO] 共享记忆已从快照恢复到 v{target_version}")
                    return True
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "version": self.version,
            "created_at": self.created_at,
            "inputs": self.inputs,
            "entries": {
                k: {"data": e.data, "meta": asdict(e.meta), "is_ready": e.is_ready}
                for k, e in self.entries.items()
            },
            "event_log": [asdict(e) for e in self.event_log]
        }


memory_store: Dict[str, SessionSharedMemory] = {}


def get_or_create_shared_memory(session_id: str) -> SessionSharedMemory:
    if session_id not in memory_store:
        memory_store[session_id] = SessionSharedMemory(
            session_id=session_id,
            created_at=time.time()
        )
    return memory_store[session_id]
