# 本地开发启动检查清单

## 快速开始顺序

```
环境检查 → 后端依赖安装 → 冒烟测试 → 启动后端 → 启动前端 → 全流程验证
```

---

## 📋 Step 1: 环境预检查 (必做)

### 1.1 Python 环境检查
```powershell
python --version
# 预期输出 Python 3.9+
```

### 1.2 项目根目录检查
```powershell
cd d:\ai coding\emo_transfer
ls
# 必须看到: backend/, frontend/,样例/, scripts/, requirements.txt, RUN.md, .env
```

### 1.3 .env 配置检查
确认根目录 .env 文件包含:
```
ARK_API_KEY=xxx
ARK_ENDPOINT_ID=ep-20260508213828-7ntjl
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
```

---

## 📦 Step 2: 后端依赖安装

```powershell
pip install -r requirements.txt
```

### 验证关键依赖已安装
```powershell
pip list | findstr fastapi
pip list | findstr uvicorn
pip list | findstr volcenginesdkarkruntime
```

---

## 🧪 Step 3: 自动化冒烟测试 (启动前必跑)

```powershell
# 1. 旧有参考分析器验证
python scripts/verify_sample_analysis.py
python scripts/verify_reference_analyzer.py

# 2. 新增编排器冒烟测试
python scripts/test_orchestration_smoke.py
```

✅ **全部通过后再启动服务**

---

## 🚀 Step 4: 启动后端服务

新开终端 A:
```powershell
conda activate capcut  # (如果用了conda)
uvicorn backend.app.main:app --reload
```

等待看到:
```
Uvicorn running on http://127.0.0.1:8000
```

### 后端健康检查 (浏览器或新终端)
| 地址 | 预期结果 |
|------|---------|
| http://127.0.0.1:8000/health | 返回 `{"status":"ok"}` |
| http://127.0.0.1:8000/docs | Swagger 文档页面可打开，能看到 orchestration 接口 |
| http://127.0.0.1:8000/capabilities | 返回系统能力列表 |

---

## 🎨 Step 5: 启动前端服务

新开终端 B:
```powershell
cd frontend
npm install  # 首次运行执行，后续可跳过
npm run dev
```

等待看到:
```
Vite v5.x.x ready in xxx ms
➜ Local: http://127.0.0.1:5173/
```

### 前端检查
- 浏览器打开 http://127.0.0.1:5173
- 不要手动填写 API Base URL (保持空，走 Vite 代理)

---

## ✅ Step 6: 完整全流程验证清单

按顺序逐个验证，全部打勾表示启动完全成功：

| 验证项 | 操作方式 | 预期结果 | 状态 |
|--------|---------|---------|------|
| 基础样例分析 | 上传 样例/抖音2026522-387724.mp4 | 生成分析结果，能看到时间轴 | ☐ |
| 编排器API测试1 | Swagger 调用 `POST /api/orchestration/jobs` 用默认 intent | 成功返回 job_id | ☐ |
| 编排器API测试2 | 调用 `GET /api/orchestration/jobs/{job_id}` | 能看到 overall_status 和 step_states | ☐ |
| 事件轨迹查看 | 调用 `GET /api/orchestration/jobs/{job_id}/trace` | 能看到 event_log 数组 | ☐ |
| 前后端联动 | 前端完整上传分析 | 播放器、时间轴、分析面板全部联动 | ☐ |

---

## 🚨 常见问题快速修复

| 现象 | 修复方案 |
|------|---------|
| 冒烟测试 import 报错 | 确认你在项目根目录 `d:\ai coding\emo_transfer` 下运行 |
| 端口 8000 被占用 | `netstat -ano \| findstr :8000` 杀进程，或改用 `--port 8001` |
| 前端 Vite 代理失败 | 确认后端确实在 8000 运行，不要改前端里的 API Base URL |
| 豆包 API 返回错误 | 自动回退到 heuristic 本地分析模式，不阻塞联调 |
