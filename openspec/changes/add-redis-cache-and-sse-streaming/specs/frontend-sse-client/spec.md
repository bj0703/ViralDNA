# Frontend SSE Client Specification

## 概述
前端EventSource客户端，消费SSE事件流，增量渲染Agent对话，体验无缝。

## 需求

### 功能需求
1. 封装 useSSEEventSource React Hook 管理连接生命周期
2. 自动记录最后收到的 eventId，重连时自动作为 last_event_id 参数携带
3. 指数退避重连策略：断开后1s → 2s → 4s → 8s，最多8秒不再递增
4. SSE连接失败自动降级回退到原有轮询逻辑，保证体验零中断
5. 增量追加新事件到对话面板，不用每次全量重渲染历史消息
6. 多轮对话场景下SSE连接保持不关闭，第二轮新事件直接追加显示

### 非功能需求
- 事件到达后UI渲染响应 < 100ms
- 内存无泄漏，组件卸载时自动关闭EventSource连接
