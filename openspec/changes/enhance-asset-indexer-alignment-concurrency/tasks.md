## 1. 增强 SessionSharedMemory 并发安全与数组操作

- [ ] 1.1 在 SessionSharedMemory 中新增 `threading.Lock` 保护所有写入操作
- [ ] 1.2 新增 `append_to_array` 方法：支持 append 新条目到现有数组（如 `asset_index.assets`）
- [ ] 1.3 新增 `_ensure_asset_index_initialized` 辅助方法：如果 asset_index 不存在先初始化空数组结构

## 2. 更新 AssetIndexerAgent 为异步并发（保持 BaseAgent 同步接口兼容）

- [ ] 2.1 新增私有异步方法 `async def _async_analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]`
- [ ] 2.2 保持公共 analyze 为同步方法，内部用 `asyncio.run(self._async_analyze(...))` 运行异步并发
- [ ] 2.3 用 `asyncio.Semaphore(3)` 控制最大并发数
- [ ] 2.4 用 `asyncio.to_thread()` 包装单个素材的 `_analyze_single_asset` 调用，保持兼容现有阻塞式 ArkChatProvider

## 3. 实现参考样例上下文注入

- [ ] 3.1 更新 `_analyze_single_asset` 签名：新增 `reference_analysis: Optional[Dict]` 参数
- [ ] 3.2 注入三个字段作为上下文前缀：`type_label`、`summary`、`migration_suggestion`
- [ ] 3.3 向后兼容：无 reference_analysis 时跳过注入

## 4. 更新依赖关系与 Agent 注册

- [ ] 4.1 在 `AgentRegistration` 中把 `"reference_analysis"` 加到 `optional_reads` 数组
- [ ] 4.2 保持 `AssetIndexerAgent.read_keys` 不变（仍然是 `["inputs.uploaded_videos"]`）

## 5. 实现单素材即时落盘与并发安全

- [ ] 5.1 每次单个素材分析完立即调用 `append_to_array` append 进 `asset_index.assets`
- [ ] 5.2 自动 log `STEP_WRITE` 事件
- [ ] 5.3 失败处理：单个素材失败打 `STEP_WARNING` 事件，继续其他素材

## 6. 验证与测试

- [ ] 6.1 更新 `scripts/test_full_pipeline.py` 包含新特性验证
- [ ] 6.2 本地全链路冒烟测试通过
