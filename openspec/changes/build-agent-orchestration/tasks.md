## 1. 共享工作记忆

- [ ] 1.1 定义会话级共享记忆的数据模型与作用域（按 session/job 隔离）
- [ ] 1.2 固定命名空间键集合：`reference_analysis`、`asset_index`、`slot_matches`、`gaps`、`resolved_gaps`、`edit_timeline`
- [ ] 1.3 定义每个记忆条目的溯源元数据（`produced_by`、`produced_at`、`confidence`、`source_refs`）
- [ ] 1.4 定义键"未就绪"状态的表示方式，避免空对象伪装成已有结果
- [ ] 1.5 实现 append-only 事件日志的数据结构与事件类型（开始/写入/警告/缺口/跳过/失败）

## 2. agent 编排器

- [ ] 2.1 定义 agent 注册表与读写契约（`reads`/`writes`/`optional_reads`）
- [ ] 2.2 实现按读写键推导依赖并排序执行的编排逻辑
- [ ] 2.3 实现必需输入缺失时的 `blocked` 跳过逻辑与可选输入降级逻辑
- [ ] 2.4 实现单 agent 失败隔离，并将失败原因写入事件日志
- [ ] 2.5 让现有 `ReferenceAnalyzerAgent` 输出写入 `reference_analysis` 键，验证编排骨架

## 3. 异步任务与状态

- [ ] 3.1 扩展任务状态机：`queued`/`planning`/`running`/`partial`/`completed`/`failed`
- [ ] 3.2 定义每个 agent 步骤的子状态：`pending`/`running`/`completed`/`blocked`/`skipped`/`failed`
- [ ] 3.3 提供创建编排任务并立即返回 `job_id` 的接口
- [ ] 3.4 提供任务状态与各步骤进度的轮询接口
- [ ] 3.5 定义 `partial` 状态下已完成步骤产物的返回方式

## 4. 意图规划升级

- [ ] 4.1 将意图识别升级为输出多 agent 执行计划（`plan` 字段）
- [ ] 4.2 保留兼容字段 `intent` 与 `analysis_scope`
- [ ] 4.3 实现结合会话记忆状态判断前置条件、补全或调整计划的逻辑
- [ ] 4.4 实现受控 agent 集合约束与低置信度回退/澄清

## 5. 下游 agent 编排契约（仅契约，不实现内部逻辑）

- [ ] 5.1 定义 `AssetAnalyzerAgent` 角色：写 `asset_index`，引用 `ASSET_INDEXER_SYSTEM_PROMPT`
- [ ] 5.2 定义 `SlotMatcherAgent` 角色：读 `reference_analysis`+`asset_index`，写 `slot_matches`+`gaps`，引用 `SLOT_MATCHER_PROMPT`
- [ ] 5.3 定义 `GapResolverAgent` 角色：读 `gaps`，写 `resolved_gaps`，引用 `GAP_RESOLVER_PROMPT`
- [ ] 5.4 定义 `EditPlannerAgent` 角色：读 `slot_matches`+`resolved_gaps`，写 `edit_timeline`，引用 `EDIT_PLANNER_PROMPT`
- [ ] 5.5 固定各 agent 的输入输出 JSON 形状，使后续实现可直接按契约接入

## 6. 可视化数据与验证

- [ ] 6.1 定义从事件日志 + 记忆快照导出迁移过程轨迹的数据接口（支撑 PRD 任务7）
- [ ] 6.2 用单 agent 计划（仅 `ReferenceAnalyzer`）验证编排骨架与轮询链路
- [ ] 6.3 用一个"缺素材"场景验证意图规划的前置条件澄清逻辑
- [ ] 6.4 记录当前编排能力的限制与下游 agent 未实现的已知缺口
