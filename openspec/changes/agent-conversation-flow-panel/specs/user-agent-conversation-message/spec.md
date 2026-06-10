## ADDED Requirements

### Requirement: 系统支持用户消息右对齐气泡
系统 SHALL 在对话面板中渲染用户发送的消息， SHALL 使用右对齐紫蓝色主色气泡样式。

#### Scenario: 提交用户消息
- **WHEN** 用户在底部输入框中输入内容并发送
- **THEN** 对话面板右侧立即追加一条右对齐的用户消息气泡，背景色为 --color-primary-500，文字为白色

### Requirement: 系统支持 Agent 消息两层结构
系统 SHALL 渲染 Agent 回复消息， SHALL 天然拆分为「可折叠思考过程区块」和「最终结果区块」两层。

#### Scenario: Agent 消息默认渲染
- **WHEN** Agent 开始输出内容
- **THEN** Agent 头像 + 名称在消息左上角，思考过程区块默认处于收起状态，只显示「思考过程」展开按钮

#### Scenario: 点击展开查看思考过程
- **WHEN** 用户点击 Agent 消息中的「思考过程」展开箭头
- **THEN** 完整的 Agent 思考过程内容在下方展开展示，箭头图标变为向下方向

#### Scenario: 点击收起隐藏思考过程
- **WHEN** 用户在展开状态下点击收起箭头
- **THEN** 思考过程内容被隐藏，只保留「思考过程」标题栏

### Requirement: 系统支持垂直流式逐字输出
系统 SHALL 支持 Agent 内容的流式增量追加渲染， SHALL 实现垂直方向逐字符/逐块输出效果。

#### Scenario: 流式追加内容
- **WHEN** 收到新的一段 Agent 思考内容流
- **THEN** 内容实时追加到当前正在输出的 Agent 消息的思考区块中，无需等待全部内容加载完成
