## Context

当前系统已经能从样例视频中提取四类关键信号：结构槽位线、BGM 卡点线、转场切换线和节奏热度线。它们已经在样例视频工作台中可视化，但后端下游仍然沿用单版本数据流：

- `slot_matches` 只有一套槽位匹配结果
- `resolved_gaps` 只有一套补口策略
- `edit_timeline` 只有一条时间线
- `final_video_meta` 只有一个渲染产物

这意味着参考分析中的多维信息没有真正参与“生成多个可比较成片”的能力，只能停留在观察层。这个变更需要在不推翻现有架构的前提下，把四个维度升级为四个受控变体，并且让前后端都能消费这些变体结果。

## Goals / Non-Goals

**Goals:**
- 将四个分析维度正式建模为四个变体：`structure`、`beat`、`transition`、`rhythm`。
- 让槽位匹配、补口、剪辑规划、渲染结果都按变体输出。
- 保持样例解析只执行一次，避免把整条工作流复制成四份互相独立的任务。
- 在新结构落地时保留默认变体兼容字段，降低对现有前端和编辑接口的破坏。
- 让结果视频页能够切换查看四个版本及其关联元数据。

**Non-Goals:**
- 不在本次变更中重新设计样例视频解析 prompt 本身。
- 不在本次变更中引入全新的渲染引擎或新的媒体基础设施。
- 不要求四个变体在首版就达到极强的风格差异，只要求它们沿不同匹配和规划偏好稳定输出。
- 不把四个变体建模为四套完全独立的结构模板体系。

## Decisions

### 1. 使用“共享骨架 + 变体偏好”而不是“四条完全独立工作流”

系统继续以 `reference_analysis.structural_slots` 作为统一骨架，四个变体只是对同一骨架施加不同的匹配与规划偏好：

- `structure`: 优先保留槽位角色、信息功能和整体结构顺序
- `beat`: 优先对齐卡点、时长和运动强度
- `transition`: 优先对齐相邻片段的转场方式和切换连续性
- `rhythm`: 优先对齐快慢起伏、镜头密度和节奏曲线

这样做的原因：
- 复用现有 `reference_analysis` 和 `structural_slots`
- 避免把 gap resolver、timeline editor、renderer 复杂度放大四倍
- 让四个版本可比较，因为它们共享同一结构骨架

备选方案是为四个维度分别生成独立模板并独立编排，但这会显著放大实现成本、数据合同复杂度和渲染调试成本，因此不采用。

### 2. 在共享内存与接口层统一引入 `variants` 容器

后端结果结构统一升级为：

- `slot_matches.variants`
- `resolved_gaps.variants`
- `edit_timeline.variants`
- `final_video_meta.outputs`

每个变体都有稳定的 `variant_id`、标签、置信度和版本内数据。顶层仍保留默认变体的兼容字段，例如：

- `slot_matches.slot_assignments` 指向默认变体
- `edit_timeline.timeline` 指向默认变体
- `final_video_meta.output_path` 指向默认变体输出

这样做的原因：
- 让新旧消费者可以分阶段迁移
- 保留 timeline editor 等旧接口的基本可用性
- 避免一次性把所有读路径都改成 breaking change

备选方案是直接把所有单字段替换成数组或映射，不保留兼容字段；这会让当前工作台与编辑服务在过渡期完全不可用，因此不采用。

### 3. 将四变体生成放在 `SlotMatcherAgent` 之后逐层传播

四个版本的分叉从 `SlotMatcherAgent` 开始，而不是从 `ReferenceAnalyzerAgent` 开始。`reference_analysis` 只负责声明四个维度蓝图，例如变体标签、匹配重点和规划重点；真正的数据分叉发生在：

1. `SlotMatcherAgent` 输出四套 `slot_assignments`
2. `GapResolverAgent` 针对每套未填充槽位生成补口方案
3. `EditPlannerAgent` 基于每套匹配和补口方案生成时间线
4. `FinalVideoRendererAgent` 按时间线逐套渲染成片

这样做的原因：
- 样例解析已经足够重，不适合重复四次
- 变体差异本质上属于素材选择和剪辑偏好，而不是基础视频理解
- 符合当前 Agent 链路的职责边界

### 4. 前端结果页使用“单页切换”而不是“四页并列”

结果视频页增加变体切换器，单次只激活一个变体，播放器、时间线、匹配说明、补口说明和校验摘要都跟随切换。

这样做的原因：
- 当前结果页已经围绕单一 `editTimeline` 和 `finalVideoMeta` 组织，切换模式更易接入
- 四屏并列会显著增加前端复杂度，并且对窄屏不友好
- 用户最常见动作是比较和挑选，不是同时逐帧审查四个版本

### 5. 渲染结果采用“多输出列表 + 默认输出回退”

`FinalVideoRendererAgent` 增加 `outputs` 列表，每条记录包含：

- `variant_id`
- `label`
- `output_path`
- `output_url`
- `success`
- `rendered_segment_count`
- `file_size_bytes`

同时保留顶层 `output_path`、`output_url` 指向默认变体。文件名使用变体后缀，例如：

- `final_rendered_v12_structure.mp4`
- `final_rendered_v12_beat.mp4`

这样做的原因：
- 保持与当前输出文件查询接口兼容
- 便于用户在工作台与文件系统中识别版本

## Risks / Trade-offs

- [单次任务耗时显著上升] -> 先复用一次参考解析和一次素材索引，只在匹配、规划、渲染阶段分叉；必要时再引入并行渲染。
- [共享内存结果结构变复杂] -> 明确 `variants` 合同，并为默认变体保留兼容字段，避免旧读路径立即失效。
- [四个变体首版差异不明显] -> 在 `SlotMatcherAgent` 和 `EditPlannerAgent` 中显式引入不同评分权重与规划偏好，确保至少行为路径不同。
- [前端结果页改造范围扩大] -> 先只改结果视频页，样例视频页继续展示单份 `reference_analysis`，控制首版范围。
- [编辑服务只支持单时间线] -> 首版以默认变体继续驱动现有编辑接口，多变体编辑能力后续再扩展。

## Migration Plan

1. 在后端新增变体结果结构，同时保留默认兼容字段。
2. 先让工作流写出四套匹配、补口、时间线和渲染结果，但默认读路径仍指向 `structure` 版本。
3. 更新结果视频页，优先消费 `variants` / `outputs`；若缺失则回退到旧单结果结构。
4. 验证新结构稳定后，再决定是否让时间线编辑接口支持指定 `variant_id`。

回滚策略：
- 如果多变体逻辑不稳定，可让写入层只回填默认 `structure` 版本到旧字段，前端仍能按旧方式展示。

## Open Questions

- 四个变体的默认排序是否固定为 `structure -> beat -> transition -> rhythm`，还是要支持后续动态配置？
- 时间线编辑服务是否需要在本次变更中同时支持按 `variant_id` 编辑，还是先只保证默认变体可编辑？
- 四个变体是否都必须渲染成功才算任务成功，还是允许部分成功并在前端标记失败版本？
