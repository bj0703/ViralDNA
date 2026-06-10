## Why

前后端目前处于分离状态，前端UI组件与后端Agent执行、Redis共享内存、SSE事件流之间缺乏完整的数据对接链路。本变更将基于已有的「前后端数据操作流程.md」文档，补齐所有缺失的对接层，让视频资源管理、时间线实时同步、Agent流式思考链三大核心链路完全打通。

## What Changes

- 新增前端完整 SSE Hook `useSSEEventSource`，自动管理连接生命周期、断点续传、指数退避重连和降级轮询
- 补齐前端 TypeScript 类型定义，实现与后端 `SessionSharedMemory` 数据结构 100% 对齐
- 实现左侧边栏视频资源区与 Redis `inputs.uploaded_videos` 的双向实时同步
- 实现中间工作区时间线编辑操作通过 REST API 写入后端 + SSE 广播多用户协作同步
- 实现右侧 Agent 对话区通过 SSE 事件流实时渲染 step_start / step_write / step_fail 流式思考链
- 实现三个 Tab（样例视频/素材视频/结果视频）的内容从 Agent 输出自动映射展示
- 向后完全兼容原有 REST API，系统自动降级到内存模式保证零中断

## Capabilities

### New Capabilities
- `frontend-sse-hook`: 实现自动管理 SSE 连接的 useSSEEventSource Hook，支持断点续传、重连策略和轮询兜底
- `shared-memory-data-binding`: 前后端数据结构类型契约定义，EditVersion / UploadedVideo / AgentNode 等核心类型完全对齐
- `video-resource-real-time-sync`: 左侧边栏视频资源区与 Redis uploaded_videos 的双向实时同步链路
- `timeline-sse-broadcast`: 时间线编辑操作实时写入后端并通过 SSE 广播给所有连接该 Job 的客户端
- `agent-streaming-think-chain`: 右侧对话区通过 SSE 事件流增量渲染 Agent 完整执行思考过程
- `three-tab-agent-output-mapping`: 三个工作区 Tab 自动映射对应 Agent 输出结果进行可视化展示

### Modified Capabilities
无现有 spec 需求变更，所有能力为新增对接层。

## Impact

- `frontend/src/hooks/useSSEEventSource.ts` （新文件）
- `frontend/src/types/index.ts` （补齐类型定义）
- 左侧边栏视频资源组件的状态绑定逻辑
- 中间时间线组件的编辑事件派发与 SSE 状态监听
- 右侧 Agent 对话区组件的 SSE 事件接入
- 三个 Tab 区域的数据映射渲染组件
- 所有原有 REST API 向后 100% 兼容保留
