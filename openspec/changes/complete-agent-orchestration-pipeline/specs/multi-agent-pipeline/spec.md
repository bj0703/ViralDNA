## ADDED Requirements

### Requirement: 5个Agent 基于共享记忆自动DAG拓扑执行
系统 SHALL 实现5个真实可用的Agent，每个Agent从共享记忆读取read_keys指定的数据，处理后把结果写回write_keys指定的位置，通过拓扑排序自动按依赖顺序执行。

#### Scenario: 单样例分析模式
- **WHEN** 用户上传一个标记为is_reference=True的视频，没有其他素材
- **THEN** 流水线自动执行ReferenceAnalyzerAgent，输出reference_analysis结果，直接完成任务

#### Scenario: 全流水线迁移模式
- **WHEN** 用户上传1个样例视频 + N个素材视频
- **THEN** 流水线自动按顺序执行：ReferenceAnalyzerAgent → AssetIndexerAgent → SlotMatcherAgent → GapResolverAgent → EditPlannerAgent，全部结果依次写入共享记忆

#### Scenario: 仅素材索引模式
- **WHEN** 用户上传全部视频都标记为is_reference=False（没有参考样例）
- **THEN** 流水线自动跳过ReferenceAnalyzerAgent，直接执行AssetIndexerAgent完成素材索引任务

### Requirement: 拓扑排序依赖校验失败快速失败
系统 SHALL 在检测到Agent的read_keys指定的依赖永远无法满足时，抛出明确的AgentDependencyUnsatisfiedError异常，而不是静默跳过继续执行。

#### Scenario: 缺失reference_analysis强行运行SlotMatcherAgent
- **WHEN** 用户手动指定执行SlotMatcherAgent，但共享记忆里没有reference_analysis
- **THEN** 系统立即抛出异常，提示用户SlotMatcherAgent缺少必须的前置依赖reference_analysis，终止流水线

### Requirement: Agent 标准接口规范
所有Agent SHALL 继承BaseAgent抽象基类，统一具备read_keys、write_keys属性和analyze(shared_memory)方法签名。

#### Scenario: 遍历所有注册Agent
- **WHEN** 系统启动后遍历AgentRegistry中所有注册的Agent
- **THEN** 每个Agent都可直接访问其read_keys和write_keys字符串列表，无需额外反射
