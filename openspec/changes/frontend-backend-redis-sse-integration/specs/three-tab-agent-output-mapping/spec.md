# Three Tab Agent Output Mapping Specification

## 1. Overview
三个工作区 Tab 自动映射对应 Agent 输出结果，直接可视化展示无需额外数据转换。

## 2. Requirements

### 2.1 Sample Video Tab
展示 `ReferenceAnalyzerAgent` 输出的全部 `reference_analysis` 字段：
- 视频基础信息卡片：时长/类型标签/有效时长概览
- 脚本分段结构：Hook → Develop → CTA 三段式可折叠时间线卡片
- 结构化槽位详情：每个槽位的时间范围、创作功能、画面类型
- 节奏曲线图示：平均镜头时长和节奏快慢可视化
- 字幕包装风格配置
- 转场风格规则
- 迁移注意事项清单：must_keep / can_adapt / must_not_copy

### 2.2 Material Video Tab
展示 `AssetIndexerAgent` 输出的全部 `asset_index` 字段：
- 素材卡片网格：缩略图+文件名+时长+标签
- 候选片段列表：素材内部自动切分的segments详情
- 分类标签云，点击标签筛选同类型素材
- 三维可视化质量评分条：visual_quality / lighting_quality / subject_clarity
- best_for_slot_types：展示该素材最适合的槽位类型

### 2.3 Result Video Tab
展示 SlotMatcher + EditPlanner 串联输出的合并结果：
- 槽位匹配结果列表：每个槽位 → 对应选中的素材片段 + 匹配分数
- 缺口明细列表：unfilled_slots + 建议解决策略
- 完整多轨时间线可视化：主视频轨+音频轨+字幕轨全可拖拽
- 剪辑总校验报告：结构保真度得分 + 自动检查警告
- 封面设计方案预览：主标题/副标题
- 人工审核要点提示

## 3. Acceptance Criteria
- ReferenceAnalyzerAgent 执行完成后，样例视频 Tab 自动填充所有分析结果卡片
- AssetIndexerAgent 完成后素材视频 Tab 自动展示全部素材卡片网格
- EditPlanner 输出后结果视频 Tab 自动展示完整时间线和剪辑校验报告
