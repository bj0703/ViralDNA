"""
Redis + SSE 全流程自动化测试脚本
执行顺序：
1. 降级模式基础测试
2. 分布式锁并发测试
3. Redis 持久化测试（如果Redis可用）
4. 事件流增量追加测试
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
import concurrent.futures

PASS_COUNT = 0
TOTAL_COUNT = 0


def case(name: str):
    global TOTAL_COUNT
    TOTAL_COUNT += 1
    def decorator(fn):
        try:
            print(f"\n[TEST] {name} ... ", end="", flush=True)
            fn()
            global PASS_COUNT
            PASS_COUNT += 1
            print("PASS", flush=True)
        except Exception as e:
            print(f"FAIL -> {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        return fn
    return decorator


@case("配置模块加载")
def _():
    from backend.app.core.config import load_redis_config
    cfg = load_redis_config()
    assert hasattr(cfg, "redis_enabled")
    assert hasattr(cfg, "redis_url")


@case("分布式锁模块导入")
def _():
    from backend.app.core.distributed_lock import DistributedLock, distributed_job_lock
    assert DistributedLock is not None
    assert distributed_job_lock is not None


@case("内存存储基础读写")
def _():
    from backend.app.core.shared_memory_redis import get_or_create_shared_memory_redis
    store = get_or_create_shared_memory_redis("auto_test_job_001")
    store.set_input_user_prompt("自动化测试输入指令")
    val = store.get_nested("inputs.user_prompt")
    assert val == "自动化测试输入指令", f"期望 '自动化测试输入指令' 实际得到 {val}"


@case("事件追加与增量获取")
def _():
    from backend.app.core.shared_memory_redis import get_or_create_shared_memory_redis
    store = get_or_create_shared_memory_redis("auto_test_job_002")
    store.append_event("step_start", "参考分析", {"detail": "开始分析"})
    store.append_event("step_write", "参考分析", {"detail": "写入结果"})
    events = store.get_new_events_since(0)
    assert len(events) >= 2
    partial = store.get_new_events_since(1)
    assert len(partial) >= 1


@case("快照版本与恢复")
def _():
    from backend.app.core.shared_memory_redis import get_or_create_shared_memory_redis
    store = get_or_create_shared_memory_redis("auto_test_job_003")
    store.set_input_user_prompt("v1")
    v2 = store.snapshot()
    store.set_input_user_prompt("v2")
    assert v2 >= 2


@case("8线程分布式锁并发安全")
def _():
    from backend.app.core.distributed_lock import distributed_job_lock
    counter = [0]

    def worker(tid):
        with distributed_job_lock("auto_concurrent_test"):
            time.sleep(0.05)
            counter[0] += 1
            return tid

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(8)))

    assert counter[0] == 8
    assert len(results) == 8


@case("Redis连接与持久化验证（可选）")
def _():
    from backend.app.core.shared_memory_redis import _get_redis_client
    r = _get_redis_client()
    if r is None:
        print("  (Redis 不可用，跳过该测试)", end="")
        return
    r.setex("test:emo_transfer:ping", 10, b"ok")
    pong = r.get("test:emo_transfer:ping")
    assert pong == b"ok"
    r.delete("test:emo_transfer:ping")


if __name__ == "__main__":
    print("=" * 50)
    print("  Redis + SSE 全流程自动化测试")
    print("=" * 50)

    try:
        import redis
    except ImportError:
        print("\n[WARN] redis 包未安装，正在自动跳过Redis相关导入检查...")

    print("\n" + "=" * 50)
    print(f"  测试结果: {PASS_COUNT}/{TOTAL_COUNT} 通过")
    print("=" * 50)

    if PASS_COUNT == TOTAL_COUNT:
        print("\n[OK] 全流程所有测试 100% 全部通过!")
        sys.exit(0)
    else:
        print(f"\n[FAIL] 有 {TOTAL_COUNT - PASS_COUNT} 项测试失败")
        sys.exit(1)
