# Agent Streaming Think Chain Specification

## 1. Overview
右侧 Agent 对话区通过 SSE 事件流增量渲染 Agent 完整执行思考过程，流式竖展示思考链。页面刚打开时对话区为干净空白状态，不自动加载任何历史内容。**Agent 节点列表完全动态生成，由后端每次意图识别后的执行计划决定显示哪几个节点。**

## 2. Requirements

### 2.0 Agent Name Display Mapping
建立后端 Agent 类名到前端显示名称的映射表：
| 后端 Agent Class Name | 前端显示名称 |
|---|---|
| ReferenceAnalyzerAgent | 参考分析 |
| AssetIndexerAgent | 资产索引 |
| SlotMatcherAgent | 插槽匹配 |
| GapResolverAgent | 间隙解析 |
| EditPlannerAgent | 编辑规划 |
| FinalVideoRendererAgent | 最终渲染 |

### 2.1 Initial Load (关键行为)
- 页面首次打开 / 切换到新 Job 时，对话区 `messages` 和 `agentNodes` 初始化为完全空的状态
- 绝对不自动拉取、渲染该 Job 任何历史对话事件
- 用户视野内刚进入页面看到的是一个干净、空的对话输入框区域

### 2.2 Dynamic Nodes Lifecycle (动态节点核心逻辑)
- 用户发送指令后，后端 LLM 意图规划生成 `selected_agent_names` 列表，先广播一个 `plan_ready` SSE 事件
- 前端收到 `plan_ready` 事件后，立即清空旧的节点列表，动态生成全新的 `agentNodes`：
  - 把事件 payload 里的 `selected_agent_names` 数组逐个转成前端显示名称
  - 全部节点初始状态为 `pending`
  - 节点数量和顺序完全由后端这次返回的计划决定，不是硬编码固定6个
  - 比如用户只发"只分析样例"，这次就只显示1个节点：「参考分析」
- 节点进度条连线也自动根据这次实际节点数量自适应渲染

### 2.3 草稿箱历史加载
- 对话区顶部新增「草稿箱」按钮/入口
- 用户主动点击「草稿箱」时才触发调用 `GET /jobs/{job_id}/events?limit=100` 拉取该 Job 的全部历史事件
- 历史事件拉取完成后，从历史事件里重建当时的执行计划节点列表，恢复完整的思考链进度条
- 用户可随时点击草稿箱收起/展开历史内容

### 2.4 Event Mapping
| SSE Event Type | UI Behavior |
|---|---|
| `plan_ready` | 清空旧节点，用 payload.selected_agent_names 动态生成全新的 agentNodes 列表 |
| `step_start` | 对应 agent_name 的节点状态置为 `running`，进度条该位置点亮为蓝色呼吸动画 |
| `step_write` | 追加 Agent 输出结果消息到对话区，弹出结果卡片，对应节点状态置为 `done`，连线变为黑色 |
| `step_skip` | 对应节点状态置为 `done` 显示灰色打勾，代表该步跳过（增量模式） |
| `step_fail` | 对应节点状态置为 `error` 显示红色叉号，展示错误信息 |

### 2.5 Streaming Render
- 收到 plan_ready 后立刻看到动态生成的进度节点，不需要等任何 Agent 开始执行
- 每个 Agent 开始执行 → 对应节点状态变成 running 蓝色呼吸动画
- Agent 输出内容 → 增量追加渲染，打字机效果实时显示
- Agent 全部串行执行过程中，页面不需要任何刷新，SSE 长连接持续复用

### 2.6 Result Card Detail
点击任意结果卡片，弹出 DetailModal 查看该 Agent 输出的完整报告内容。

### 2.7 Re-submit Flow
用户在输入框发送新的自然语言指令 → `POST /jobs/{job_id}/re-submit`，后端重新运行意图规划生成新的 plan_ready 事件，前端用新计划替换掉旧的动态节点列表，新一轮 Agent 执行的进度条完全由这次的新计划决定。

## 3. Acceptance Criteria
- 刚打开页面时对话区完全空白，看不到任何历史对话内容
- 发送「只分析样例」指令 → 动态进度条只显示1个节点：参考分析
- 发送「全流程复刻」指令 → 动态进度条显示完整的6个节点按顺序排列
- 收到 step_start 事件后对应节点立刻变成 running 呼吸状态
- 收到 step_write 事件后对应节点变成 done 黑色打勾，前面的连线变蓝
- 收到 step_fail 事件后对应节点变成红色叉号
- 多次 re-submit 不同指令，每次动态节点列表自动切换为这次计划对应的节点组合
- 点击草稿箱按钮可加载历史对话，从历史事件里重建当时的节点进度条
