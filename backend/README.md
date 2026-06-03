# 样例分析后端

这是 `build-sample-analysis` change 对应的最小后端实现，目标是先打通样例视频输入、结构拆解、结果输出和页面展示闭环。

## 目录结构

- `app/api/routes`：FastAPI 路由
- `app/schemas`：Pydantic API 契约
- `app/services`：业务编排层
- `app/providers`：分析 provider 适配层
- `app/repositories`：内存仓储
- `app/renderers`：分析结果 HTML 渲染

## 主要接口

- `POST /sample-analysis/jobs`
- `GET /sample-analysis/jobs/{job_id}`
- `GET /sample-analysis/jobs/{job_id}/result`
- `GET /sample-analysis/jobs/{job_id}/view-model`
- `GET /sample-analysis/jobs/{job_id}/view`
- `POST /sample-analysis/intent`
- `GET /health`
- `GET /capabilities`

## 当前实现说明

- 当前样例分析默认优先走 `ReferenceAnalyzerAgent`，并在失败或未配置时回退到本地启发式分析器。
- 当前自然语言意图识别支持受控意图集合，并优先尝试通过 Ark `chat/completions` 接口识别；当配置不可用或请求失败时，回退到本地规则匹配。
- 当前 Ark 调用配置严格只使用 `ARK_API_KEY`、`ARK_ENDPOINT_ID` 和 `ARK_BASE_URL` 三个环境变量。
- 如果本机安装了 `ffprobe`，系统会优先读取真实视频时长；否则会根据文件大小估算时长。
- 字幕或语音概览支持通过 `notes_json` 传入，未传入时会根据文件名做弱推断。
- 结果页同时显示人类可读摘要和机器可读 JSON，方便后续结构迁移流程复用。
- `ReferenceAnalyzerAgent` 使用固定系统 prompt，对输出做 JSON 提取、轻量修复和字段补全，再映射到后端标准结构。

## 已知限制

- 当前任务和结果仅保存在内存中，服务重启后会丢失。
- 当前 `ReferenceAnalyzerAgent` 仍基于 `chat/completions` 文本接口和视频上下文推断，不是直接的视频像素流上传理解。
- 当 Ark 调用失败或返回不稳定 JSON 时，会回退到 heuristic 结果，因此 agent 质量仍受底层调用形态限制。
- 当前仅提供样例视频分析闭环，结构迁移、素材缺口识别和补全接口仍是预留状态。

## ReferenceAnalyzerAgent 验证结论

- 真实样例视频可通过 `scripts/verify_reference_analyzer.py` 验证 agent 与 heuristic 的输出差异。
- 相比 heuristic，agent 能输出更丰富的包装、声音和迁移建议信息。
- 已知风险：当前 agent 的“视频理解”依赖文本上下文与启发式基线，并不等同于真正的多模态视频像素分析，因此后续仍建议升级底层 provider。

## 启动方式

安装依赖后可运行：

```bash
uvicorn backend.app.main:app --reload
```

建议依赖：

- `fastapi`
- `uvicorn`
- `python-multipart`
- `pydantic`
