## Context

当前后端已经有样例分析 API 和展示模型，但主要依赖启发式规则，因此输出更多是“工程占位结果”而不是真实视频理解结果。你现在提供的 [prompt.md](/d:/ai%20coding/emo_transfer/prompt.md:1) 已经定义了一套清晰、约束严格、可直接落地的样例分析行为，这足以支撑一个正式的 `ReferenceAnalyzerAgent`。

这个 agent 的职责不是泛化聊天，而是针对“样例视频理解”这个任务执行单一高价值动作：对视频进行结构化逆向工程拆解，并为后续迁移创作提供上游输入。

同时，你后续目标是多 agent 系统，因此本次设计不仅要解决“怎么分析样例视频”，还要解决“这个 agent 在整体系统里处于什么位置”。

## Goals / Non-Goals

**Goals:**
- 定义 `ReferenceAnalyzerAgent` 的职责边界、输入输出和异常处理。
- 固定样例分析使用的系统 prompt 和 JSON 输出结构。
- 让 agent 输出可被后续多 agent 流程直接消费，而不是只用于单页展示。
- 明确水印过滤、无效片尾裁剪和爆款类型标签选择等规则属于 agent 的核心职责。

**Non-Goals:**
- 不在本次 change 中实现完整多 agent 编排系统。
- 不在本次 change 中实现素材视频分析、缺口识别或结构迁移生成。
- 不在本次 change 中定义最终前端交互细节。

## Decisions

### 1. 将样例视频分析升级为独立 agent
本次不再把样例分析视为一个普通 provider 调用，而是定义为 `ReferenceAnalyzerAgent`。

原因：
- 这个能力已经有明确输入、系统提示词、结构化输出和可复用价值。
- 它天然是多 agent 系统中的上游分析节点。
- 作为独立 agent 更方便后续编排、监控和调试。

### 2. prompt 作为正式能力契约的一部分
当前提供的样例分析 prompt 将被纳入正式实现，而不是只保留在实验文件中。

原因：
- prompt 已经包含关键业务规则，如忽略水印、裁剪片尾、限定类型标签和 JSON 输出结构。
- 这些规则本质上是产品能力的一部分，而不仅是模型调用细节。

### 3. agent 输出必须经过 JSON 校验与修复
模型输出不能直接信任，必须经过：
- JSON 提取
- schema 校验
- 字段修复或降级错误返回

原因：
- 后续多个 agent 会依赖这个结果。
- 如果上游输出不稳定，整个多 agent 链路会变得脆弱。

### 4. agent 输出与现有 view-model 分离
`ReferenceAnalyzerAgent` 的原始输出保持为标准 JSON 结果，再由映射层转换为当前前端展示模型。

原因：
- 可以同时服务于前端工作台和后续迁移 agent。
- 避免为了页面展示污染原始分析结构。

### 5. 在多 agent 架构中作为上游真值来源
后续多 agent 系统建议采用以下最小链路：
- `IntentRouterAgent`
- `ReferenceAnalyzerAgent`
- `AssetAnalyzerAgent`
- `GapDetectorAgent`
- `TransferPlannerAgent`

其中 `ReferenceAnalyzerAgent` 是样例理解的上游真值来源。

原因：
- 样例理解决定了后续迁移的结构模板。
- 如果这个上游节点不稳定，后面所有 agent 的输出都会偏离目标。

## Risks / Trade-offs

- [模型返回非 JSON 或 JSON 不完整] -> 增加 JSON 提取、字段修复和失败回退。
- [prompt 过长导致输出截断] -> 控制 max tokens，并在失败时分层返回简化错误。
- [当前 chat/completions 难以直接做高质量视频理解] -> 本次先完成 agent 契约和实现边界，必要时后续再升级底层视频理解调用方式。
- [原始 agent 输出与现有 sample-analysis schema 不一致] -> 引入显式映射层，把 agent 输出转换为统一后端结果。

## Migration Plan

第一阶段先保留当前 heuristic 样例分析作为 fallback，同时引入 `ReferenceAnalyzerAgent` 作为正式分析路径。  
第二阶段逐步让 `/sample-analysis/jobs` 优先走 agent 分析，并在失败时回退 heuristic。  
第三阶段再将 agent 结果直接作为后续结构迁移和素材缺口识别的输入。

## Open Questions

- 当前底层调用是否足以承载真实视频理解，还是需要后续单独升级 provider 形态？
- 第一版是否要求 `ReferenceAnalyzerAgent` 完整覆盖 prompt 中所有字段，还是允许部分字段先降级返回？
- `migration_suggestion` 是否需要直接进入前端 UI 首屏展示，还是仅作为下游迁移模块输入？
