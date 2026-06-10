## ADDED Requirements

### Requirement: 系统提供会话级共享工作记忆
系统 SHALL 为每个分析/创作会话提供一个共享工作记忆，用于让多个 agent 通过统一上下文协作，而不是在调用处手动传参拼接。

#### Scenario: agent 写入产物到共享记忆
- **WHEN** 某个 agent 完成其产物
- **THEN** 系统将该产物以约定的命名空间键写入当前会话的共享记忆

#### Scenario: 下游 agent 读取上游产物
- **WHEN** 某个 agent 需要上游产物作为输入
- **THEN** 它通过命名空间键从共享记忆读取，而不直接调用上游 agent

### Requirement: 系统定义稳定的共享记忆命名空间键
系统 SHALL 使用一组稳定的命名空间键组织共享记忆，至少包括 `reference_analysis`、`asset_index`、`slot_matches`、`gaps`、`resolved_gaps` 和 `edit_timeline`。

#### Scenario: 按键存取产物
- **WHEN** agent 读写某类产物
- **THEN** 系统使用对应的稳定命名空间键，使新增 agent 不影响已有键的读写约定

#### Scenario: 键尚无产物
- **WHEN** 某个键对应的产物尚未被任何 agent 写入
- **THEN** 系统对该键返回明确的"未就绪"状态，而不是返回空对象伪装成已有结果

### Requirement: 共享记忆条目携带溯源元数据
系统 SHALL 为每个共享记忆条目记录溯源元数据，至少包括产出该条目的 agent、产出时间、置信度和所依赖的上游来源引用。

#### Scenario: 回溯产物来源
- **WHEN** 用户或下游模块需要判断某个产物的来源
- **THEN** 系统能给出该产物由哪个 agent 产出、依赖了哪些上游键或任务

### Requirement: 系统维护 agent 间通信事件日志
系统 SHALL 为每个会话维护一条只追加（append-only）的事件日志，记录各 agent 的开始、写入、警告、缺口、跳过和失败等事件，作为 agent 间通信与执行轨迹的可观测来源。

#### Scenario: 记录 agent 执行事件
- **WHEN** 某个 agent 开始执行、写入产物或发生失败
- **THEN** 系统向事件日志追加一条带时间顺序的事件，而不覆盖历史事件

#### Scenario: 支撑迁移过程可视化
- **WHEN** 前端需要展示"从样例抽取了什么、如何映射、哪里缺口、如何补全"
- **THEN** 系统能基于事件日志与记忆快照按时间顺序提供这条迁移轨迹的数据
