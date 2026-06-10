## Context

当前项目为 Agent 动态编排的爆款视频结构迁移引擎，核心数据流为：上传视频 → 多Agent串行执行生成分析结果 → 增量二次提交 → 最终渲染出片。现有共享记忆存储为 Python 全局 Dict，绑定进程生命周期；前端通过每1.5秒轮询 `/api/orchestration/jobs/{job_id}` 获取全量状态。存在痛点：服务重启Job全丢、多实例无法共享状态、轮询延迟高带宽浪费。

## Goals / Non-Goals

**Goals:**
- 无缝替换进程内 Dict 为 Redis 持久化存储，上层 Agent 业务代码零改动
- 新增 SSE 事件流，Agent 事件毫秒级推送到前端，轮询延迟从 1.5s 降到 < 500ms
- 自动 TTL 24h 清理过期 Job，防止 Redis 内存泄漏
- 使用 Redlock 分布式锁替代原生 threading.Lock，支持多实例横向扩展
- 完全向后兼容，原有 REST API 保留不删除，前端可渐进式升级

**Non-Goals:**
- 不引入 WebSocket 全双工通信，SSE 单向推送足够覆盖当前场景
- 不把大视频文件存入 Redis，仅存路径元数据，视频文件继续走磁盘/OSS
- 不重构现有 Agent 编排逻辑，透明无侵入改造

## Decisions

1. **存储选型：Redis 单节点 + JSON 序列化**
   - 方案对比：JSON vs Protobuf vs RedisHash → 选 JSON，可读性强调试方便，不用额外引入序列化依赖
   - 优势：可以直接用 Python 标准 json 库，前端拿到数据结构和现有完全一致

2. **Redis Key 设计规范**
   - Job 完整共享记忆：`job:{job_id}:shared_memory` → TTL 24h
   - Job 执行计划状态：`job:{job_id}:plan` → TTL 24h
   - 事件流 List：`job:{job_id}:events` → TTL 24h，LRANGE 增量取
   - 版本快照：`job:{job_id}:snapshots:{version}` → TTL 72h
   - 分布式锁 Key：`lock:job:{job_id}` → 持有超时 10s

3. **SSE 断点续传协议**
   - 请求路径：`GET /api/orchestration/jobs/{job_id}/stream?last_event_id=N`
   - 增量拉取偏移量从 last_event_id 下标开始，自动重连不会丢事件
   - 兼容多轮对话，同个 SSE 连接在 re-submit 第二轮后继续复用不用断连

4. **降级兜底策略**
   - Redis 连接失败时自动 fallback 回原有内存 Dict 模式，保证服务可用
   - 前端 EventSource 连接失败自动回退到原有轮询逻辑，体验零中断

## Risks / Trade-offs

- [Risk] Redis 挂掉导致所有 Job 状态丢失 → Mitigation：开启 RDB 持久化每5分钟快照，降级自动回内存模式
- [Risk] SSE 长连接占用连接数过多 → Mitigation：Nginx 配置 10 分钟超时自动断连，前端指数退避重连
- [Risk] 序列化/反序列化大对象性能损耗 → Mitigation：只增量更新变更字段，不需要每次全量覆盖写回
- [Trade-off] 引入 Redis 额外部署依赖 → 换取服务重启不丢数据 + 多实例扩展能力，收益远大于成本
