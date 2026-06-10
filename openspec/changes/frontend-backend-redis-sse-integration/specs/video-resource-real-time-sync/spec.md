# Video Resource Real Time Sync Specification

## 1. Overview
左侧边栏视频资源区与 Redis `inputs.uploaded_videos` 双向实时同步，支持样例视频和素材视频分离展示。

## 2. Requirements

### 2.1 Initial Load
组件挂载时调用 `GET /api/orchestration/jobs/{job_id}` 拉取全量 `shared_memory.inputs.uploaded_videos` 初始化本地 videoList 状态。

### 2.2 Upload Flow
- 用户上传样例视频 → 前端 FormData POST `/api/orchestration/jobs/{job_id}/upload-video?is_reference=true`
- 用户上传素材视频 → 前端 FormData POST `/api/orchestration/jobs/{job_id}/upload-video?is_reference=false`
- 上传成功后后端写入 Redis，同时发出 `resource_updated` SSE 事件

### 2.3 SSE Sync Flow
收到 SSE 事件 `event_type === 'resource_updated'` 后，直接将新的 `uploaded_videos` 数组替换本地状态，视频列表立即刷新。

### 2.4 Filter Display
- 样例视频 Tab：显示所有 `is_reference === true` 的视频
- 素材视频 Tab：显示所有 `is_reference === false` 的视频

### 2.5 Click Behavior
点击任意视频项，中间播放器自动加载该视频的 url 并切换播放。

## 3. Acceptance Criteria
- 上传视频后视频列表 1s 内自动新增展示
- 同 Job 下另一个浏览器窗口上传视频，当前窗口视频列表秒级同步更新
- 点击视频后中间播放器立即切换到对应视频播放
