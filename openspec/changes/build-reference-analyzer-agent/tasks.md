## 1. Agent 定义

- [x] 1.1 定义 `ReferenceAnalyzerAgent` 的输入输出接口和职责边界
- [x] 1.2 将当前样例分析 prompt 收编为正式系统提示词资源

## 2. 模型调用与解析

- [x] 2.1 实现样例视频分析的 agent 调用链路
- [x] 2.2 实现模型原始输出的 JSON 提取、schema 校验和修复逻辑
- [x] 2.3 为非法输出、字段缺失和低质量结果增加标准化错误或降级返回

## 3. 结果标准化

- [x] 3.1 定义 agent 原始 JSON 输出结构与后端标准结果结构之间的映射
- [x] 3.2 定义将 agent 输出转换为现有前端 view-model 所需字段的映射规则

## 4. 多 Agent 预留

- [x] 4.1 在设计层明确 `ReferenceAnalyzerAgent` 在后续多 agent 系统中的位置
- [x] 4.2 为后续 `AssetAnalyzerAgent`、`GapDetectorAgent` 和 `TransferPlannerAgent` 预留上游输入契约

## 5. 验证

- [x] 5.1 使用真实样例视频验证 agent 输出的 JSON 结构完整性
- [x] 5.2 对比 heuristic 分析结果与 agent 分析结果，记录质量差异与已知风险
