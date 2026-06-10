## ADDED Requirements

### Requirement: Gap Resolver 7级策略按优先级执行
Gap Resolver 必须严格按照统一7级策略优先级执行：reuse -> static_graphic -> text_card -> brand_asset -> structure_reorder -> ai_generate -> ask_user。

#### Scenario: 缺口策略按优先级选择
- **WHEN** 一个未填充的 slot 进入 Gap Resolver
- **THEN** 系统按7级优先级顺序逐一尝试可行性，从最低编号可行策略中选择最终方案

### Requirement: 输出可执行补齐方案，params 不再为空
Gap Resolver 的输出不能只有抽象策略名，必须附带具体可执行的参数，包括素材引用、编辑参数、覆盖文字、视频变换指令等。

#### Scenario: 补齐方案完全可执行
- **WHEN** 缺口被 Gap Resolver 成功解决
- **THEN** resolution 对象包含完整的 new_slot_type、asset_ref、edit_params，edit_params 中明确指定 crop、speed、motion、overlay_text、caption_style 等具体参数

### Requirement: 标注补齐方案对原结构的影响
每个缺口补齐方案必须附带 impact_on_template，指示该操作对原模板时长、节奏、结构保真度的影响。

#### Scenario: 结构影响评估完整
- **WHEN** 补齐方案生成完成
- **THEN** impact_on_template 对象包含 duration_change 数值、rhythm_change 描述、structure_fidelity 保真度等级

### Requirement: 标注是否需要人工复核
补齐方案必须明确标记 requires_human_review 布尔字段。

#### Scenario: 高风险补齐方案标记人工复核
- **WHEN** 缺口补齐方案的置信度低于 0.7 或使用了 structure_reorder / ai_generate / ask_user 策略
- **THEN** requires_human_review 被设置为 true，该缺口将进入最终的 human_review_points 人工复核列表
