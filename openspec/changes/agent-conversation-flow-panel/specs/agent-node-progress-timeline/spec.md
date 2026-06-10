## ADDED Requirements

### Requirement: 系统在右栏顶部展示 Agent 节点流转进度条
系统 SHALL 在对话面板的顶部固定展示横向圆点节点流转进度条， SHALL 可视化当前多 Agent 流水线的执行状态。

#### Scenario: 初始状态展示所有节点
- **WHEN** 用户刚提交分析请求时
- **THEN** 进度条展示所有 Agent 节点，每个待运行节点都是空心白圆样式

#### Scenario: 节点进入运行中状态
- **WHEN** 某一个 Agent 开始执行
- **THEN** 该节点变为紫蓝色实心圆，显示呼吸动画效果，表示当前正在运行

#### Scenario: 节点完成执行
- **WHEN** 某一个 Agent 执行完毕
- **THEN** 该节点变为黑色实心圆，圆内显示白色对勾图标，表示该 Agent 任务已成功完成

#### Scenario: 节点执行失败
- **WHEN** 某一个 Agent 执行过程中发生错误
- **THEN** 该节点变为红色实心圆，圆内显示白色叉号图标，表示任务执行失败
