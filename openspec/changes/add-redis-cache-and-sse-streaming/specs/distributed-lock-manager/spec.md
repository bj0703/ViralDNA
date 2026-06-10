# Distributed Lock Manager Specification

## 概述
基于Redis Redlock实现分布式锁，替换原有进程内threading.Lock，支持多实例并发安全。

## 需求

### 功能需求
1. 锁 Key 规范：`lock:job:{job_id}`
2. 持有超时时间：10秒，防止死锁
3. 支持 with 上下文管理器自动加锁/解锁
4. 加锁失败自动重试3次，每次间隔50ms
5. Redis不可用时自动降级回退到原有threading.Lock模式，保证单实例场景正常运行
6. 锁粒度精确到单个Job，不同Job之间完全不冲突

### 非功能需求
- 锁开销 < 10ms
- 无死锁风险
