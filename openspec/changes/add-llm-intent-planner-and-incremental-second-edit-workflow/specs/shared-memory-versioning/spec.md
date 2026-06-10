# Shared Memory Versioning Specification

## Summary
共享记忆版本快照系统，每次用户提交新需求自动打版本号，保存完整历史状态，支持任意版本回退。

## Requirements
- SessionSharedMemory 新增 version 整数字段，首次初始化值为1
- 新增 snapshot() 方法，深copy整个当前shared_memory字典，保存到version_history数组中
- 新增 restore(target_version) 方法，从历史快照恢复回指定版本号状态
- 每个Job自动保留最近最多3个版本历史，超过自动清理最旧的版本
- 每次Re-submit新需求时，自动先打vN快照，再开始新的增量执行
