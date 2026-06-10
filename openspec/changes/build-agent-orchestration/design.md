## Context

`ReferenceAnalyzerAgent` 已经能产出结构化样例分析，但要完成 `prd.md` 的迁移创作目标，还需要至少四个下游 agent：`AssetAnalyzerAgent`（分析用户素材）、`SlotMatcherAgent`（把素材分配到样例结构槽位并标缺口）、`GapResolverAgent`（按优先级补齐缺口）、`EditPlannerAgent`（产出可编辑时间线）。这些 agent 的提示词草稿已存在于 `prompt.md`。

它们之间是强依赖关系：

```
ReferenceAnalyzer ─┐
                   ├─> SlotMatcher ─> GapResolver ─> EditPlanner
AssetAnalyzer ─────┘
```

问题在于：如果靠调用处手动传参把上游输出喂给下游，链路会随着 agent 增多而急剧变脆，且无法回答"这次迁移到底经过了哪些步骤、哪里出现了缺口、如何补的"——而这恰恰是 `prd.md` 任务7 要求展示的内容。

因此本次设计要解决三个问题：
1. agent 之间如何共享上下文与通信（共享工作记忆）。
2. agent 如何被有序、可观测、可容错地串起来（编排器）。
3. 用户的自然语言如何决定调用哪几个 agent（意图规划）。

本次只锁定这三件事的契约骨架，四个下游 agent 的内部实现逻辑留给后续变更。

## Goals / Non-Goals

**Goals:**
- 定义会话级共享工作记忆的数据模型、命名空间键、溯源元数据和事件日志。
- 定义 agent 编排器：agent 注册契约（读写哪些记忆键）、依赖排序、异步执行、缺输入处理、单 agent 失败隔离与部分结果返回。
- 把意图识别升级为多 agent 执行计划规划，并结合会话记忆状态判断前置条件。
- 让共享记忆与事件日志成为「迁移过程可视化」的数据来源。

**Non-Goals:**
- 不实现 `AssetAnalyzerAgent`、`SlotMatcherAgent`、`GapResolverAgent`、`EditPlannerAgent` 的完整内部逻辑（仅定编排契约）。
- 不实现六级缺口补全策略的具体算法。
- 不实现 EditableTimeline 到真实成片的渲染。
- 不在本次定义最终前端交互细节，只定义其可消费的数据。
- 不引入外部消息队列或分布式任务系统；复用现有进程内任务模型。

## Decisions

### 1. 共享工作记忆采用会话级"黑板"模型

引入一个会话级（session）的共享记忆，作为所有 agent 的统一上下文载体。结构上是按命名空间键组织的条目集合：

- `reference_analysis`：样例结构分析（来自 `ReferenceAnalyzerAgent`）
- `asset_index`：用户素材分析索引（来自 `AssetAnalyzerAgent`）
- `slot_matches`：素材到槽位的匹配结果（来自 `SlotMatcherAgent`）
- `gaps`：未被满足的结构槽位缺口（来自 `SlotMatcherAgent`）
- `resolved_gaps`：缺口补齐方案（来自 `GapResolverAgent`）
- `edit_timeline`：可编辑时间线草案（来自 `EditPlannerAgent`）

每个条目都携带溯源元数据：`produced_by`（agent 名）、`produced_at`、`confidence`、`source_refs`（依赖了哪些上游键 / job）。

原因：
- 下游 agent 只按键读取上游产物，agent 之间不直接互相调用，降低耦合。
- 命名空间键是稳定契约，新增 agent 不影响已有 agent 的读写约定。
- 溯源元数据让任意一个产物都能回溯它的来源链，支撑可解释性。

### 2. agent 间通信走 append-only 事件日志

除了记忆条目本身，共享记忆还维护一条只追加的事件日志，记录每个 agent 的开始、写入、警告、缺口、失败、跳过等事件。

原因：
- 这是 agent 间"通信"的可观测轨迹，而不是隐式的函数调用栈。
- 事件日志 + 记忆快照直接构成 `prd.md` 任务7「从样例抽取了什么 → 如何映射 → 哪里缺口 → 如何补全」的展示数据来源。
- append-only 让执行轨迹可被前端按时间顺序回放。

### 3. 编排器按 agent 声明的读写键做依赖排序

每个 agent 在注册表中声明：

- `reads`：它需要读取的记忆键
- `writes`：它会写入的记忆键
- `optional_reads`：缺失也能降级运行的键

编排器接收意图规划给出的 agent 计划，按 reads/writes 形成的依赖关系排序后执行。某个 agent 的必需 `reads` 在记忆中缺失时，该步标记为 `blocked` 并跳过，而不是让整条链崩溃。

原因：
- 依赖关系由数据契约（读写键）推导，而不是写死的调用顺序，新增 agent 时编排器无需改动。
- `blocked` 与 `optional_reads` 让链路具备部分执行能力，符合 PRD"素材不足时仍要产出合理结果"的精神。

### 4. 多 agent 流程采用异步任务 + 轮询

复用现有任务模型，但扩展状态机以表达多步执行：

- 任务级状态：`queued` -> `planning` -> `running` -> (`partial` | `completed` | `failed`)
- 每个 agent step 子状态：`pending` / `running` / `completed` / `blocked` / `skipped` / `failed`

创建任务后立即返回 `job_id`，前端轮询任务状态与各 step 进度。

原因：
- 多 agent + 真实视频/素材分析整体耗时较长，同步阻塞请求体验差、易超时。
- 轮询模型与现有任务接口一致，前端改造成本低。
- `partial` 状态让"部分 agent 成功"也能返回可用结果，而非全有或全无。

### 5. 意图识别升级为多 agent 执行计划规划

把现有"识别单一分析维度"的能力升级为「意图规划」：输入用户自然语言 + 当前会话记忆状态，输出一个执行计划——该调用哪几个 agent、按什么顺序、各自的范围。

- 规划时读取会话记忆判断前置条件。例：用户说"帮我套这个样例剪一版"，但记忆里还没有 `reference_analysis` 或 `asset_index`，则计划中自动前置补上对应 agent，或返回"需要先上传素材"的澄清。
- 仍限制在受控 agent 集合内，不规划超出集合的动作。
- 向后兼容：保留现有 `intent` / `analysis_scope` 字段，新增 `plan`（agent 步骤序列）字段。

原因：
- 用户表达的是创作意图（"剪一版""换个 hook"），而不是"调用哪个 agent"；规划层负责把意图翻译成 agent 计划。
- 结合记忆状态规划，避免在缺前置数据时盲目执行下游 agent。

### 6. 下游四 agent 本次只定编排契约

`AssetAnalyzer` / `SlotMatcher` / `GapResolver` / `EditPlanner` 在本次只定义：它在编排中的角色、`reads`/`writes` 的记忆键、输入输出 JSON 形状（引用 `prompt.md` 中的提示词草稿），不定义其内部分析/补全算法。

原因：
- 先把协作基座和契约钉死，下游 agent 可以各自独立实现、独立验证。
- 避免本次变更范围过大、评审上下文过载。

## Risks / Trade-offs

- [共享记忆随会话增长膨胀] -> 按 job/session 作用域隔离，条目以最新覆盖为主，事件日志可分页。
- [agent 链路某步失败拖垮全程] -> 失败隔离 + `partial` 返回 + `blocked`/`skipped` step 状态。
- [意图规划误判导致多调或少调 agent] -> 受控 agent 集合 + 低置信度回退澄清 + 计划对用户可见可调整（后续变更）。
- [异步轮询增加前端复杂度] -> 复用现有任务接口形态，仅扩展状态字段，保持轮询契约简单。
- [下游 agent 契约与未来实现不符] -> 本次只锁定读写键与 I/O 形状这类稳定契约，内部逻辑留实现期细化。
- [内存持久化下重启丢失记忆] -> 记忆与任务复用同一存储层；持久化是已知的独立问题，不在本次范围，但契约设计不应假设永驻内存。

## Migration Plan

第一步：实现共享工作记忆的数据模型、命名空间键与事件日志，并让现有 `ReferenceAnalyzerAgent` 的输出写入 `reference_analysis` 键。
第二步：实现 agent 注册表与编排器，先用「单 agent 计划」跑通 `ReferenceAnalyzer`，验证编排骨架。
第三步：把意图识别升级为意图规划，输出 agent 计划并结合记忆状态判断前置条件。
第四步：按编排契约逐个接入 `AssetAnalyzer` / `SlotMatcher` / `GapResolver` / `EditPlanner`（各自后续变更），编排器无需改动。
第五步：把事件日志与记忆快照暴露给前端，支撑迁移过程可视化。

## Open Questions

- 共享记忆是否需要版本化（同一键的多次产出是否保留历史，还是只留最新）？
- 意图规划的执行计划是否需要在执行前让用户确认/编辑，还是自动执行后允许回退？
- 部分成功（`partial`）时，前端默认展示已完成 step 的结果，还是要求用户显式确认继续？
- 事件日志的粒度到 agent 级即可，还是需要细到 agent 内部关键步骤？
