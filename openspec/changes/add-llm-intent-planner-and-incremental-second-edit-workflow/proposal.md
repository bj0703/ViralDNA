## Why

当前系统意图规划完全依赖硬编码关键词匹配，灵活性不足，无法理解复杂自然语言指令；且第一次生成视频后用户提出二次修改需求时必须全量重跑所有Agent，效率很低，无法实现快速迭代修改的闭环体验。

## What Changes

- 新增LLM驱动智能意图规划，完全替代现有硬编码规则，理解任意用户自然语言指令自动选择需要执行的Agent子集
- 新增共享记忆版本快照机制，每次用户提交新需求自动打版本号，保留历史状态支持任意版本回退
- 扩展WorkflowOrchestrator支持增量执行模式：检测已存在的输出key直接跳过对应Agent，不重复跑无意义的计算
- 新增Re-submit二次提交API接口，用户在已有Job基础上提交新需求直接增量生成下一版视频
- 所有原有规则逻辑完整保留作为fallback兜底，LLM不可用时自动降级，100%向后兼容

## Capabilities

### New Capabilities
- `llm-driven-intent-planning`: LLM智能意图规划，基于上下文动态生成Agent执行计划，替代硬编码关键词匹配
- `shared-memory-versioning`: 共享记忆版本快照系统，支持版本管理与历史状态回退
- `incremental-orchestration`: 增量编排引擎，自动跳过已缓存结果的Agent，仅执行必要的下游依赖
- `re-submit-second-edit-api`: 二次提交API接口，用户快速提交新需求生成第2版及后续迭代视频

### Modified Capabilities
- 无破坏性变更，所有修改完全向后兼容

## Impact

- `backend/app/services/intent_planner.py` - 扩展加入LLM智能规划逻辑，保留原有规则作为fallback
- `backend/app/core/shared_memory.py` - 新增版本号字段和快照管理方法
- `backend/app/agents/orchestrator.py` - 扩展WorkflowOrchestrator支持增量跳过检测
- `backend/app/api/routes/orchestration.py` - 新增/re-submit二次提交端点
