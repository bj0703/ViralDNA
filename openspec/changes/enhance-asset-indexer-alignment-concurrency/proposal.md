## Why

当前 AssetIndexerAgent 存在两个关键痛点：
1. **素材分析与参考样例方向对齐缺失**：AssetIndexerAgent 完全独立分析素材，不参考 ReferenceAnalyzerAgent 输出的 type_label、summary、migration_suggestion，导致素材标签、分类方向严重偏离样例主题，后续槽位匹配和剪辑编排质量差
2. **性能差等待时间长**：9个素材串行逐个分析，总耗时长达20-30秒，且必须等全部素材跑完才能落盘，用户体验很差

## What Changes

- **AssetIndexerAgent 引入样例上下文对齐**：新增读取 reference_analysis 的 read_keys，分析每个素材前注入 type_label、summary、migration_suggestion 三个字段作为上下文前缀，保证素材分析方向100%与参考样例一致
- **3路并发素材索引 + 单素材即时落盘**：用 asyncio.Semaphore(3) 控制最大并发数，每分析完一个素材立即 append 进 asset_index.assets，无需等全部素材跑完才落盘，前端实时看到索引进度
- **完全向后兼容**：纯素材索引场景（无 reference_analysis）注入部分自动跳过，不改变现有 behavior，所有改动都是增量增强

## Capabilities

### New Capabilities
- `asset-index-alignment`：素材索引与参考样例方向对齐能力
- `asset-index-concurrency`：3路并发单素材即时落盘能力

### Modified Capabilities
- `orchestration`：修改 AssetIndexerAgent 实现细节，但不改变外部接口契约，API 层完全兼容

## Impact

- 影响文件：`backend/app/agents/asset_indexer.py`、`backend/app/dependencies.py`（更新 Agent 注册的 read_keys）、`backend/app/prompts/asset_indexer.py`（可选微调，但本次先不改）
- API 完全向后兼容：接口入口、返回值结构不变
- 性能提升显著：9个素材分析总耗时从25秒降到6-8秒
