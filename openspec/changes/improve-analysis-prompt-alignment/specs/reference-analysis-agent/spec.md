## ADDED Requirements

### Requirement: ReferenceAnalyzerAgent 基于真实视频输入发起分析
`ReferenceAnalyzerAgent` SHALL 使用真实视频输入调用目标模型 API，而不是仅基于文本上下文推断视频内容。

#### Scenario: agent 发起真实视频分析
- **WHEN** agent 收到一个样例视频分析请求
- **THEN** 它向目标 API 提交视频输入和分析指令，并请求结构化 JSON 输出

### Requirement: ReferenceAnalyzerAgent 保留结构化输出约束
`ReferenceAnalyzerAgent` SHALL 在进行真实视频分析时保留现有结构化输出约束，以保证结果可映射到标准分析结果结构。

#### Scenario: 视频分析返回模型结果
- **WHEN** 目标模型 API 返回分析结果
- **THEN** agent 对结果执行 JSON 提取、校验和必要修复，再输出标准结构

### Requirement: ReferenceAnalyzerAgent 对视频分析失败返回显式错误
当目标模型 API 无法完成真实视频分析时，`ReferenceAnalyzerAgent` SHALL 返回显式能力错误或失败原因，而不是默认伪装成成功的视频理解结果。

#### Scenario: 底层接口只返回文本能力
- **WHEN** 当前 endpoint 不支持视频输入或返回不支持的视频能力错误
- **THEN** agent 返回清晰错误，并将该状态传递给上层结果或任务状态
