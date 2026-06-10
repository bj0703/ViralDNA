## ADDED Requirements

### Requirement: Reference Analyzer 输出结构化可迁移模板
Reference Analyzer 必须从样例视频中抽象出可迁移的创作结构模板，输出包含 schema_version、template_id、structural_slots 等完整字段。

#### Scenario: 成功提取完整结构模板
- **WHEN** 用户上传标记为 reference 的样例视频并启动分析
- **THEN** Reference Analyzer 输出包含 structural_slots 数组的标准结构模板，每个 slot 拥有 slot_id (hook_01/hook_02 格式)、creative_function、required_visual_type、caption_requirement、audio_sync、importance 等20+字段

### Requirement: 全链路统一 slot_id 命名规范
系统所有 Agent 必须使用统一的 slot_id 命名格式，如 hook_01, develop_01, cta_01，禁止混用不同格式。

#### Scenario: 所有 slot_id 格式统一
- **WHEN** 任意 Agent 输出包含 slot_id 的数据
- **THEN** slot_id 必须严格采用 `角色_两位序号` 格式，例如 hook_01, develop_02，不存在 hook_1, slot_001 等其他格式

### Requirement: 输出统一 confidence 和 risk_notes
Reference Analyzer 的最终输出必须包含顶层 confidence (0.0~1.0) 和 risk_notes 数组字段。

#### Scenario: 带置信度的分析结果输出
- **WHEN** Reference Analyzer 完成视频分析
- **THEN** 输出顶层包含 confidence 浮点数值和 risk_notes 字符串数组，用于后续链路识别低置信度结果
