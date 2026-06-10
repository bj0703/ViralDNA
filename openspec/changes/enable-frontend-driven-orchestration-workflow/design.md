## Context

当前前端已经具备三栏工作台、左栏视频上传区、右栏 Agent 对话区和基础 SSE Hook，但真实业务闭环仍不完整：

- 用户无法从前端首次创建 Job，必须借助 Swagger 调用 `POST /api/orchestration/jobs`
- 右侧输入框只支持已有 Job 的 `re-submit`
- 中栏三个 Tab 仍以 mock 数据占位，未绑定 `reference_analysis`、`asset_index`、`edit_timeline`、`final_video_meta`
- 编排任务上传后返回的资源 URL 缺少明确稳定的文件访问交付链路
- `currentJobId` 只在左右两栏流转，中栏没有共享同一 Job 上下文
- 多条样例视频场景下，前端点击选择不会影响后端参考分析目标，后端仍固定取第一个 `is_reference=True` 视频

这次变更需要把“接口已存在”提升为“前端完整可用”，并尽量复用现有 Redis 共享记忆、SSE Hook、Agent 编排与上传接口。

## Goals / Non-Goals

**Goals:**
- 让用户可以在单一前端界面内完成 Job 首次创建与后续多轮追问
- 让整页围绕同一个 `currentJobId` 工作并自动建立 SSE 连接
- 让中栏基于后端真实数据渲染，而不是本地 mock
- 让编排任务上传资源具备稳定的访问 URL，支持预览和播放
- 让多样例场景下的参考分析目标由用户显式选中的视频决定
- 保持现有 Agent 编排、Redis 共享记忆和 `re-submit` 机制不被重写

**Non-Goals:**
- 不重写任何既有 Agent 分析逻辑
- 不替换现有 SSE 为 WebSocket 或第三方实时协议
- 不在本次变更中完成所有时间线高级编辑能力
- 不引入新的外部存储系统替换当前本地上传目录

## Decisions

1. **采用“首条消息触发建任务，后续消息触发 re-submit”的统一交互**
   - 选择：右侧消息区保留为统一入口，但在没有 `currentJobId` 时走 `POST /api/orchestration/jobs`，已有 `currentJobId` 时走 `POST /api/orchestration/jobs/{job_id}/re-submit`
   - 原因：用户心智最简单，避免在 UI 上人为拆分“先建任务再聊天”两段流程
   - 备选方案：额外新增独立“开始生成”按钮作为唯一入口
   - 不选原因：会与现有消息区形成双入口，增加前端状态协调复杂度

2. **将待上传文件缓存于前端页面状态，首次建任务时批量提交**
   - 选择：样例视频和素材视频在没有 Job 前先保留在前端本地状态，首次发送消息时与 `intent` 一起提交到 `POST /jobs`
   - 原因：后端 `create_job` 当前要求一次性接收文件数组，这种方式最兼容现有接口
   - 备选方案：先匿名上传文件，再在创建 Job 时引用临时文件 ID
   - 不选原因：需要新增临时资源生命周期管理和清理策略，超出本次范围

3. **把 `currentJobId` 提升为工作台顶层共享状态，并向中栏下发**
   - 选择：继续由 `App.tsx` 维护 `currentJobId`，但同时把它传给中栏及其子组件
   - 原因：当前结构已具备顶层状态入口，扩展成本最低
   - 备选方案：引入全局 store
   - 不选原因：当前问题是闭环缺失，不是状态工具不足

4. **中栏以“读取共享记忆快照 + 消费 SSE 增量事件”的方式渲染**
   - 选择：切换 Job 或首轮创建成功后，通过现有 Job 状态接口拉取共享记忆快照建立初始视图；随后依赖 SSE 事件触发重新取数或局部更新
   - 原因：避免让每个事件承载全部渲染数据，保持事件流轻量
   - 备选方案：让 `step_write` 直接携带完整渲染模型
   - 不选原因：会放大事件 payload，耦合 Agent 输出格式和前端展示格式

5. **为编排上传资源新增稳定的 GET 文件交付路由**
   - 选择：在 orchestration 路由下提供与上传目录对应的只读文件访问端点，并让前端统一使用该 URL
   - 原因：当前前端已在消费 `/api/orchestration/uploads/...` 形式 URL，补齐服务端实现可最小改动打通链路
   - 备选方案：改为返回外部对象存储 URL
   - 不选原因：当前项目未引入对象存储，不适合本次扩张

6. **将样例视频选中态作为显式共享记忆输入传给后端**
   - 选择：前端维护 `selectedReferenceVideoId`，在创建 Job 或后续请求解析时把它写入共享记忆 `inputs.selected_reference_video_id`，`ReferenceAnalyzerAgent` 优先按该 ID 查找目标视频
   - 原因：只有把“选中了哪条样例视频”变成后端可消费的状态，才能真正控制参考分析目标
   - 备选方案：仍按 `uploaded_videos` 中第一个参考视频作为主样例
   - 不选原因：与用户点击选择的直觉冲突，且无法支持多样例切换分析

## Risks / Trade-offs

- [Risk] 首次创建 Job 需要同时提交多文件，失败时用户体验不清晰 → Mitigation：前端对建任务失败提供明确错误提示，并保留本地待上传文件状态以便重试
- [Risk] 中栏依赖共享记忆结构，若 Agent 输出字段不稳定会影响渲染 → Mitigation：前端先按“最小稳定字段”渲染，并对缺失字段使用空态处理
- [Risk] 继续沿用现有 `create_job` 多文件接口会让首发入口实现稍重 → Mitigation：先以兼容当前接口为目标，后续若需要再抽象上传事务
- [Risk] 文件访问端点若缺少路径校验存在安全隐患 → Mitigation：服务端仅允许读取编排上传根目录内的已知文件名
- [Risk] 用户选中的样例视频被删除或失效后，参考分析目标可能悬空 → Mitigation：后端在找不到 `selected_reference_video_id` 时回退到第一个参考视频，并由前端清空失效选中态

## Migration Plan

1. 先补齐前端 Job 创建入口和顶层 `currentJobId` 共享
2. 再接入编排上传文件访问路由，确保左栏和中栏预览可用
3. 再逐步替换中栏 mock 为共享记忆驱动渲染
4. 保留现有 Swagger 流程和 `re-submit` 接口作为回退路径

## Open Questions

- 首次创建 Job 时，右侧消息区是否还需要显式“未创建任务”空态提示
- 中栏真实渲染第一阶段是否只覆盖核心字段，还是一次性覆盖完整卡片内容
- 是否需要在前端持久化最近一次 `currentJobId`，支持刷新后恢复当前任务
