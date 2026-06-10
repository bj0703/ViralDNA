## 1. Frontend Job Bootstrap

- [x] 1.1 设计并实现前端“无 Job”首发流程，允许用户先选择参考视频和素材视频再发送第一条需求
- [x] 1.2 接入 `POST /api/orchestration/jobs`，把首条需求、文件数组和参考标记一次性提交并保存返回的 `job_id`
- [x] 1.3 在顶层统一维护 `currentJobId`，确保左栏、中栏、右栏在建任务成功后同步切换到同一 Job
- [x] 1.4 为建任务失败场景补充前端错误提示和本地待上传状态保留
- [x] 1.5 在左栏样例视频区维护唯一 `selectedReferenceVideoId`，点击样例视频时更新选中态并同步给后续请求

## 2. Message Driven Workflow

- [x] 2.1 调整右侧消息输入逻辑，在无 `currentJobId` 时走创建任务，在已有 `currentJobId` 时走 `re-submit`
- [x] 2.2 为首条消息和后续追问建立统一的消息回显和执行中状态
- [ ] 2.3 验证创建新 Job 后 SSE 自动连接建立，且 `plan_ready` 与步骤事件能实时驱动右侧进度
- [x] 2.4 让创建 Job 与后续参考分析请求都携带 `selectedReferenceVideoId`，并在后端共享记忆中保存 `inputs.selected_reference_video_id`
- [x] 2.5 调整参考分析目标选择逻辑，优先解析选中的样例视频，失效时再回退到第一个参考视频

## 3. Upload Delivery

- [x] 3.1 在后端补齐编排上传资源的只读访问端点，并限制访问范围在编排上传目录内
- [x] 3.2 统一前端上传资源的 URL 生成方式，确保左栏和中栏使用同一访问路径
- [ ] 3.3 验证样例视频和素材视频在真实页面中可预览、可播放、可切换

## 4. Live Workbench Rendering

- [x] 4.1 把 `currentJobId` 传入中栏工作区，并在切换 Job 时拉取当前共享记忆快照
- [x] 4.2 用真实 `reference_analysis` 替换样例视频 Tab 的 mock 内容
- [x] 4.3 用真实 `asset_index` 替换素材视频 Tab 的 mock 内容
- [x] 4.4 用真实 `slot_matches`、`edit_timeline` 和 `final_video_meta` 替换结果视频 Tab 的 mock 内容
- [x] 4.5 通过 SSE 事件或重新取数机制让中栏在 Agent 产出后自动刷新

## 5. End to End Validation

- [ ] 5.1 验证用户仅通过前端即可完成“上传文件 -> 发送首条需求 -> 自动建任务 -> 实时执行 -> 页面渲染”
- [ ] 5.2 验证已有 Job 下继续发送消息时走增量 `re-submit`，且页面不需要刷新
- [ ] 5.3 验证刷新页面或重新进入同一 Job 时，至少可以恢复共享记忆驱动的当前展示状态
- [ ] 5.4 验证存在多条样例视频时，鼠标点击选中的视频才会被 `ReferenceAnalyzerAgent` 解析
