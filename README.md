# ViralDNA - 面向短视频创作的爆款结构迁移平台

ViralDNA 是一个面向短视频创作的 AI 创作平台。项目希望通过 AI 对优质样例视频进行拆解，提取其中可复用的脚本结构、镜头节奏、字幕包装、音乐卡点、卖点推进和结尾表达方式，并将这些“爆款结构基因”迁移到新的主题、商品信息或用户素材中，辅助创作者生成新的短视频方案。
相比于直接复制样例视频内容，ViralDNA 更强调对创作方法的迁移，即学习样例视频背后的结构逻辑，并根据用户提供的新素材进行适配、补全与重组，从而形成具有相似表达效果但内容不同的新视频方案。

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [环境准备](#环境准备)
- [环境变量配置](#环境变量配置)
- [安装依赖](#安装依赖)
- [Redis 启动](#redis-启动)
- [启动后端服务](#启动后端服务)
- [启动前端服务](#启动前端服务)
- [完整使用流程](#完整使用流程)
- [核心新特性说明](#核心新特性说明)
- [SSE 事件流参考](#sse-事件流参考)
- [降级策略](#降级策略)
- [接口文档](#接口文档)
- [常见问题排查](#常见问题排查)

---

## 项目简介

ViralDNA 是一个 AI 驱动的视频情感转移工作台，用户通过自然语言指令，系统自动规划 Agent 执行流程，完成从样例视频分析到素材匹配、编辑规划、最终渲染的全链路自动化。

## 核心特性

- 🧠 **LLM 意图规划**：自然语言指令 → 动态生成 Agent 执行计划，节点数量和顺序由后端决定
- 📡 **SSE 实时事件流**：长连接流式推送，增量渲染竖思考链，多窗口实时同步
- 📊 **动态进度条**：根据 `plan_ready` 事件动态生成节点，非硬编码固定数量
- 🎬 **三 Tab 自动映射**：样例视频 / 素材视频 / 结果视频 Tab 自动填充 Agent 输出
- 📋 **草稿箱手动加载**：对话区初始干净空白，手动点击加载历史事件
- 🔄 **智能降级策略**：Redis 不可用自动降级内存模式，LLM 失败回退 heuristic 分析

## 技术栈

### 后端
- **FastAPI** - Web 框架
- **Redis** - 事件流存储与广播（可选，支持降级）
- **Pydantic** - 数据校验
- **Uvicorn** - ASGI 服务器

### 前端
- **React 19** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具与开发服务器
- **Server-Sent Events (SSE)** - 实时事件流

## 项目结构

```
emo_transfer/
├── backend/                    # 后端 FastAPI 服务
│   ├── app/
│   │   ├── agents/            # Agent 实现（6+ 个核心 Agent）
│   │   ├── api/               # API 路由定义
│   │   ├── core/              # 核心配置与共享内存
│   │   ├── services/          # 业务服务（意图规划、时间线编辑等）
│   │   ├── providers/         # LLM 提供商与 heuristic 分析
│   │   └── main.py            # FastAPI 入口
│   ├── requirements.txt       # Python 依赖
│   └── scripts/               # 后端启动脚本
├── frontend/                   # 前端 React 工作台
│   ├── src/
│   │   ├── components/        # UI 组件
│   │   ├── hooks/             # SSE 连接等自定义 Hook
│   │   ├── layouts/           # 布局组件
│   │   └── types/             # TypeScript 类型定义
│   ├── package.json           # Node 依赖
│   └── vite.config.ts         # Vite 配置（含 /api 代理）
├── scripts/                    # 项目根目录脚本
│   └── run_backend_with_logs.py  # 后端启动（带日志写入）
├── knowledge_base/             # 知识库配置
├── .env.example               # 环境变量模板
├── AGENTS.md                  # Agent 执行规则
└── 文档/
    └── RUN.md                 # 详细运行文档
```

## 环境准备

建议使用 **Anaconda** 管理 Python 环境，**Node.js 18+** 运行前端。

### Windows 推荐操作

打开 **Anaconda Prompt** 或 **PowerShell**：

```powershell
conda create -n capcut python=3.11 -y
conda activate capcut
cd <项目目录>
```

### Node.js 检查

```powershell
node --version
npm --version
```

确保 Node.js >= 18。

## 环境变量配置

在项目根目录创建 `.env` 文件，复制 `.env.example` 的内容并填入你的配置：

```env
# 豆包 ARK API 配置
ARK_API_KEY=your_ark_api_key_here
ARK_ENDPOINT_ID=ep-20260508213828-7ntjl
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions

# Redis 配置（可选，设置为 disabled 即关闭 Redis，自动降级回内存模式）
REDIS_URL=redis://localhost:6379/0
```

### 降级说明

- **Redis 不可用**：后端自动检测，无缝降级到本地内存模式，所有接口正常工作
- **ARK API Key 缺失或请求失败**：后端自动回退本地 heuristic 分析，优先走真实 LLM，失败兜底规则判断


## Docker 一键部署（推荐）

如果你已经安装了 Docker 和 Docker Compose，可以跳过以上所有步骤，一键启动整个环境：

### 1. 构建并启动

```powershell
# 进入项目根目录
cd <项目目录>

# 设置 API Key（或在 .env 文件中配置）
$env:ARK_API_KEY="你的豆包API_Key"

# 第一次启动会构建镜像（可能需要 5-10 分钟）
docker-compose up --build -d
```

### 2. 日常使用

```powershell
# 启动（已构建过，几秒即可完成）
docker-compose up -d

# 查看实时日志
docker-compose logs -f app

# 停止
docker-compose down

# 重启
docker-compose restart
```


## 安装依赖

### 1. 后端依赖

```powershell
cd <项目目录>
pip install -r backend/requirements.txt
```

### 2. 前端依赖

```powershell
cd frontend
npm install
```

### （可选）TypeScript 编译验证

```powershell
cd frontend
npx tsc --noEmit
```

输出为空代表编译完全 0 错误。

## Redis 启动

> Redis 是**可选**依赖，不启动也可运行（自动降级到内存模式）。

### 使用 Docker 启动 Redis

在项目根目录执行：

```powershell
docker run -d --name viraldna-redis -p 6379:6379 redis:7-alpine
```

如果本地已经有同名容器，可先启动已有容器：

```powershell
docker start viraldna-redis
```

### 验证 Redis 连接

```powershell
redis-cli ping
# 返回 PONG 表示连接正常
```

> 如果 Redis 不可用，无需任何操作，后端启动时会自动检测并降级到内存模式。

## 启动后端服务

在项目根目录执行（**建议新开一个终端窗口**）：

```powershell
conda activate capcut
cd <项目目录>
python scripts/run_backend_with_logs.py
```

### 后端启动后验证

启动成功后确认可访问：

| 功能 | 地址 |
|------|------|
| Swagger API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |
| SSE 事件流测试 | 在 Swagger 中找到 `/api/orchestration/jobs/{job_id}/events/stream` 接口 |

后端完整运行日志会自动写入项目根目录 `logs/` 下，例如：

```
logs/backend_20260609_153000.log
```

## 启动前端服务

**新开另一个终端窗口**：

```powershell
conda activate capcut
cd <项目目录>
cd frontend
npm run dev
```

### 前端访问地址

默认访问：**http://127.0.0.1:5173**

> 前端 Vite 已配置代理，自动转发 `/api` 请求到后端 `http://127.0.0.1:8000`，不需要手动填写 API Base URL，也不会有 CORS 跨域问题。

## 完整使用流程

### 1. 页面初始状态

- 访问 `http://127.0.0.1:5173`
- 右侧对话区：完全空白，显示提示文字「发送指令开始工作，对话区干净空白」
- 进度条节点数量：0
- 右上角状态：「⚪ 未连接」，选择 Job 后自动变成「🟢 实时连接中」

### 2. 发送第一条指令「只分析样例」

在右下角输入框输入：

```
只分析样例视频，看脚本结构
```

点击「发送」按钮或按回车：

1. 用户消息气泡立刻出现在对话区（右侧蓝色）
2. 后端收到 re-submit 请求，DynamicIntentPlanner LLM 意图规划生成 `selected_agent_names = ["ReferenceAnalyzerAgent"]`
3. 后端优先广播 `plan_ready` SSE 事件
4. 前端收到 `plan_ready` 事件，**动态生成只有 1 个节点的进度条**：「参考分析 pending」
5. 紧接着收到 `step_start` 事件，节点变成 running 蓝色呼吸动画
6. Agent 执行完成收到 `step_write` 事件，节点变成 done 黑色打勾
7. 对话区追加 Agent 输出结果卡片

**验证点**：动态进度条只有 1 个节点，**不是硬编码 6 个全部显示**！

### 3. 发送第二条指令「全流程复刻」

在输入框输入：

```
上传了1个样例视频和3个素材视频，全流程复刻生成最终视频
```

点击发送：

1. 后端重新运行意图规划，返回完整 6 个 Agent 列表
2. 收到新的 `plan_ready` 事件，旧节点清空，**动态生成新的 6 节点完整进度条**
3. 依次执行：参考分析 → 资产索引 → 插槽匹配 → 间隙解析 → 编辑规划 → 最终渲染
4. 每个节点按顺序变 running → done，前面连线自动变蓝
5. 增量模式下，已缓存的 Agent 会直接收到 `step_skip` 事件，节点显示灰色 → 箭头，跳过该步

### 4. 草稿箱手动加载历史

- 点击对话区顶部「📋 草稿箱」按钮
- 前端自动拉取该 Job 全部历史事件，从事件流重建当时的动态节点进度条
- 再次点击「收起草稿箱」可以隐藏历史

### 5. 多浏览器窗口实时同步

- 打开两个浏览器窗口同时访问同一个 Job
- 在窗口 A 发送指令，动态进度条开始运行
- 窗口 B 0.5 秒内自动同步看到完全一样的动态节点流转画面
- 不需要任何刷新，SSE 广播多用户秒级同步

### 6. 三个 Tab 内容自动填充

Agent 全部执行完后，顶部 WorkbenchTabNavigation 三个 Tab 自动点亮：

| Tab | 展示内容 |
|-----|---------|
| **样例视频** | ReferenceAnalyzerAgent 输出的脚本分段、节奏曲线、字幕包装、转场规则 |
| **素材视频** | AssetIndexerAgent 输出的素材卡片网格、质量评分条、标签云 |
| **结果视频** | SlotMatcher + EditPlanner 输出的槽位匹配结果、缺口明细、完整多轨时间线、剪辑校验报告 |

---

## 核心新特性说明

1. **动态进度条**：节点数量完全由后端 LLM 意图规划决定，前端收到 `plan_ready.selected_agent_names` 后动态渲染
2. **SSE 长连接**：`/api/orchestration/jobs/{job_id}/events/stream` 提供持久连接，增量推送事件
3. **对话区干净空白**：页面打开不自动加载任何历史，手动通过「草稿箱」加载
4. **增量渲染思考链**：每个 Agent 输出通过 `step_write` 事件增量追加到对话区

## SSE 事件流参考

| SSE Event Type | 前端行为 |
|----------------|---------|
| `plan_ready` | 清空旧节点，用 `payload.selected_agent_names` 动态生成全新 agentNodes 列表 |
| `step_start` | 对应 agent_name 的节点状态置为 running，蓝色呼吸动画 |
| `step_write` | 追加 Agent 结果消息卡片到对话区，节点状态置为 done 黑色打勾 |
| `step_skip` | 节点状态置为 skipped 灰色 → 箭头，代表增量模式跳过（结果已缓存） |
| `step_fail` | 节点状态置为 error 红色叉号，展示错误信息 |
| `resource_updated` | 左侧边栏视频资源列表自动刷新同步 |
| `timeline_segment_updated` | 中间时间线片段更新，多窗口实时同步 |

## 降级策略

### Redis 不可用场景

- 关闭本地 Redis 服务，后端自动检测到 Redis 连接失败
- 无缝降级到本地内存模式，所有接口完全正常工作
- 前端用户感知不到任何中断，全流程继续运行

### SSE 断网场景

- 开发者工具网络面板切换到 Offline，观察 SSE 重连
- 连续 3 次重连失败后，自动切换到 1.5s 轮询兜底
- 网络恢复后自动重新建立 SSE 长连接，停止轮询，零人工介入

## 接口文档

启动后端后访问 Swagger 完整文档：**http://127.0.0.1:8000/docs**

### 核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/orchestration/jobs` | 创建新 Job |
| POST | `/api/orchestration/jobs/{job_id}/upload-video` | 上传视频（is_reference=true/false） |
| POST | `/api/orchestration/jobs/{job_id}/re-submit` | 提交新的自然语言指令 |
| GET | `/api/orchestration/jobs/{job_id}/events/stream` | SSE 长连接事件流 |
| GET | `/api/orchestration/jobs/{job_id}/events` | 拉取历史事件列表（草稿箱用） |
| PATCH | `/api/orchestration/jobs/{job_id}/timeline/segments/{segment_id}` | 编辑时间线片段 |

