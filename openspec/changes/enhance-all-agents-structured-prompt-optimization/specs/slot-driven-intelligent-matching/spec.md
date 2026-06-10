## ADDED Requirements

### Requirement: 以结构 slot 为中心的 LLM 智能匹配
Slot Matcher 必须移除现有硬编码循环分配逻辑，改为调用 LLM 为每个 structural slot 选择最优素材片段。

#### Scenario: 智能匹配完成
- **WHEN** Slot Matcher 接收到完整的 Reference Analyzer 输出和 Asset Indexer 输出
- **THEN** LLM 被调用，以每个 structural slot 为核心进行素材匹配，输出的 slot_assignments 数组中每个项拥有 selected_candidate、match_score、score_breakdown、adaptation_plan 等字段

### Requirement: 匹配结果包含完整分数拆解
每个匹配项必须提供多维度分数拆解，指示语义匹配、视觉匹配、时长匹配、运动匹配、风格匹配的各自得分。

#### Scenario: 多维度分数拆解完整
- **WHEN** 一个素材被成功分配到某个 slot
- **THEN** score_breakdown 对象包含 semantic_fit、visual_fit、duration_fit、motion_fit、style_fit 五个维度的浮点得分 (0.0~1.0)

### Requirement: 未填充槽位进入 unfilled_slots
完全找不到合适素材的槽位必须明确进入 unfilled_slots 数组，附带缺失原因和建议补齐策略列表。

#### Scenario: 缺口槽位正确识别
- **WHEN** 某个 slot 没有任何可匹配的素材片段
- **THEN** 该 slot 进入 unfilled_slots 数组，附带 need 描述、missing_reason 和 suggested_gap_strategies 策略列表
