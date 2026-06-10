# Frontend SSE Hook Specification

## 1. Overview
实现一个自定义 React Hook `useSSEEventSource`，完全自动管理 SSE 长连接的生命周期，支持断点续传、指数退避重连，连接失败自动降级到轮询兜底。

## 2. Requirements

### 2.1 Core Behavior
- Hook 接收 `jobId` 参数，当 jobId 非空时自动建立 SSE 连接：`GET /api/orchestration/jobs/{jobId}/stream?last_event_id=<offset>`
- 当 jobId 变为 null 时自动关闭连接释放资源
- 组件卸载时自动关闭 EventSource，无内存泄漏

### 2.2 Reconnection Strategy
- 首次连接失败等待 1s 重连
- 第二次失败等待 2s
- 第三次失败等待 4s
- 第四次及之后失败等待 8s
- 累计连续失败 >= 3 次后，自动切换到轮询兜底模式，每 1.5s 拉取一次事件
- 轮询模式下，每次成功拉取到事件后保留重连能力，SSE 恢复可用时自动切回正常长连接模式

### 2.3 Resumable Transmission
- **游标统一为整数 offset**，而非事件 UUID 字符串
- Redis 事件队列底层用 `LRANGE events offset -1` 直接从指定下标开始续传，零遍历成本
- 每次收到事件后 `lastEventOffset += 1`，重连时通过 query param 直接携带给后端：`/stream?last_event_id=N`
- 不会丢失任何中间产生的事件

### 2.4 Event Payload
SSE 事件类型统一为 JSON 结构：
```typescript
interface SSEEventPayload {
  event_id: string
  event_type: 'plan_ready' | 'step_start' | 'step_write' | 'step_skip' | 'step_fail' | 'resource_updated' | 'timeline_updated'
  agent_name?: string
  payload: Record<string, unknown> // 100% 对齐后端 WorkflowEvent，不再混用 data
  timestamp: number
}
```

### 2.5 API
```typescript
function useSSEEventSource(options: {
  jobId: string | null;
  onEvent?: (event: SSEEventPayload) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onFallbackPollStart?: () => void;
  pollIntervalMs?: number;
}): {
  isConnected: boolean
  isFallbackPolling: boolean
  lastEventOffset: number
}
```

## 3. Acceptance Criteria
- jobId 变化时自动切换到对应 job 的事件流，offset 自动重置为 0
- 网络断开重连后从上次 offset 位置继续续传，不会丢失任何事件
- 连续 3 次 SSE 失败后自动切到轮询模式
- 组件 unmount 后浏览器开发者工具网络面板中无残留未关闭连接
