# Analysis Workbench Frontend

独立前端位于 `frontend/`，与 FastAPI 后端分开运行，技术栈为 React + TypeScript + Vite。

## 启动方式

1. 安装依赖

```powershell
cd "D:\ai coding\emo_transfer\frontend"
npm install
```

2. 启动开发服务器

```powershell
npm run dev
```

默认地址：

- `http://127.0.0.1:5173`

## 后端联调

先启动后端：

```powershell
cd "D:\ai coding\emo_transfer"
python -m uvicorn backend.app.main:app --reload
```

前端默认通过 Vite 代理把以下请求转发到 `http://127.0.0.1:8000`：

- `/sample-analysis/*`
- `/health`
- `/capabilities`

如果后续把前端部署到独立域名，可以在 `frontend/.env` 中设置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 当前能力

- 独立三栏工作台布局
- 左侧上传视频并创建分析任务
- 输入已有 `job_id` 加载后端结果
- 左侧视频列表与中间播放器联动
- 播放器下方脚本/节奏时间轴
- 时间轴点击跳转与播放时高亮
- 右侧自然语言输入和快捷分析按钮
- 右侧概览、脚本、节奏、风险、原始结果切换

## 已知说明

- 当前自然语言区域接入的是 `POST /sample-analysis/intent`，用于意图识别与分析范围路由展示。
- 真正的视频分析任务仍由 `POST /sample-analysis/jobs` 触发。
- 如果前后端使用不同域名直连，后端还需要补充 CORS 配置。
