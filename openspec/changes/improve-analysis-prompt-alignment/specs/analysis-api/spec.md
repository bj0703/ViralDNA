## ADDED Requirements

### Requirement: 系统对样例分析任务使用真实视频输入
系统 SHALL 在样例分析任务中向目标模型 API 提交真实视频输入，而不是仅提交文件名、备注或启发式摘要等文本上下文。

#### Scenario: 创建真实视频分析任务
- **WHEN** 用户上传样例视频并发起分析
- **THEN** 系统使用该视频本体或该视频的有效媒体引用调用目标模型 API

#### Scenario: API 不支持当前视频输入方式
- **WHEN** 当前目标模型 API 不支持系统采用的视频输入协议
- **THEN** 系统返回明确能力错误，而不是静默改为文本推断分析

### Requirement: 系统返回可验证的分析来源与输入形态
系统 SHALL 在样例分析结果中返回统一的 provider trace，以说明本次任务是否真正基于视频输入完成。

#### Scenario: 真实视频分析成功
- **WHEN** 系统成功完成一次真实视频分析
- **THEN** 结果中包含 `actual_provider`、`input_modality=video` 或等价值，且 `used_fallback=false`

#### Scenario: 退回降级路径
- **WHEN** 系统未能完成真实视频分析并执行了显式降级
- **THEN** 结果中包含 `used_fallback=true`、可读的 `fallback_reason` 和非视频输入形态标识

### Requirement: 系统显式接收分析指令
系统 SHALL 为样例视频分析任务接收显式的用户分析指令，并 SHALL 将该指令与真实视频输入共同传入分析 provider。

#### Scenario: 创建带分析指令的真实视频分析任务
- **WHEN** 用户上传样例视频并提供“只看节奏结构”或等价分析诉求
- **THEN** 系统将该指令作为独立分析参数传入视频分析请求
