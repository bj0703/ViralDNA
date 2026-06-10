# Redis Shared Memory Store Specification

## 概述
透明替换原有进程内 Dict 内存存储，将 SessionSharedMemory 全量持久化到 Redis，上层业务代码无需任何改动。

## 需求

### 功能需求
1. 完全兼容原有 `SessionSharedMemory` 类的所有公开接口，方法签名、参数返回值100%对齐
2. Redis Key 规范：
   - `job:{job_id}:shared_memory` → 完整共享记忆 JSON，TTL 24h
   - `job:{job_id}:events` → List 事件日志，TTL 24h
   - `job:{job_id}:snapshots:{version}` → 版本快照 JSON，TTL 72h
3. get_or_create_shared_memory() 优先从 Redis 读取，不存在则新建再写入
4. 每次写操作自动刷新 TTL，延长生命周期
5. Redis 连接失败时自动降级 fallback 回原有内存 Dict 模式，保证服务完全可用

### 非功能需求
- 序列化/反序列化耗时 < 50ms
- 向后100%兼容，原有 REST API `/jobs/{job_id}` 行为无任何变化
