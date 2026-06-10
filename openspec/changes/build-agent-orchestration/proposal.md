## Why

当前系统只完成了样例理解这条上游链路（`ReferenceAnalyzerAgent` 输出结构化样例分析）。但 `prd.md` 的核心是"从样例迁移到新内容"，这需要素材分析、槽位匹配、缺口补齐、剪辑编排等多个 agent 协作。`prompt.md` 中已经为 `AssetAnalyzer`、`SlotMatcher`、`GapResolver`、`EditPlanner` 准备了提示词草稿，但它们彼此强依赖：槽位匹配要读样例结构和素材索引，缺口补齐要读匹配结果，剪辑编排要读匹配和补齐结果。

如果不先定义一个让 agent 之间共享上下文与通信的机制，这些 agent 只能靠在调用处手动传参拼接，链路会变得脆弱、难以观测、难以可视化。同时，用户的自然语言请求（"帮我把这个样例的结构套到我的素材上剪一版"）需要被解析成"该调用哪几个 agent、按什么顺序"，而不是只识别单一分析维度。

因此需要先落定三件事：一个会话级共享工作记忆、一个 agent 编排器、一个能产出多 agent 执行计划的意图规划能力。

## What Changes

- 新增会话级共享工作记忆（"黑板"），让各 agent 通过命名空间键读写带溯源信息的产物，并通过 append-only 事件日志记录 agent 间通信与执行轨迹。
- 新增 agent 编排器：每个 agent 声明读写的记忆键，编排器按依赖顺序执行意图规划给出的计划，处理缺输入、单 agent 失败隔离和部分结果返回。
- 将意图识别能力从"识别单一分析维度"升级为"产出多 agent 执行计划"，并在规划时结合当前会话记忆状态判断前置条件是否满足。
- 本次仅锁定编排骨架、共享记忆契约和意图规划能力；四个下游 agent（Asset/SlotMatcher/GapResolver/EditPlanner）只定义其在编排中的角色、读写的记忆键和 I/O 契约，不实现其完整内部逻辑。
- 多 agent 流程复用现有任务模型，采用异步任务 + 前端轮询的执行形态。

## Capabilities

### New Capabilities
- `agent-shared-memory`: 提供会话级共享工作记忆与 agent 间通信事件日志，作为多 agent 协作的统一上下文载体。
- `agent-orchestration`: 提供 agent 注册、依赖编排、异步执行与部分结果处理能力，把单个 agent 串成可观测的迁移创作链路。

### Modified Capabilities
- `analysis-intent-routing`: 从单维度分析意图识别升级为多 agent 执行计划规划。

## Impact

- 影响 `backend` 中 agent 层、服务层、任务模型与 API 路由：需要新增共享记忆与编排服务，并扩展任务状态机以表达多步执行进度。
- 为 `AssetAnalyzerAgent`、`SlotMatcherAgent`、`GapResolverAgent`、`EditPlannerAgent` 的后续实现提供统一上游契约与协作基座。
- 直接支撑 `prd.md` 任务7「迁移过程可视化」：事件日志与记忆快照即"从样例抽取了什么、如何映射、哪里缺口、如何补全"的数据来源。
- 影响 `frontend`：需要消费多 agent 任务进度与执行轨迹，但本次变更不约束最终前端交互细节。
