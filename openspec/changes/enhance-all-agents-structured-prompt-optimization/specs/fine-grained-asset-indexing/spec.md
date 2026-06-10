## ADDED Requirements

### Requirement: Asset Indexer 拆解细粒度可剪辑片段
Asset Indexer 必须将每个输入素材拆解为多个 candidate segments，每个 segment 拥有完整的元数据描述。

#### Scenario: 素材片段化分析完成
- **WHEN** 用户上传的素材视频进入 Asset Indexer
- **THEN** 输出的 assets 数组中每个素材拥有 segments 数组，每个 segment 包含 segment_id、start/end 时间、content_type、shot_size、camera_motion、motion_intensity、visual_quality、lighting_quality、subject_clarity、orientation_fit 等20+维度字段

### Requirement: 每个 segment 标注最佳适用场景
每个拆解出的素材片段必须明确标注 best_for_roles 和 best_for_slot_types，直接指示该片段适合承担的结构功能。

#### Scenario: 片段使用场景标注完整
- **WHEN** 素材片段被分析完成
- **THEN** best_for_roles 数组包含可适配的结构角色 (hook/develop/cta)，best_for_slot_types 数组包含可适配的槽位类型 (产品特写/结果展示等)

### Requirement: 标注片段可复用加工方式
每个 segment 必须列出 can_reuse_by 数组，指示该片段支持的后期处理操作。

#### Scenario: 可复用方式标注正确
- **WHEN** 素材片段分析完成
- **THEN** can_reuse_by 数组包含 crop、speed_up、zoom_in、freeze_frame 等允许的后期处理方式，指导后续链路进行素材二次加工
