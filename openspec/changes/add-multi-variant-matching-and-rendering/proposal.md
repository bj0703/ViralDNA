## Why

当前样例视频虽然已经能解析出结构槽位、BGM 卡点、转场风格和节奏曲线，但下游槽位匹配、剪辑规划和最终渲染仍然只生成单一版本，导致这些维度只能作为参考展示，不能真正转化为多版本创作能力。现在需要把这四个维度变成可执行的输出分支，让系统一次分析后返回四个风格侧重不同的成片版本，支撑工作台比较、挑选和后续迭代。

## What Changes

- 新增多变体剪辑输出能力，基于同一份样例解析结果生成 `structure`、`beat`、`transition`、`rhythm` 四个变体版本。
- 扩展槽位匹配输出，从单份 `slot_matches` 升级为按变体分组的匹配结果，同时保留默认版本兼容字段。
- 扩展补口与剪辑规划输出，使 `resolved_gaps` 和 `edit_timeline` 都能承载四套变体结果。
- 扩展最终渲染输出，使系统一次任务返回四个成片文件及其元数据，而不是单个 `final_video_meta`。
- 更新结果视频工作台，允许用户切换四个版本并查看每个版本对应的时间线、匹配说明、补口策略和渲染结果。

## Capabilities

### New Capabilities
- `multi-variant-edit-output`: 将样例视频的四个分析维度转化为四套可执行的匹配、规划、渲染和前端展示结果。

### Modified Capabilities

## Impact

- 影响后端 `slot_matcher`、`gap_resolver`、`edit_planner`、`final_video_renderer` 以及共享内存中的结果结构。
- 影响编排接口返回的数据合同，包括 `slot_matches`、`resolved_gaps`、`edit_timeline`、`final_video_meta` 的结构和兼容策略。
- 影响前端结果视频页的数据读取与交互模型，需要支持版本切换而不是单结果展示。
- 不引入新的外部依赖，但会增加单次任务的渲染次数、存储占用和任务执行时长。
