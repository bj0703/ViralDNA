## ADDED Requirements

### Requirement: 系统提供样例视频分析 agent
系统 SHALL 提供 `ReferenceAnalyzerAgent`，用于对样例视频执行结构化理解，并返回可复用的标准结果。

#### Scenario: 接收样例视频并发起分析
- **WHEN** 用户或上游流程提交一个样例视频进行分析
- **THEN** 系统调用 `ReferenceAnalyzerAgent` 执行样例理解流程

#### Scenario: agent 结果可供后续模块复用
- **WHEN** `ReferenceAnalyzerAgent` 完成分析
- **THEN** 输出结果可被前端展示和后续迁移模块直接消费

### Requirement: 系统使用固定样例分析 prompt
系统 SHALL 使用正式定义的样例分析系统 prompt，并 SHALL 执行其中关于水印过滤、片尾裁剪、结构拆解和 JSON 输出的约束。

#### Scenario: 画面中包含水印或平台角标
- **WHEN** 样例视频画面中存在动态或静态水印、创作者 logo 或平台角标
- **THEN** agent 在分析包装与声音时忽略这些内容，不将其误判为包装贴纸

#### Scenario: 视频结尾存在无效片尾
- **WHEN** 视频结尾出现黑屏、关注标志、定格播完动画或平台自带结束 logo
- **THEN** agent 将其识别为无效片尾，并从核心有效内容分析中扣除

### Requirement: 系统输出固定 JSON 结构
系统 SHALL 输出固定 JSON 结构，并至少包含 `video_basic_info`、`script_structure`、`rhythm_structure`、`packaging_and_sound` 和 `migration_suggestion`。

#### Scenario: 样例分析成功
- **WHEN** agent 成功完成样例分析
- **THEN** 返回结果中包含所有约定一级字段

#### Scenario: 爆款类型标签选择
- **WHEN** agent 识别视频类型
- **THEN** `type_label` 只能从约定列表中选择且只能返回一个标签

### Requirement: 系统输出脚本结构与节奏结构
系统 SHALL 输出可解释的脚本结构和节奏结构结果，用于后续结构迁移。

#### Scenario: 输出脚本结构
- **WHEN** agent 解析样例视频
- **THEN** 返回 hook、develop、cta 等段落级结构及其时间范围和摘要

#### Scenario: 输出节奏结构
- **WHEN** agent 解析样例视频
- **THEN** 返回镜头数量、平均镜头时长、节奏变化和高潮位置等信息

### Requirement: 系统输出包装与迁移建议
系统 SHALL 输出包装与声音分析结果以及迁移建议，用于支撑后续创作迁移。

#### Scenario: 输出包装与声音分析
- **WHEN** agent 完成样例拆解
- **THEN** 返回字幕密度、视觉元素、转场特征、音频规律和封面风格

#### Scenario: 输出迁移建议
- **WHEN** agent 完成样例拆解
- **THEN** 返回至少两条明确的迁移建议，用于指导后续复用

### Requirement: 系统对 agent 输出进行校验与兜底
系统 SHALL 对模型返回的 agent 输出进行 JSON 提取、schema 校验与异常兜底，而不能直接信任模型原始文本。

#### Scenario: 模型返回合法 JSON
- **WHEN** 模型返回符合预期的 JSON 结果
- **THEN** 系统通过校验并进入标准结果映射流程

#### Scenario: 模型返回非法或不完整 JSON
- **WHEN** 模型返回非 JSON、字段缺失或结构异常
- **THEN** 系统执行修复或返回标准化错误，而不是直接透传原始输出
