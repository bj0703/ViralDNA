# 前后端联调完整运行文档

## 1. 目标

帮助你在本地完整跑通全链路新特性：
1. 启动后端 FastAPI + Redis SSE 事件流服务
2. 启动前端 React 实时工作台
3. 发送自然语言指令，后端 LLM 意图规划动态生成 Agent 执行计划
4. 右侧对话区实时展示动态进度条，节点数量和顺序由后端决定，不是硬编码6个
5. SSE 长连接流式推送事件，增量渲染竖思考链
6. 页面刚打开对话区干净空白，草稿箱手动加载历史
7. 三个 Tab（样例视频/素材视频/结果视频）自动映射 Agent 输出结果展示

当前仓库内样例视频路径：
`D:\ai coding\emo_transfer\样例\抖音2026522-387724.mp4`

## 2. 环境准备

建议在 `Anaconda Prompt` 或 `PowerShell` 中操作：
```powershell
conda activate capcut
cd /d "D:\ai coding\emo_transfer"
```

## 3. 配置环境变量

后端需要以下环境变量，根目录下 `.env` 文件自动读取：
```env
ARK_API_KEY=你的豆包API Key
ARK_ENDPOINT_ID=ep-20260508213828-7ntjl
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
REDIS_URL=redis://localhost:6379/0
```

说明：
- 如果 Redis 未配置或不可用，后端自动降级到本地内存模式，全部功能零中断可用
- 如果 ARK_API_KEY 未配置或 Ark 请求失败，后端自动回退本地 heuristic 分析
- 优先走真实 LLM 意图规划，失败自动兜底规则判断

## 4. 安装依赖

### 4.1 后端依赖
```powershell
pip install -r backend/requirements.txt
```

### 4.2 前端依赖
```powershell
# 确保你现在在项目根目录 D:\ai coding\emo_transfer，不要重复 cd frontend
cd frontend
npm install
# 操作完可以退回到根目录继续其他操作
cd ..
```

TypeScript 编译验证：
```powershell
cd frontend
npx tsc --noEmit
```
输出为空代表编译完全 0 错误。

## 5. 启动后端服务

在项目根目录执行：
```powershell
python scripts/run_backend_with_logs.py
```

后端完整运行日志会自动写入项目根目录 `logs/` 下，例如：
```powershell
logs/backend_20260609_153000.log
```

启动成功后确认可访问：
- Swagger 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`
- SSE 事件流测试：Swagger 里找到 `/api/orchestration/jobs/{job_id}/events/stream` 接口

## 6. 启动前端服务

新开一个终端窗口：
```powershell
conda activate capcut
# 直接用绝对路径进入，避免路径嵌套错误
cd /d "D:\ai coding\emo_transfer\frontend"
npm run dev
```

默认访问地址：`http://127.0.0.1:5173`

前端 Vite 已配置代理自动转发 `/api` 请求到后端 8000 端口，不需要手动填写 API Base URL，也不会有 CORS 跨域问题。

## 7. 核心新特性联调步骤

### 7.1 页面刚打开对话区干净空白
- 访问 `http://127.0.0.1:5173`
- 右侧对话区状态：完全空白，显示提示文字「发送指令开始工作，对话区干净空白」
- 进度条节点数量为 0，没有任何历史对话自动加载
- 右上角状态显示「⚪ 未连接」，选择 Job 后自动变成「🟢 实时连接中」

### 7.2 发送第一条指令「只分析样例」
在右下角输入框输入：
```
只分析样例视频，看脚本结构
```
点击「发送」按钮或按回车：
1. 用户消息气泡立刻出现在对话区（右侧蓝色）
2. 后端收到 re-submit 请求，DynamicIntentPlanner LLM 意图规划生成 selected_agent_names = ["ReferenceAnalyzerAgent"]
3. 后端优先广播 `plan_ready` SSE 事件
4. 前端收到 plan_ready 事件，动态生成只有1个节点的进度条：「参考分析 pending」
5. 紧接着收到 `step_start` 事件，节点变成 running 蓝色呼吸动画
6. Agent 执行完成收到 `step_write` 事件，节点变成 done 黑色打勾
7. 对话区追加 Agent 输出结果卡片

**验证点**：动态进度条只有 1 个节点，不是硬编码6个全部显示！

### 7.3 发送第二条指令「全流程复刻」
在输入框输入：
```
上传了1个样例视频和3个素材视频，全流程复刻生成最终视频
```
点击发送：
1. 后端重新运行意图规划，返回完整6个 Agent 列表
2. 收到新的 `plan_ready` 事件，旧节点清空，动态生成新的6节点完整进度条
3. 依次执行：参考分析 → 资产索引 → 插槽匹配 → 间隙解析 → 编辑规划 → 最终渲染
4. 每个节点按顺序变 running → done，前面连线自动变蓝
5. 增量模式下，已缓存的 Agent 会直接收到 `step_skip` 事件，节点显示灰色 → 箭头，跳过该步直接往下走

### 7.4 草稿箱手动加载历史
- 点击对话区顶部「📋 草稿箱」按钮
- 前端自动拉取该 Job 全部历史事件，从事件流重建当时的动态节点进度条
- 再次点击「收起草稿箱」可以隐藏历史

### 7.5 多浏览器窗口实时同步
- 打开两个浏览器窗口同时访问同一个 Job
- 在窗口A发送指令，动态进度条开始运行
- 窗口B 0.5秒内自动同步看到完全一样的动态节点流转画面
- 不需要任何刷新，SSE 广播多用户秒级同步

### 7.6 三个 Tab 内容自动填充
- Agent 全部执行完后，顶部 WorkbenchTabNavigation 三个 Tab 自动点亮
- 「样例视频」Tab：自动展示 ReferenceAnalyzerAgent 输出的脚本分段、节奏曲线、字幕包装、转场规则所有卡片
- 「素材视频」Tab：自动展示 AssetIndexerAgent 输出的素材卡片网格、质量评分条、标签云
- 「结果视频」Tab：自动展示 SlotMatcher + EditPlanner 输出的槽位匹配结果、缺口明细、完整多轨时间线、剪辑校验报告

## 8. SSE 事件流参考完整事件列表

| SSE Event Type | 前端行为 |
|---|---|
| `plan_ready` | 清空旧节点，用 payload.selected_agent_names 动态生成全新 agentNodes 列表 |
| `step_start` | 对应 agent_name 的节点状态置为 running，蓝色呼吸动画 |
| `step_write` | 追加 Agent 结果消息卡片到对话区，节点状态置为 done 黑色打勾 |
| `step_skip` | 节点状态置为 skipped 灰色 → 箭头，代表增量模式跳过（结果已缓存） |
| `step_fail` | 节点状态置为 error 红色叉号，展示错误信息 |
| `resource_updated` | 左侧边栏视频资源列表自动刷新同步 |
| `timeline_segment_updated` | 中间时间线片段更新，多窗口实时同步 |

## 9. 降级策略验证

### 9.1 SSE 断网场景
- 开发者工具网络面板切换到 Offline，观察 SSE 重连
- 连续3次重连失败后，自动切换到 1.5s 轮询兜底
- 网络恢复后自动重新建立 SSE 长连接，停止轮询，零人工介入

### 9.2 Redis 不可用场景
- 关闭本地 Redis 服务，后端自动检测到 Redis 连接失败
- 无缝降级到本地内存模式，所有接口完全正常工作
- 前端用户感知不到任何中断，全流程继续运行

## 10. 接口文档参考

Swagger 完整接口文档：`http://127.0.0.1:8000/docs`

核心新接口：
- `POST /api/orchestration/jobs` - 创建新 Job
- `POST /api/orchestration/jobs/{job_id}/upload-video` - 上传视频（is_reference=true/false）
- `POST /api/orchestration/jobs/{job_id}/re-submit` - 提交新的自然语言指令
- `GET /api/orchestration/jobs/{job_id}/events/stream` - SSE 长连接事件流
- `GET /api/orchestration/jobs/{job_id}/events` - 拉取历史事件列表（草稿箱用）
- `PATCH /api/orchestration/jobs/{job_id}/timeline/segments/{segment_id}` - 编辑时间线片段

## 11. 常见问题排查

### Q: TypeScript 编译有错误？
运行：
```powershell
cd frontend
npx tsc --noEmit
```
看具体报错信息，所有类型定义都集中在 `frontend/src/types/index.ts`。

### Q: SSE 连接失败？
优先确认后端 8000 端口启动正常，Vite 代理配置正确（查看 `frontend/vite.config.ts` 里 `/api` 代理到 `http://127.0.0.1:8000`）。

### Q: 动态进度条显示节点数量不对？
打开浏览器 Console 看 `[SSE Event] 收到事件:` 日志，确认 plan_ready 事件里的 selected_agent_names 数组内容，是后端 LLM 意图规划返回的真实结果。

### Q: 想直接看后端事件流？
用 Swagger 打开 `/api/orchestration/jobs/{job_id}/events/stream` 直接订阅，手动发送 re-submit 请求，能实时看到每一个事件推出来。
