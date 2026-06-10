## Context

当前项目已实现基础的多Agent流水线，5个Agent（Reference Analyzer / Asset Indexer / Slot Matcher / Gap Resolver / Edit Planner）均已有代码骨架。但现状存在关键问题：
- Reference Analyzer 输出偏报告化，缺少结构化的 structural_slots
- Asset Indexer 粒度太粗，没有细粒度素材片段拆解
- Slot Matcher / Gap Resolver / Edit Planner 硬编码逻辑，没有真正调用LLM
- 全链路中间数据协议不统一，字段冲突，后续链路难以协同
- 所有变更必须100%向后兼容，不修改外部API接口，不破坏现有shared_memory顶层key结构

## Goals / Non-Goals

**Goals:**
- 升级所有5个Agent的prompt，输出符合新规范的结构化数据
- Slot Matcher / Gap Resolver 改为调用LLM，移除硬编码分配逻辑
- 全链路统一slot_id格式、7级缺口策略、confidence/risk_notes协议
- 升级Edit Planner生成多轨完整EditableTimeline，增加validation和human_review_points
- 所有修改完全向后兼容，不改变外部API签名，不破坏现有流水线
- 保留原有parse-and-repair容错逻辑，防止LLM输出格式异常导致崩溃

**Non-Goals:**
- 本变更不新增Verifier独立Agent，校验逻辑整合到Edit Planner内
- 不修改Ochestrator核心调度逻辑，不增加新Agent注册入口
- 不引入任何新的外部依赖包
- 不重构ArkChatProvider等底层Provider逻辑

## Decisions

**Decision 1: 完全向后兼容的增量字段追加策略**
- 方案选择：不修改原有顶层key结构（reference_analysis / asset_index / slot_matches / resolved_gaps / edit_timeline），只在原有JSON结构基础上追加新字段
- 理由：保证现有测试脚本、前端UI、API调用完全不受影响，升级零风险
- 替代方案：完全重构shared_memory结构 → 破坏性变更，代价太高被否决

**Decision 2: 旧降级逻辑作为 fallback 兜底保留**
- 方案选择：在每个Agent中，新LLM调用逻辑为主路径，如果LLM调用失败/返回无效JSON，原有旧的硬编码降级逻辑继续作为保底方案
- 理由：防止LLM服务异常时流水线完全不可用，保证系统鲁棒性
- 替代方案：移除所有旧逻辑 → 服务异常时系统彻底瘫痪，风险过大被否决

**Decision 3: 逐步扩展输出而非整体替换**
- 方案选择：新输出结构作为新字段追加，原有旧字段（Reference Analyzer原有的script_structure/rhythm_structure/packaging_and_sound）完全保留不动
- 理由：历史兼容 + 双轨并行，旧消费者不感知变更，新消费者可以使用新字段
- 替代方案：删除旧字段 → 破坏依赖旧字段的所有逻辑，被否决

**Decision 4: 7级缺口策略统一为全链路标准**
- 方案选择：全链路统一策略顺序：reuse → static_graphic → text_card → brand_asset → structure_reorder → ai_generate → ask_user
- 理由：完全对齐prompt优化建议中的方案，字段无冲突
- 替代方案：保留原有策略定义 → 多Agent策略不一致，导致后续链路无法协同，被否决

## Risks / Trade-offs

[Risk] LLM输出JSON格式不稳定，新字段解析失败 → Mitigation: 复用现有parse-and-repair轻量修复逻辑，同时增加字段级容错填充，如果新字段解析失败不影响原有字段的正常输出
[Risk] 升级后流水线处理token数量显著增加 → Mitigation: 逐步调整各Agent的max_tokens参数，Reference Analyzer设为3000，Asset Indexer单素材设为1200，其余Agent设为2000，平衡输出完整度和token消耗
[Risk] 新增字段过多导致旧逻辑解析出问题 → Mitigation: 所有新增字段完全使用新key命名，与旧字段无命名冲突，旧逻辑读取未知key不会抛出异常
[Trade-off] 保留旧降级逻辑会导致代码中存在一定"双重逻辑"冗余 → 接受这个trade-off，换取极高的系统鲁棒性和向后兼容性
