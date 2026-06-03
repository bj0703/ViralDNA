# 运行说明

## 1. 进入环境

在 Anaconda Prompt 或 PowerShell 中执行：

```powershell
conda activate capcut
cd /d "D:\ai coding\emo_transfer"
```

## 2. 检查 `.env`

项目当前只使用这三个环境变量：

```env
ARK_API_KEY=你的豆包 API Key
ARK_ENDPOINT_ID=ep-20260508213828-7ntjl
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
```

项目根目录下的 `.env` 已经会被后端自动读取，不需要再手动 `set` 环境变量。

## 3. 安装依赖

第一次运行时执行：

```powershell
pip install -r requirements.txt
```

如果 `uvicorn` 命令不可用，后面统一改用：

```powershell
python -m uvicorn backend.app.main:app --reload
```

## 4. 启动后端

运行：

```powershell
uvicorn backend.app.main:app --reload
```

启动成功后访问：

- Swagger 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`
- 能力列表：`http://127.0.0.1:8000/capabilities`

## 5. 推荐联调顺序

### 5.1 测试意图识别

在 Swagger 中使用：

- `POST /sample-analysis/intent`

请求体示例：

```json
{
  "user_input": "请帮我分析这个视频的节奏",
  "target_video_id": "sample-1"
}
```

### 5.2 上传并分析真实样例视频

在 Swagger 中使用：

- `POST /sample-analysis/jobs`

上传这个文件：

`D:\ai coding\emo_transfer\样例\抖音2026522-387724.mp4`

表单可填写：

- `session_name`: `real-sample-test`
- `notes_json`:

```json
{
  "抖音2026522-387724.mp4": "请分析这个真实样例视频的脚本结构、节奏结构、包装与声音，并输出迁移建议。"
}
```

接口会返回：

- `job_id`
- `session_id`
- `status`
- `sample_count`

### 5.3 查询任务状态

在 Swagger 中使用：

- `GET /sample-analysis/jobs/{job_id}/status`

### 5.4 查看标准化结果

在 Swagger 中使用：

- `GET /sample-analysis/jobs/{job_id}/result`

### 5.5 查看前端展示模型

在 Swagger 中使用：

- `GET /sample-analysis/jobs/{job_id}/view-model`

这里返回的是后续三栏工作台最直接会消费的结构，重点看：

- `timeline`
- `panels.overview`
- `panels.script`
- `panels.pace`
- `panels.packaging_and_sound`
- `panels.migration_suggestion`

### 5.6 查看 HTML 结果页

浏览器打开：

```text
http://127.0.0.1:8000/sample-analysis/jobs/<job_id>/view
```

## 6. 纯脚本验证

### 6.1 验证基础样例分析链路

```powershell
python scripts/verify_sample_analysis.py
```

这个脚本只验证当前样例分析 service 的基本结果，不启动网页服务。

### 6.2 验证 ReferenceAnalyzerAgent

```powershell
python scripts/verify_reference_analyzer.py
```

这个脚本会：

- 用真实样例视频跑一遍 `heuristic`
- 再跑一遍 `ReferenceAnalyzerAgent`
- 输出两者对比结果

如果你想确认“当前到底有没有真的调用豆包”，优先看这个脚本的输出。

## 7. 当前状态说明

目前后端已经具备：

- 样例分析 API
- 意图识别 API
- `view-model` 聚合结果
- `ReferenceAnalyzerAgent`
- `heuristic fallback`

当前三栏前端工作台还在实现中，所以现在最稳的使用入口仍然是：

- Swagger：`/docs`
- HTML 结果页：`/sample-analysis/jobs/<job_id>/view`

## 8. 常见问题

### 缺少 `fastapi`

执行：

```powershell
pip install -r requirements.txt
```

### `uvicorn` 无法识别

执行：

```powershell
python -m uvicorn backend.app.main:app --reload
```

### 页面打不开

确认访问的是：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

而不是其他端口。

### 想确认是否真的调用了豆包

运行：

```powershell
python scripts/verify_reference_analyzer.py
```

如果输出里出现：

- `provider: "reference-analyzer-agent"`

说明当前已经进入 agent 分析链路，而不是只走 heuristic。
