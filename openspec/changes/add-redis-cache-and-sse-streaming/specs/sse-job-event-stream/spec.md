# SSE Job Event Stream Specification

## 概述
Server-Sent Events 实时事件流接口，替代前端轮询，毫秒级推送Job状态和事件日志。

## 需求

### 功能需求
1. 端点：`GET /api/orchestration/jobs/{job_id}/stream`
   - 可选查询参数 `last_event_id`：从该下标后开始续传事件，默认从0开始
2. Content-Type: text/event-stream
3. 推送事件格式：
   ```
   data: {"event_id": "...", "event_type": "step_start", "agent_name": "...", "timestamp": ...}\n\n
   ```
4. 自动增量追加，新事件产生后立刻推送到前端
5. 支持多轮re-submit场景，同个SSE连接在第二轮执行时继续复用，无需重连
6. 连接断开后前端携带last_event_id重连，自动从断开位置续传，不丢任何事件

### 非功能需求
- 事件推送延迟 < 500ms
- 完全向后兼容原有轮询接口，前端可渐进式切换
- 空闲时每30秒发送一条 `: heartbeat\n\n` 防止代理断开连接
