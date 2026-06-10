## Why

emo_transfer 是多 Agent 编排系统，用户需要清晰看到整个 Agent 流水线的执行过程，而不只是最终结果。参考 TRAE 的对话交互格式和 AI 研究助手的节点流转进度条，我们需要在右栏打造一个垂直流式的对话面板：既能展示可折叠的 Agent 思考过程，又能通过圆点节点进度条可视化记录当前运行到哪一个 Agent，最终结果以格式化卡片输出并支持翻页浏览。

## What Changes

- 定义用户消息 + Agent 回复的对话消息体格式，Agent 回复天然拆分为「可折叠思考过程」+「最终结果」两层结构。
- 实现垂直流式输出模式，Agent 思考过程支持逐步展开/收起。
- 实现圆点节点流转进度条，实时可视化显示当前多 Agent 流水线的执行节点位置。
- 实现格式化结果卡片系统，每一个 Agent 完成任务后输出结构化卡片，支持多卡片翻页浏览。

## Capabilities

### New Capabilities
- `user-agent-conversation-message`: 定义右侧对话面板的用户消息与 Agent 回复消息格式，支持思考过程折叠与垂直流式渲染。
- `agent-node-progress-timeline`: 实现圆点节点流转进度条，实时展示当前 Agent 流水线运行状态与位置。
- `formatted-result-cards-pagination`: 实现格式化输出卡片系统，支持 Agent 完成后输出结构化结果卡片和多卡片翻页浏览。

### Modified Capabilities

## Impact

- 作为右栏操作区的核心业务组件，直接承接用户自然语言输入和 Agent 编排系统的流式输出。
- 完全复用之前 `three-column-layout-and-color-theme` 变更定义的三栏布局和 Soft Lavender 色彩主题，无需改动基础布局层。
