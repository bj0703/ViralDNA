# Incremental Orchestration Specification

## Summary
增量编排引擎，自动检测已存在的缓存结果，直接跳过对应Agent，不重复执行无意义的计算。

## Requirements
- WorkflowOrchestrator 新增 incremental_mode 布尔开关，默认False（保持原有全量执行行为不变）
- Agent执行前自动检查：该Agent所有write_keys是否都已在shared_memory中存在且非空 → 满足条件直接跳过该Agent
- 跳过Agent时写入事件日志："step_skipped_already_cached"，说明跳过原因
- 支持force_run_agent_names参数，用户可以强制指定某些Agent必须重新执行，绕过自动跳过逻辑
- 拓扑排序逻辑完全复用原有代码，增量跳过只在执行阶段生效
