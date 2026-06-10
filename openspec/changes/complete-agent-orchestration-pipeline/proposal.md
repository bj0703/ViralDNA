## Why

当前后端存在两套完全独立的分析体系，Agent Orchestration 框架只搭了基础设施但所有真实Agent都是幽灵占位。现在把完整的爆款结构迁移全链路5个Agent全部实现，基于共享记忆动态执行流水线，让用户通过自然语言+多视频上传完成从样例分析→素材索引→槽位匹配→缺口补齐→剪辑时间线生成的完整闭环。同时明确区分上传文件中的参考样例视频和普通素材视频。

## What Changes

- 实现5个真实可用的Agent：ReferenceAnalyzerAgent、AssetIndexerAgent、SlotMatcherAgent、GapResolverAgent、EditPlannerAgent，每个都有独立Prompt和完整执行逻辑
- 升级SessionSharedMemory，增加inputs区域，支持标记每个上传视频的类型：is_reference（样例）或is_asset（普通素材）
- 重写DynamicIntentPlanner，基于user_prompt和共享记忆当前状态动态生成下一批Agent列表，不再返回硬编码幽灵Agent
- 修复WorkflowOrchestrator.run的async/await问题，用拓扑排序自动按依赖顺序执行Agent
- 新增API字段区分上传视频类型，支持用户指定哪个是参考样例，哪些是待迁移素材
- 保留sample-analysis老链路作为兼容，内部数据同步写入共享记忆

## Capabilities

### New Capabilities
- `multi-agent-pipeline`: 完整多Agent编排流水线，5个Agent基于共享记忆自动DAG拓扑执行
- `shared-memory-enhanced`: 增强版会话共享记忆，支持inputs区域、样例/素材区分、全链路event_log追踪
- `dynamic-intent-planner`: 动态意图规划器，根据用户自然语言输入+当前上下文动态决定执行哪些Agent

### Modified Capabilities
- `agent-orchestration`: 原有spec的实现被完全替换，从半残框架升级为真实可用的全链路编排系统

## Impact

- backend/app/agents/ 目录新增4个真实Agent实现文件
- backend/app/prompts/ 目录补充4个新Agent的系统Prompt
- backend/app/api/routes/orchestration.py 更新请求体支持视频类型标记
- backend/app/dependencies.py 更新AgentRegistry注册全部5个Agent
- 保留所有现有sample-analysis API接口向后兼容
