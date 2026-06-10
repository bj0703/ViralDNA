## ADDED Requirements

### Requirement: 新增 inputs 嵌套子域
SessionSharedMemory SHALL 新增inputs嵌套子域，包含 user_prompt 字符串字段和 uploaded_videos 数组字段。

#### Scenario: 设置用户原始自然语言输入
- **WHEN** 调用 shared_memory.set_input_user_prompt("帮我分析这个视频")
- **THEN** 共享记忆中 inputs.user_prompt 字段保存该字符串

### Requirement: UploadedVideo 数据结构包含 is_reference 标记
上传视频数据结构 SHALL 包含 is_reference 布尔字段，用来明确区分该视频是参考样例还是普通素材。

#### Scenario: 标记参考样例视频
- **WHEN** 追加一个上传视频，设置is_reference=True
- **THEN** 该视频被流水线识别为样例，自动分配给ReferenceAnalyzerAgent处理

#### Scenario: 标记普通素材视频
- **WHEN** 追加一个上传视频，设置is_reference=False
- **THEN** 该视频被流水线识别为素材，自动分配给AssetIndexerAgent处理

### Requirement: 点号分隔嵌套key路径支持
系统 SHALL 实现 get_nested(key_path) 工具函数，支持点号分隔的嵌套key路径直接穿透取值。

#### Scenario: 读取 inputs.uploaded_videos
- **WHEN** 调用 shared_memory.get_nested("inputs.uploaded_videos")
- **THEN** 系统自动穿透 inputs 子域，直接返回 uploaded_videos 数组内容

#### Scenario: 直接读取一级key保持兼容
- **WHEN** 调用 shared_memory.get("reference_analysis")
- **THEN** 仍然正常返回一级内容，完全向后兼容
