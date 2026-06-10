## ADDED Requirements

### Requirement: 生成多轨完整 EditableTimeline
Edit Planner 必须输出包含视频轨、字幕轨、包装轨、音频轨的完整多轨时间线结构。

#### Scenario: 多轨时间线生成成功
- **WHEN** Edit Planner 完成编排
- **THEN** 输出包含 timeline (视频轨)、caption_track (字幕轨)、packaging_track (包装元素轨)、audio_track (BGM+SFX轨)、cover_design 封面设计的完整结构

### Requirement: 时间线自动校验 validation
Edit Planner 在输出前必须执行完整的自动校验，输出 validation 对象。

#### Scenario: 自动校验执行完成
- **WHEN** 所有时间线元素生成完毕
- **THEN** validation 对象检查 all_slots_filled、no_missing_assets、no_timeline_overlap、source_ranges_valid、duration_close_to_reference，计算 structure_fidelity_score，并列出 warnings 数组

### Requirement: 输出 human_review_points 人工复核入口
最终输出必须包含 human_review_points 数组，列出所有需要用户确认的补齐项。

#### Scenario: 人工复核点完整输出
- **WHEN** 完整时间线生成且自动校验完成
- **THEN** human_review_points 数组列出所有 requires_human_review 标记为 true 的项，每项包含 slot_id、issue 描述和可选操作选项
