## Context

当前后端现状：
- SampleAnalysis 体系已完整可用，但仅支持单视频分析
- Agent Orchestration 框架已搭建（orchestrator.py, shared_memory.py），但只注册了1个可用Agent，剩下4个全是占位的幽灵Agent
- IntentPlanner 硬编码返回5个Agent名字，完全不具备动态规划能力
- 上传的视频没有明确类型标记，无法区分用户上传的是"参考样例"还是"待迁移素材"
- 两套体系完全独立，数据零互通

## Goals / Non-Goals

**Goals:**
- 实现全部5个真实可用的Agent，覆盖从样例分析→素材索引→槽位匹配→缺口补齐→最终剪辑时间线生成的完整流水线
- 强化 SessionSharedMemory，新增 inputs 子域，为每个上传视频增加 `is_reference: bool` 标记字段
- 重写 DynamicIntentPlanner，基于 user_prompt + 共享记忆当前状态动态决定下一批 Agent 执行列表
- 修复 WorkflowOrchestrator 的异步问题，用拓扑排序自动满足依赖条件后执行 Agent
- 所有 Agent 统一遵循标准接口定义 read_keys/write_keys，自动从共享记忆取数、结果写回

**Non-Goals:**
- 不引入外部队列/数据库依赖，保持纯内存实现适合本地开发
- 不删除现有 sample-analysis 接口，保持 100% 向后兼容
- 本次不做复杂的 Agent 迭代循环，第一轮先保证 DAG 拓扑顺序一次性跑完，后续再扩展多轮迭代

## Decisions

| 决策 | 方案A | 方案B | 最终选择 | 理由 |
|---|---|---|---|---|
| Agent 接口规范 | 每个 Agent 定义 BaseAgent 抽象基类，继承实现 | 用 dataclass + 工厂函数直接注册 | 方案A | 统一接口，保证所有 Agent 都有 read_keys/write_keys 属性和 analyze 方法 |
| 5个Agent 精确读写键定义 | 提前固定全部5个Agent的键映射 | 运行时动态推导 | 方案A | 确定性高，DAG图结构清晰，不需要复杂推导逻辑 |
| 嵌套key路径支持 | 点号分隔 "inputs.uploaded_videos" 作为key | 仅支持一级扁平key | 方案A | inputs 子域是嵌套结构，点号路径可以直接穿透取值 |
| 拓扑排序失败处理 | 检测到依赖永远不满足 → 抛出明确异常 | 静默把剩余Agent塞进去执行 | 方案A | 快速失败，用户立刻知道哪个Agent缺少前置条件，避免静默失败 |
| 上传视频类型标记 | 新增 `video_type: Enum("reference", "asset")` 字段 | 仅用布尔值 `is_reference: bool` | 方案B | 简洁明了，当前只有两类，后续扩展用 Enum |
| 多视频样例数量边界校验 | 0个样例→跳过ReferenceAnalyzerAgent，≥2个样例→取第一个打warning | 强制必须有且只有1个样例 | 方案A | 容错性好，覆盖"仅素材索引"场景 |
| 拓扑排序实现 | 复用现有 _resolve_dependency_order，遍历依赖关系图自动排序，升级支持嵌套key | 手动硬编码执行顺序 | 方案A | 动态自动排序，新增 Agent 无需改排序逻辑 |
| 异步处理 | BackgroundTasks 中直接跑同步代码，用 asyncio.to_thread 包装 | 全链路改成真正 async/await | 方案A | 最小改动兼容现有代码，避免大量同步逻辑改异步的侵入性变更 |
| 持久化 | 本次保持内存存储 | 引入 SQLite 持久化 | 方案A | 优先跑通全流程，后续迭代再加持久化 |

### 5个Agent 标准读写键表（提前约定）
| Agent | read_keys | write_keys | 过滤规则 |
|---|---|---|---|
| ReferenceAnalyzerAgent | `["inputs.uploaded_videos"]` | `["reference_analysis"]` | 只取 `is_reference=True` 的视频 |
| AssetIndexerAgent | `["inputs.uploaded_videos"]` | `["asset_index"]` | 只取 `is_reference=False` 的素材视频 |
| SlotMatcherAgent | `["reference_analysis", "asset_index"]` | `["slot_matches"]` | 无特殊过滤 |
| GapResolverAgent | `["slot_matches"]` | `["resolved_gaps"]` | 无特殊过滤 |
| EditPlannerAgent | `["reference_analysis", "asset_index", "resolved_gaps"]` | `["edit_timeline"]` | 无特殊过滤 |

## Risks / Trade-offs

[Risk] 5个 Agent 都依赖火山引擎 Ark 大模型 API，网络不稳定或配额耗尽会导致整个流水线中断 → Mitigation：每个 Agent 内部保留降级逻辑，失败时在共享记忆中写入部分结果并打上 warning，不直接崩溃
[Risk] 多个 Agent 并发写入共享记忆存在竞态条件 → Mitigation：第一轮用串行拓扑执行，同一时刻只有一个 Agent 在写，完全避免并发问题
[Trade-off] 全部保内存，服务重启所有任务丢失 → Mitigation：本地单用户场景完全接受，后续按需加持久化层

## Migration Plan

- 第一步：新增 BaseAgent 抽象基类，统一定义 5 个 Agent 的 read_keys/write_keys 标准
- 第二步：实现 4 个全新 Agent 文件（AssetIndexerAgent, SlotMatcherAgent, GapResolverAgent, EditPlannerAgent）
- 第三步：在 prompts 目录补充对应的 4 个新系统提示词文件
- 第四步：升级 SharedMemory 数据结构，新增 inputs 嵌套子域（inputs.user_prompt, inputs.uploaded_videos）
- 第五步：修复拓扑排序算法，支持点号分隔的嵌套key路径，不存在的依赖直接抛出明确异常不静默跳过
- 第六步：重写 DynamicIntentPlanner，支持动态生成执行计划和三种场景模式
- 第七步：改造 orchestration API 支持 multipart/form-data 文件上传 + is_reference 标记，补全样例数量边界校验
- 第八步：修复 Orchestrator 异步执行逻辑，Agent.analyze 传入完整 shared_memory 对象
- 第九步：更新 AgentRegistry 全部注册，端到端测试全流水线
