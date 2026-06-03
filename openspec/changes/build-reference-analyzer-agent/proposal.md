## Why

当前样例视频分析仍以启发式规则为主，能够跑通流程，但还不能代表真实的视频理解能力。为了让后续结构迁移、素材缺口识别和多 agent 编排建立在可信的上游输入之上，需要新增一个正式的样例视频分析 agent，使用固定 prompt 和结构化 JSON 输出对样例视频进行深度拆解。

## What Changes

- 新增 `ReferenceAnalyzerAgent`，用于对样例视频执行真实的结构化理解。
- 将当前提供的样例分析 prompt 收编为正式系统提示词输入，而不是散落在实验脚本中。
- 定义样例分析 agent 的标准输出 schema，覆盖基础信息、脚本结构、节奏结构、包装与声音、迁移建议。
- 定义模型输出解析、JSON 校验与异常兜底逻辑，保证上游 agent 输出可被后续模块复用。
- 明确该 agent 在后续多 agent 系统中的职责边界和协作位置。

## Capabilities

### New Capabilities
- `reference-analysis-agent`: 使用多模态模型对样例视频进行结构化拆解，并输出可供迁移系统复用的标准 JSON 结果。

### Modified Capabilities

## Impact

- 影响 `backend` 中样例分析 provider、agent 编排层、结果标准化层和前端展示模型映射逻辑。
- 为后续 `asset-analyzer`、`gap-detector`、`transfer-planner` 等 agent 提供统一上游输入。
- 会改变当前启发式样例分析的实现路径，使“样例分析”从 demo 级能力升级为核心生产能力。
