## Context

当前 AssetIndexerAgent：
- 只读 `["inputs.uploaded_videos"]`，完全不参考 reference_analysis
- 9个素材串行逐个分析，每个调用 ArkChatProvider 耗时2-3秒，总耗时20-30秒
- 必须等全部素材分析完才统一写 asset_index，无实时进度反馈

**重要约束**：
1. BaseAgent 接口约定 `analyze` 是同步方法 `def analyze(...)`，不能直接改成 `async def`，否则会破坏所有其他 Agent 的接口契约
2. 但 WorkflowOrchestrator 已经用 `asyncio.to_thread(agent_instance.analyze, ...)` 包装了所有 Agent 的 analyze 调用，所以在 AssetIndexerAgent 内部用 `asyncio.run()` 运行内部 async 逻辑完全兼容

本次增强完全向后兼容，纯素材索引场景不引入 reference_analysis 依赖时保持原样。

## Goals / Non-Goals

**Goals:**
- 素材分析方向100%与参考样例对齐
- 9个素材分析总耗时从25秒降到6-8秒（3路并发）
- 单素材分析完立即落盘，前端实时看到进度

**Non-Goals:**
- 不修改现有 ASSET_INDEXER_SYSTEM_PROMPT
- 不修改外部 API 接口契约
- 不做持久化增强（仍用内存共享记忆）

## Decisions

| Decision | Option A (选择) | Option B (弃选) | Rationale |
|---|---|---|---|
| 并发实现方案 | `asyncio.Semaphore(3)` + `async def analyze` | ThreadPoolExecutor | 用户明确选择 asyncio，保持与系统整体异步架构一致 |
| reference_analysis 依赖位置 | `optional_reads` | `reads` | 纯素材索引场景没有样例，不应该阻塞执行 |
| 并发控制 | `asyncio.Semaphore(3)` 最大3路 | 无限制并发或固定5路 | 3路是用户明确指定的数量，平衡性能和大模型API容量 |
| 参考样例上下文注入 | 注入三个字段：`type_label` + `summary` + `migration_suggestion` | 只注入 type_label + summary | 用户明确提到需要加入 migration_suggestion，对齐更完整 |
| 单素材即时落盘 | 每次分析完立即 append 进 `asset_index.assets` 数组 | 全部素材跑完一次性写入 | 提升前端实时体验，单素材失败不影响其他 |
| 并发安全 | 共享记忆锁保护 assets 数组 | 无锁自由追加 | 防止并发竞态条件覆盖数据 |
| 失败处理 | 单个素材失败打 warning 标记，继续其他素材 | 任意素材失败直接抛出异常中断全部 | 保证 9个素材尽量都跑完，最大化可用素材数量 |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| 3路并发可能短暂占用更多API配额 | 用户明确接受，3路在合理范围内，无风险 |
| 参考样例上下文注入可能增加 prompt 长度 | injection 部分控制在 200 字符内，可接受 |

## Implementation Pitfalls（融合现有代码必须注意的关键坑）

| Pitfall | 现状 | 解决方案 |
|---|---|---|
| **BaseAgent analyze 是同步抽象方法，不能直接改成 async def** | BaseAgent 接口约定 `def analyze(...)`，不支持 async | 新增私有 async 方法 `async def _async_analyze`，保持公共 analyze 同步，内部用 `asyncio.run` 运行异步并发 |
| **WorkflowOrchestrator 包装兼容性** | ✅ orchestrator 已经用 `asyncio.to_thread(agent_instance.analyze, ...)` 包装所有调用 | 完全兼容我们的方案，无需修改 orchestrator |
| **SessionSharedMemory 完全没有线程锁保护** | entries、event_log 都是普通 Python dict/list | 新增 `threading.Lock` 保护所有写入操作 |
| **SessionSharedMemory 缺少数组 append API** | 只有 `set(key, data)` 完全覆盖写入 | 新增 `append_to_array` 方法和 `_ensure_asset_index_initialized` 辅助方法 |
| **reference_analysis 依赖位置** | 纯素材索引场景没有样例，不能阻塞执行 | 加到 `AgentRegistration.optional_reads` 数组里，保持 `reads` 不变 |
| **Asyncio 嵌套事件循环问题** | orchestrator 已经在 asyncio 事件循环里，再在同步 analyze 里用 `asyncio.run()` 可能出现 nested loop | `asyncio.to_thread()` 已经把整个 analyze 放在后台线程，线程内新建事件循环用 `asyncio.run()` 完全安全，不会嵌套冲突 |

## Migration Plan

1. 更新 SessionSharedMemory：新增线程锁、append_to_array 等
2. 更新 AssetIndexerAgent：异步并发 + 上下文注入
3. 更新 dependencies.py：optional_reads 注册
4. 保持 API 完全向后兼容，无需迁移

## Open Questions

- 暂无，所有设计细节已明确
