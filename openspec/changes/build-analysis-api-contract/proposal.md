## Why

当前样例分析能力已经有最小后端闭环，但前端工作台、自然语言输入和后续模块扩展还缺少稳定的前后端契约。如果不先固定 API、任务状态和分析结果 schema，后续前端开发和 agent 能力扩展会频繁返工。

## What Changes

- 定义分析模块面向前端的标准 API 契约，覆盖任务创建、任务查询、结构化结果获取和前端展示模型获取。
- 定义自然语言输入的意图识别接口，使“用户指令 -> 分析动作”具备统一入口。
- 统一分析任务状态、错误状态和结构化结果 schema，供前端工作台和后续 agent 模块复用。
- 明确前后端分离下的职责边界，约束前端只依赖业务能力接口，不直接耦合底层模型 provider。
- 固定当前模型调用契约只依赖 `ARK_API_KEY`、`ARK_ENDPOINT_ID` 和 `ARK_BASE_URL` 三个参数，并通过 HTTP `chat/completions` 请求调用豆包模型。

## Capabilities

### New Capabilities
- `analysis-api`: 提供样例分析模块的标准任务型 API、结果接口和前端展示模型接口。
- `analysis-intent-routing`: 提供自然语言指令到分析意图的识别与路由能力。

### Modified Capabilities

## Impact

- 影响 `backend` 的 API 路由设计、Pydantic schema、服务层边界和任务状态模型。
- 影响后端配置读取方式，要求配置层严格收敛到 `ARK_API_KEY`、`ARK_ENDPOINT_ID` 和 `ARK_BASE_URL` 三个环境变量。
- 为未来的 React 前端提供稳定调用面，降低接口变更带来的联动成本。
- 为后续结构迁移、素材缺口识别和自然语言改片预留统一调用入口。
