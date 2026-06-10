## Why

当前项目的5个Agent输出偏报告化，缺少统一的结构槽位协议，素材分析粒度不够细，Slot Matcher/Gap Resolver/Edit Planner 硬编码逻辑没有调用LLM，导致整体迁移效果达不到"爆款视频创作结构抽象与迁移"的预期目标。本变更将所有Agent升级为结构驱动的智能链路，彻底解决中间数据不一致、匹配逻辑缺失、缺口补齐不可执行等核心问题。

## What Changes

- **Reference Analyzer 升级**：从"视频报告生成器"升级为"爆款结构模板抽象器"，新增 `structural_slots` 标准化槽位输出，输出后续所有Agent都可直接复用的可迁移结构模板
- **Asset Indexer 升级**：从"素材整体分析师"升级为"素材片段索引器"，将素材拆分为细粒度的可剪辑segments，新增镜头运动、竖屏适配、视觉质量等20+维度字段
- **Slot Matcher 完全重写**：移除现有硬编码循环分配逻辑，改为调用LLM以structural slot为中心的智能匹配，每个匹配项带匹配分数、分数拆解、适配方案和置信度
- **Gap Resolver 完全重写**：从简单策略选择器升级为可执行缺口补齐器，LLM按7级优先级选择策略并生成完整可执行的补齐方案，不再返回空的params
- **Edit Planner 升级**：从简单时间线拼接升级为多轨可执行剪辑方案生成器，新增视频轨/字幕轨/包装轨/音频轨完整结构，增加validation校验层和human_review_points人工复核入口
- **新增统一中间数据协议**：全链路统一slot_id格式、缺口补齐7大策略、confidence/risk_notes字段，彻底解决字段冲突
- **向后兼容保证**：所有现有API接口、共享内存结构完全兼容，不引入破坏性变更，保证流水线可无缝切换到新版本

## Capabilities

### New Capabilities
- `structured-template-extraction`: Reference Analyzer输出标准化可迁移爆款结构模板，包含structural_slots、rhythm_curve、audio_beat_map等完整字段
- `fine-grained-asset-indexing`: Asset Indexer细粒度素材片段索引，将每个素材拆解为带完整维度描述的多个可剪辑segments
- `slot-driven-intelligent-matching`: Slot Matcher以结构槽位为中心的LLM智能匹配，输出匹配分数和适配方案
- `executable-gap-resolution`: Gap Resolver生成可执行缺口补齐方案，明确策略优先级、素材引用、编辑参数和人工确认标记
- `multi-track-editable-timeline`: Edit Planner生成包含视频/字幕/包装/音频多轨道的完整EditableTimeline，带自动校验和人工复核点

### Modified Capabilities
没有修改现有外部需求规范，所有变更在现有流水线框架内向后兼容。

## Impact

- 影响文件：`backend/app/prompts/` 下5个Agent的prompt文件
- 影响文件：`backend/app/agents/` 下5个Agent的实现逻辑
- 不改变外部API接口，不改变shared_memory顶层key结构，完全向后兼容
- 无新依赖引入，仅在现有LLM Provider基础上升级逻辑
