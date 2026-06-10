## Why

当前 GapResolverAgent 只输出抽象的补齐方案描述，无法实际执行生成新素材，当素材缺口出现时只能依赖现有素材或纯逻辑调整。现在将7级补齐策略中的可执行能力落地，直接生成 text_card、static_graphic、ai_generate 三类真实视频片段，自动补充到素材库中，从根本上解决素材不足问题。

## What Changes

- 新增 `GeneratedAssetFactory` 工厂类，统一管理所有AI生成素材的生命周期
- 新增 GapResolverAgent 后置执行阶段，将 resolved_gaps 中的补齐方案转化为实际执行的FFmpeg渲染操作
- 实现 text_card 策略：用FFmpeg drawtext滤镜生成0.5-2秒的文字卡片视频
- 实现 static_graphic 策略：从关键帧加Ken Burns视差动效生成短视频
- 集成 reference-driven-generator Skill，支持基于参考片段生成AIGC图片/短视频
- 自动将生成的新素材追加写入共享记忆的 asset_index.assets 数组，下游 EditPlanner 无需任何修改直接引用新 asset_id
- 所有生成文件持久化到 `data/{job_id}/generated_assets/` 目录

## Capabilities

### New Capabilities
- `generated-asset-factory`: 统一生成素材工厂，管理所有生成素材的生命周期和持久化存储
- `text-card-generator`: FFmpeg文字卡片生成器，直接渲染带文字的动态视频片段
- `ken-burns-generator`: Ken Burns视差动效生成器，静态图片转带放大运动的短视频
- `gap-resolver-execution-layer`: GapResolverAgent执行层，补齐抽象方案为可执行生成逻辑

### Modified Capabilities
- 无现有需求变更，完全向后兼容

## Impact

- 新增文件：`backend/app/providers/generated_asset_factory.py`
- 修改文件：`backend/app/agents/gap_resolver.py` 新增后置执行阶段
- 依赖FFmpeg drawtext滤镜，无额外第三方依赖
- 不改变任何现有Agent接口和数据结构
