## 1. 类型定义补齐

- [x] 1.1 在 frontend/src/types/index.ts 中新增 UploadedVideo、EditVersion、AgentNode、TimelineSegment、EditTrack 等核心类型
- [x] 1.2 新增 SSEEventPayload 事件类型定义
- [x] 1.3 验证 TypeScript 编译无类型错误

## 2. useSSEEventSource Hook 实现

- [x] 2.1 创建 frontend/src/hooks/useSSEEventSource.ts 文件
- [x] 2.2 实现基础 EventSource 连接管理，支持 jobId 动态切换
- [x] 2.3 实现指数退避重连策略 1s → 2s → 4s → 8s
- [x] 2.4 校准续传游标：统一用整数 offset（不是 UUID），重连时通过 query param last_event_id 直接传给后端 LRANGE 寻址
- [x] 2.5 实现连续 3 次失败自动降级到 1.5s 轮询兜底
- [x] 2.6 实现组件卸载自动关闭连接，无内存泄漏
- [ ] 2.7 单元测试验证 SSE Hook 各种场景

## 3. 视频资源区双向同步对接

- [x] 3.1 在左侧边栏视频资源组件中接入 useSSEEventSource
- [x] 3.2 组件挂载时自动拉取历史 uploaded_videos 初始化本地 videoList，监听 resource_updated SSE 事件
- [x] 3.3 上传视频后触发 POST /api/orchestration/jobs/{job_id}/upload-video 接口，收到事件自动刷新列表
- [x] 3.4 实现样例视频/素材视频按 is_reference 字段过滤分离展示
- [x] 3.5 点选视频项传入回调，为后续中栏播放铺路

## 4. 时间线 SSE 广播对接

- [ ] 4.1 时间线编辑操作实现乐观 UI 更新
- [ ] 4.2 拖拽/修改片段时异步派发 PATCH/POST/DELETE 编辑 API
- [ ] 4.3 接收 timeline_segment_updated 事件自动同步最新时间线状态
- [ ] 4.4 验证多浏览器窗口同时打开同 Job 页面，编辑操作实时双向同步

## 5. Agent 流式思考链对接（动态节点流转）

- [x] 5.0 校准核心断点：WorkflowOrchestrator 统一改用 get_or_create_shared_memory_redis，事件写入和 SSE/trace 读取完全同源
- [x] 5.0b 校准核心断点：App.tsx 顶层统一管理 jobId，左右两侧共享单源状态，不再各自维护独立 currentJobId
- [x] 5.1 在右侧 AgentConversationPanel 组件中接入 useSSEEventSource
- [x] 5.2 实现页面初始打开时对话区 messages/agentNodes 完全为空，干净空白
- [x] 5.3 实现 plan_ready 事件接收，动态生成全新 agentNodes 列表（节点数量和顺序由后端计划决定）
- [x] 5.4 实现 step_start 事件更新对应 agent_name 的 AgentNode 状态为 running
- [x] 5.5 实现 step_write 事件增量追加结果消息到对话区并标记节点 done
- [x] 5.6 实现 step_skip 事件标记节点状态为 skipped
- [x] 5.7 实现 step_fail 事件标记节点状态为 error
- [x] 5.8 接入 re-submit 提交接口，新指令发送后后端生成新 plan_ready 替换当前动态节点列表
- [x] 5.9 实现对话区顶部草稿箱入口按钮，主动点击才拉取历史事件
- [x] 5.10 校准：GET /jobs/{job_id}/trace 历史事件拉取，从事件流重建历史动态节点进度条
- [ ] 5.11 实现结果卡片点击弹出 DetailModal 查看完整报告

## 6. 三个 Tab Agent 输出映射

- [ ] 6.1 样例视频 Tab 接入 reference_analysis 数据，展示所有分析卡片
- [ ] 6.2 素材视频 Tab 接入 asset_index 数据，展示素材卡片网格和质量评分
- [ ] 6.3 结果视频 Tab 接入 SlotMatcher + EditPlanner 输出，展示完整多轨时间线和校验报告
- [ ] 6.4 验证 Agent 执行完成后对应 Tab 内容自动填充展示

## 7. 兼容性与全链路测试

- [x] 7.0 校准：新增 POST /api/orchestration/jobs/{job_id}/upload-video 单文件追加上传接口
- [x] 7.0b 校准：上传成功后后端广播 resource_updated 事件，payload 字段名对齐前端消费契约
- [ ] 7.1 验证原有 REST API 全部正常工作，向后兼容
- [ ] 7.2 模拟 SSE 网络断开场景，验证自动重连和断点续传
- [ ] 7.3 模拟 Redis 不可用场景，验证系统自动降级到内存模式零中断
- [ ] 7.4 端到端完整流程测试：上传视频 → Agent 执行 → 输出到三个 Tab → 编辑时间线 → 多用户同步
