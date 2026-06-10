## 1. LLM驱动智能意图规划

- [x] 1.1 新增LLM Intent Planner专用System Prompt模板
- [x] 1.2 扩展DynamicIntentPlanner，优先调用LLM获取结构化结果
- [x] 1.3 实现Agent白名单校验+置信度过滤逻辑
- [x] 1.4 LLM不可用时自动回退到原有硬编码规则，完全向后兼容

## 2. 共享记忆版本系统

- [x] 2.1 SessionSharedMemory 新增 version 整数字段，初始值=1
- [x] 2.2 实现 snapshot() 方法，深copy当前状态存入version_history
- [x] 2.3 实现 restore(target_version) 方法，从历史快照恢复状态
- [x] 2.4 自动版本清理逻辑，最多保留最近3个版本历史

## 3. 增量编排引擎

- [x] 3.1 WorkflowOrchestrator 新增 incremental_mode 布尔开关，默认=False
- [x] 3.2 实现Agent前置检查：所有write_keys已存在且非空 → 直接跳过
- [x] 3.3 跳过Agent事件日志写入：step_skipped_already_cached
- [x] 3.4 支持 force_run_agent_names 参数，强制指定某些Agent必须重跑

## 4. Re-submit二次提交API

- [x] 4.1 新增 POST /api/orchestration/jobs/{job_id}/re-submit 端点
- [x] 4.2 自动打当前状态快照 → LLM增量意图规划 → 推导最小Agent子集
- [x] 4.3 支持 added_assets 新上传素材参数，增量索引新素材
- [x] 4.4 完整向后兼容，旧create_job接口完全不受影响
