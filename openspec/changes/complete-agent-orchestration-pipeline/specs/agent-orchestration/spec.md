## MODIFIED Requirements

### Requirement: 系统提供 agent 注册与读写契约
系统 SHALL 维护一个 agent 注册表，每个 agent SHALL 声明其读取（`reads`）、写入（`writes`）和可选读取（`optional_reads`）的共享记忆键，支持点号分隔的嵌套key路径。

#### Scenario: 注册一个 agent
- **WHEN** 一个 agent 被纳入编排系统
- **THEN** 系统记录其读写的记忆键，作为编排依赖排序的依据

#### Scenario: agent 缺少必需输入
- **WHEN** 某 agent 的必需 `reads` 键在共享记忆中尚未就绪
- **THEN** 系统直接抛出 AgentDependencyUnsatisfiedError 异常终止流水线，不再标记为blocked静默跳过

### Requirement: 系统按数据依赖编排 agent 执行
系统 SHALL 根据 agent 声明的读写键推导依赖关系，并按依赖顺序执行意图规划给出的 agent 计划，而不是依赖写死的调用顺序。支持嵌套key路径判断依赖是否满足。

#### Scenario: 按依赖顺序执行计划
- **WHEN** 编排器收到一个包含多个 agent 的执行计划
- **THEN** 系统在某 agent 所依赖的上游产物就绪后才执行该 agent

#### Scenario: 新增 agent 不破坏既有编排
- **WHEN** 一个新 agent 按读写键契约加入注册表
- **THEN** 编排器无需修改即可将其纳入依赖排序

### Requirement: 系统以异步任务执行多 agent 编排
系统 SHALL 以异步任务形式执行多 agent 编排，立即返回任务标识，并 SHALL 提供任务级状态与各 agent 步骤的子状态供前端轮询。使用 asyncio.to_thread 包装同步阻塞代码避免阻塞事件循环。

#### Scenario: 创建编排任务
- **WHEN** 前端提交一个多 agent 编排请求（multipart/form-data 包含视频文件）
- **THEN** 系统创建任务、返回 `job_id`，并将任务置于 `queued` 或 `planning` 状态

#### Scenario: 轮询执行进度
- **WHEN** 前端轮询一个执行中的编排任务
- **THEN** 系统返回任务级状态和每个 agent 步骤的 `pending`/`running`/`completed`/`blocked`/`skipped`/`failed` 子状态

### Requirement: 系统使用统一的编排任务状态集合
系统 SHALL 为多 agent 编排任务使用统一状态集合，包括 `queued`、`planning`、`running`、`partial`、`completed` 和 `failed`。

#### Scenario: 全部步骤成功
- **WHEN** 计划中的所有 agent 步骤成功完成
- **THEN** 系统将任务标记为 `completed`

#### Scenario: 部分步骤成功
- **WHEN** 部分 agent 步骤成功、部分被跳过或失败，但仍产出可用结果
- **THEN** 系统将任务标记为 `partial`，并保留已完成步骤的产物

### Requirement: 系统隔离单个 agent 失败
系统 SHALL 隔离单个 agent 的失败，使其不导致整条编排链路崩溃，并 SHALL 在事件日志中记录失败原因。

#### Scenario: 某 agent 执行失败
- **WHEN** 编排过程中某个 agent 抛出错误
- **THEN** 系统将该步骤标记为 `failed`、记录原因，并终止后续步骤，不再静默继续

### Requirement: 5个真实Agent全部接入编排系统
系统 SHALL 完全实现之前预留契约中的所有5个Agent，全部有完整执行逻辑，不再是占位框架。

#### Scenario: 5个Agent全量注册
- **WHEN** 系统启动加载AgentRegistry
- **THEN** 可查询到全部5个Agent：ReferenceAnalyzerAgent、AssetIndexerAgent、SlotMatcherAgent、GapResolverAgent、EditPlannerAgent，每个都有真实analyze实现
