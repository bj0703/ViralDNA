## ADDED Requirements

### Requirement: 系统提供 agent 注册与读写契约
系统 SHALL 维护一个 agent 注册表，每个 agent SHALL 声明其读取（`reads`）、写入（`writes`）和可选读取（`optional_reads`）的共享记忆键。

#### Scenario: 注册一个 agent
- **WHEN** 一个 agent 被纳入编排系统
- **THEN** 系统记录其读写的记忆键，作为编排依赖排序的依据

#### Scenario: agent 缺少必需输入
- **WHEN** 某 agent 的必需 `reads` 键在共享记忆中尚未就绪
- **THEN** 系统将该 agent 步骤标记为 `blocked` 并跳过，而不是用空数据强行执行

### Requirement: 系统按数据依赖编排 agent 执行
系统 SHALL 根据 agent 声明的读写键推导依赖关系，并按依赖顺序执行意图规划给出的 agent 计划，而不是依赖写死的调用顺序。

#### Scenario: 按依赖顺序执行计划
- **WHEN** 编排器收到一个包含多个 agent 的执行计划
- **THEN** 系统在某 agent 所依赖的上游产物就绪后才执行该 agent

#### Scenario: 新增 agent 不破坏既有编排
- **WHEN** 一个新 agent 按读写键契约加入注册表
- **THEN** 编排器无需修改即可将其纳入依赖排序

### Requirement: 系统以异步任务执行多 agent 编排
系统 SHALL 以异步任务形式执行多 agent 编排，立即返回任务标识，并 SHALL 提供任务级状态与各 agent 步骤的子状态供前端轮询。

#### Scenario: 创建编排任务
- **WHEN** 前端提交一个多 agent 编排请求
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
- **THEN** 系统将该步骤标记为 `failed`、记录原因，并按依赖关系决定后续步骤是 `blocked` 还是继续

### Requirement: 系统为下游 agent 预留编排契约
系统 SHALL 在编排层为 `AssetAnalyzerAgent`、`SlotMatcherAgent`、`GapResolverAgent` 和 `EditPlannerAgent` 定义其角色、读写的共享记忆键和输入输出契约，即使其内部实现逻辑在本次尚未完成。

#### Scenario: 下游 agent 契约可被引用
- **WHEN** 后续变更实现某个下游 agent
- **THEN** 该 agent 可直接按已定义的读写键和 I/O 契约接入编排器，无需改动编排骨架

#### Scenario: 下游 agent 的协作位置明确
- **WHEN** 查看编排契约
- **THEN** 可看出 `AssetAnalyzer` 写 `asset_index`、`SlotMatcher` 读 `reference_analysis` 与 `asset_index` 并写 `slot_matches` 与 `gaps`、`GapResolver` 读 `gaps` 写 `resolved_gaps`、`EditPlanner` 读 `slot_matches` 与 `resolved_gaps` 写 `edit_timeline`
