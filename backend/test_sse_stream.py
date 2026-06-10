"""
SSE事件流测试脚本
直接连接后端SSE接口，实时打印收到的事件和心跳包
"""
import sys
import time

try:
    import requests
except ImportError:
    print("[ERROR] 需要先安装 requests: pip install requests")
    sys.exit(1)

SSE_URL = "http://127.0.0.1:8000/api/orchestration/jobs/demo_001/stream?last_event_id=0"

print("=" * 60)
print(f"正在连接 SSE 流: {SSE_URL}")
print("=" * 60)

try:
    resp = requests.get(
        SSE_URL,
        stream=True,
        headers={"Accept": "text/event-stream"},
        timeout=60
    )
    print(f"[OK] 连接成功! status={resp.status_code}\n")

    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8")
        if decoded.startswith(":"):
            print(f"[心跳] {time.strftime('%H:%M:%S')} 收到心跳包")
        elif decoded.startswith("data:"):
            data = decoded[5:].strip()
            if data:
                print(f"[事件] {time.strftime('%H:%M:%S')} {data}")

except KeyboardInterrupt:
    print("\n\n[OK] 用户断开连接，测试结束")
except Exception as e:
    print(f"\n[FAIL] 连接出错: {e}")
