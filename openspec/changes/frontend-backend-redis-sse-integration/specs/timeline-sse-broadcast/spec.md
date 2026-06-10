# Timeline SSE Broadcast Specification

## 1. Overview
时间线编辑操作实时写入后端，通过 SSE 广播给所有连接该 Job 的客户端，实现多用户协作秒级同步。

## 2. Requirements

### 2.1 Edit Operations
所有时间线编辑操作通过以下 REST API 发送给后端：
- `PATCH /jobs/{job_id}/timeline/segments/{segment_id}` - 更新片段属性
- `POST /jobs/{job_id}/timeline/segments` - 新增片段
- `DELETE /jobs/{job_id}/timeline/segments/{segment_id}` - 删除片段

### 2.2 Optimistic UI Update
用户执行拖拽、调整时长、修改属性等操作时，前端立即更新本地时间线画面，同时异步派发 API 请求。用户操作无任何等待延迟。

### 2.3 Backend Write + Broadcast
后端收到任意编辑请求后：
1. 更新 Redis 中 `edit_timeline` 结构化数据
2. 追加写入 **`timeline_updated`** SSE 事件到事件流（不再命名为 timeline_segment_updated，单事件名覆盖所有编辑场景）
3. 所有连接该 job_id 的 SSE 客户端 0.5s 内收到该事件
4. 客户端收到 `timeline_updated` 后直接拉取 `/jobs/{job_id}/timeline` 拿到完整最新时间线覆盖本地状态

### 2.4 Three-Tab Structured Data Strategy
三个 Tab 永远优先直接读取 shared_memory.entries 里的结构化业务结果：
- `reference_analysis` → 样例视频 Tab
- `asset_index` → 素材视频 Tab
- `edit_timeline` → 结果视频 Tab
事件流只负责记录执行轨迹和发送「状态变更通知信号」，绝不把事件流当业务数据库用。

### 2.5 Multi User Sync
任意一个客户端修改时间线，其他所有打开同 Job 页面的浏览器窗口自动同步最新时间线状态，画面完全一致。

## 3. Acceptance Criteria
- 拖拽片段松手后立即显示新位置，不等待网络请求返回
- 两个浏览器窗口同时打开同一个 Job，窗口A修改片段后，窗口B 0.5s 内自动看到更新
- 刷新页面后时间线状态与修改前完全一致
