## Why

当前项目已经具备后端 Agent 编排、Redis 共享记忆和 SSE 推流能力，但真实用户仍然无法只通过前端完成一次完整任务。用户必须依赖 Swagger 手动创建 Job、手动触发 `re-submit`，中间工作区也仍以 mock 内容为主，这使系统停留在集成演示阶段而非可用产品阶段。

## What Changes

- 新增前端首发任务入口，允许用户在页面内上传参考视频、上传素材视频、输入第一条需求并直接创建 Job。
- 新增消息驱动的工作流入口编排，统一“首次提交创建 Job”和“已有 Job 的二次追问 re-submit”两种前端发送行为。
- 新增“选中的样例视频”状态传递链路，确保存在多条样例视频时，后端优先解析用户鼠标点击选中的那一条。
- 新增前端工作区与后端真实结果的数据绑定，让三个 Tab 基于共享记忆中的结构化结果渲染页面，而不是依赖本地 mock。
- 新增编排任务上传文件的可访问交付链路，确保左栏和中栏可以真实预览/播放编排任务的上传资源。
- 统一前端 `currentJobId` 作为整页状态源，让左栏、 中栏、右栏和 SSE 连接围绕同一 Job 工作。

## Capabilities

### New Capabilities
- `frontend-job-bootstrap`: 用户可以只通过前端完成一次新 Job 的创建，包括首条需求输入、参考/素材上传和 Job 初始化。
- `message-driven-orchestration-flow`: 右侧消息输入区根据是否已有 Job 自动选择创建新任务或发起增量 `re-submit`。
- `workbench-live-data-rendering`: 中间三个工作区 Tab 基于后端共享记忆结果实时渲染真实内容，而不是静态 mock。
- `orchestration-upload-delivery`: 编排任务上传的资源必须有稳定可访问的后端交付路径，供前端真实预览和播放。

### Modified Capabilities

## Impact

- `frontend/src/App.tsx`
- `frontend/src/layouts/LeftSidebarContent.tsx`
- `frontend/src/layouts/CenterWorkbenchContent.tsx`
- `frontend/src/components/AgentConversationPanel.tsx`
- `frontend/src/components/SampleVideoSection.tsx`
- `frontend/src/components/SampleVideoTabContent.tsx`
- `frontend/src/components/MaterialVideoTabContent.tsx`
- `frontend/src/components/ResultVideoTabContent.tsx`
- `frontend/src/types/`
- `backend/app/api/routes/orchestration.py`
- `backend/app/core/shared_memory.py`
- `backend/app/core/shared_memory_redis.py`
- 现有 SSE 事件消费链路与前端 Job 状态管理
