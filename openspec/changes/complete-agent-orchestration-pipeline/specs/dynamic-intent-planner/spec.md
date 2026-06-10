## ADDED Requirements

### Requirement: DynamicIntentPlanner 动态生成执行计划
DynamicIntentPlanner SHALL 基于用户自然语言输入和当前共享记忆状态，动态决定下一批要执行的Agent列表，不再硬编码幽灵Agent名字。

#### Scenario: 用户要求"只分析这个样例视频"
- **WHEN** 用户输入自然语言提示词"只分析这个样例视频"
- **THEN** 动态规划器只返回 [ReferenceAnalyzerAgent] 列表，不执行后续其他Agent

#### Scenario: 用户要求"用这些素材复刻爆款"
- **WHEN** 用户输入自然语言提示词"用这些素材复刻爆款结构"
- **THEN** 动态规划器返回完整5个Agent的有序列表，执行全流水线迁移

#### Scenario: 用户要求"只索引这些素材"
- **WHEN** 用户输入自然语言提示词"只索引这些素材内容"
- **THEN** 动态规划器只返回 [AssetIndexerAgent] 列表，不执行ReferenceAnalyzerAgent和后续流水线
