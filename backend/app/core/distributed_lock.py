from __future__ import annotations
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from backend.app.core.config import load_redis_config

_redis_client: Optional[object] = None
_fallback_lock_store: dict[str, threading.Lock] = {}
_global_fallback_lock = threading.Lock()


def _get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    config = load_redis_config()
    if not config.is_available:
        return None

    try:
        import redis
        _redis_client = redis.from_url(config.redis_url)
        _redis_client.ping()
        print(f"[INFO] Redis 连接成功: {config.redis_url}")
        return _redis_client
    except Exception as e:
        print(f"[WARN] Redis 连接失败，自动降级回本地线程锁模式: {e}")
        return None


class DistributedLock:
    def __init__(self, lock_key: str, timeout_seconds: int = 10, retry_count: int = 3, retry_delay_ms: int = 50):
        self.lock_key = lock_key
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_ms / 1000.0
        self.lock_value = str(uuid.uuid4())
        self._redis_lock = None
        self._fallback_lock: Optional[threading.Lock] = None

        redis_client = _get_redis_client()
        if redis_client is not None:
            # 直接从已连接的 Redis 客户端实例获取锁，不是从模块上获取
            self._redis_lock = redis_client.lock(
                name=self.lock_key,
                timeout=self.timeout_seconds,
                thread_local=False
            )
        else:
            with _global_fallback_lock:
                if self.lock_key not in _fallback_lock_store:
                    _fallback_lock_store[self.lock_key] = threading.Lock()
                self._fallback_lock = _fallback_lock_store[self.lock_key]

    def acquire(self, blocking: bool = True) -> bool:
        if self._redis_lock is not None:
            return self._redis_lock.acquire(
                blocking=blocking,
                blocking_timeout=self.timeout_seconds
            )
        else:
            if not blocking:
                return self._fallback_lock.acquire(blocking=False)
            for _ in range(self.retry_count):
                if self._fallback_lock.acquire(blocking=False):
                    return True
                time.sleep(self.retry_delay_seconds)
            return self._fallback_lock.acquire(blocking=True)

    def release(self) -> None:
        if self._redis_lock is not None:
            self._redis_lock.release()
        else:
            self._fallback_lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


@contextmanager
def distributed_job_lock(job_id: str) -> Generator[None, None, None]:
    lock = DistributedLock(f"lock:job:{job_id}")
    with lock:
        yield
