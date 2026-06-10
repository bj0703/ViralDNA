## Why

当前系统使用进程内 Python 字典存储所有 Job 共享记忆，服务重启数据完全丢失，不支持多实例横向扩展，前端轮询延迟高且浪费带宽。引入 Redis 高速缓存 + SSE 实时推送，解决数据持久化、分布式共享、多轮对话无缝体验三大核心问题。

## What Changes

- 新增 RedisMemoryStore 替换原有 `memory_store: Dict` 内存字典，全透明兼容上层业务代码
- 新增 SSE Server-Sent Events 事件流接口，替换前端轮询，毫秒级实时推送 Agent 进度
- Redis 中 Job 共享记忆自动 TTL 过期清理，防止内存泄漏
- 支持分布式锁替代原有线程锁，多实例部署无并发竞态问题
- 前端新增 EventSource 增量事件流消费逻辑，按需拉取新事件无需全量同步

## Capabilities

### New Capabilities
- `redis-shared-memory-store`: 基于 Redis 的共享记忆持久化存储层，透明替换现有内存字典
- `sse-job-event-stream`: SSE 实时事件流接口，支持断点续传增量推送 Job 状态和事件日志
- `distributed-lock-manager`: Redis 分布式锁实现，替代 threading.Lock 保证并发安全
- `frontend-sse-client`: 前端 EventSource 客户端消费逻辑，增量渲染多轮对话事件

### Modified Capabilities
(无现有功能变更，向后完全兼容)

## Impact

- `backend/app/core/shared_memory.py` 核心模块扩展 Redis 实现
- `backend/app/api/routes/orchestration.py` 新增 SSE 流接口端点
- 依赖新增：`redis-py` Python SDK
- 前端组件新增 EventSource 连接管理逻辑
- .env 配置文件新增 Redis 连接配置项
