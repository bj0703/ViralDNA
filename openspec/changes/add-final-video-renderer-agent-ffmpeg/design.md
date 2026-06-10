## Context

现有5Agent流水线最后产出edit_timeline纯数据结构，没有实际视频渲染能力。用户不想手动打开剪映GUI，也不想调用外部云端渲染API，要求全本地零依赖全自动输出最终mp4。

## Goals / Non-Goals

**Goals:**
- 完全自动化后台渲染，不需要人干预
- 零外部GUI依赖，不需要打开剪映/CapCut
- 零外部网络API依赖，完全本地运行
- 支持时间线里的基础操作：片段裁切、变速、9:16画面居中裁剪、简单字幕叠加

**Non-Goals:**
- 不实现复杂关键帧动画（第一版先不做）
- 不对接VectCutAPI的HTTP服务
- 不要求用户安装剪映软件

## Decisions

| Decision | 选项A (选择) | 选项B (弃选) | Rationale |
|---|---|---|---|
| 渲染引擎 | FFmpeg subprocess 直接调用filter_complex | MoviePy 上层封装 | MoviePy内部也只是包装了FFmpeg，直接调用原生FFmpeg性能最高，中间少一层不必要的封装 |
| 并发模型 | 同步阻塞 subprocess.run | asyncio.create_subprocess_exec | 渲染过程本来就是CPU密集型阻塞操作，同步代码最简单最稳定 |
| 输出分辨率 | 强制竖屏1080x1920 9:16 | 跟源视频保持同分辨率 | 短视频场景9:16是主流，所有素材统一竖屏更实用 |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| FFmpeg 没有在系统PATH里找不到 | 增加配置项允许用户自定义ffmpeg_path，找不到ffmpeg时直接返回友好提示，不抛出崩溃 |
| 渲染大视频耗时较长 | 把状态实时写入shared_memory的event_log，记录渲染进度百分比 |

## Implementation Pitfalls（融合现有代码必须注意的关键坑）

### 项目现有代码结构融合冲突点
| Pitfall | 现状 | 解决方案 |
|---|---|---|
| 项目没有 utils/ 目录 | 现有目录结构中完全没有 backend/app/utils/ 文件夹，但是已经存在 backend/app/renderers/ 目录 | 不要新建多余的 utils 目录，直接把 FFmpeg 渲染模块放在现有 renderers/ 目录下，命名为 ffmpeg_timeline.py，和已有的 sample_analysis.py 放在一起，完全保持项目现有结构风格一致 |
| DynamicIntentPlanner 没有生成视频逻辑 | 现有代码完全没有任何识别"生成视频"语义的逻辑 | 新增关键词检测：关键词列表包含 ["生成视频", "输出视频", "渲染视频", "导出视频", "final video", "render"]，只在用户明确说了生成视频时，才在 EditPlannerAgent 后面追加 FinalVideoRendererAgent，绝对不能默认强制追加，避免不必要的慢操作 |
| config.py 缺少 ffmpeg_path 配置 | 现有 core/config.py 里完全没有 FFmpeg 路径配置项 | 新增可选配置，ffmpeg_path 默认值为 None，自动检测系统 PATH 里的 ffmpeg 可执行文件，找不到时返回友好降级提示 |
| backend/data/outputs 目录完全不存在 | 项目现有目录结构里没有 outputs 子目录 | 代码里必须使用 Path.mkdir(parents=True, exist_ok=True) 自动递归创建完整输出目录，绝对不要假设目录已经存在 |
| 现有 renderers/sample_analysis.py 是 HTML 渲染 | 现有 renderers 目录下只用来生成样例分析 HTML 报告，完全没有任何视频渲染相关逻辑 | 零冲突，我们直接在同目录下新增 ffmpeg_timeline.py 完全不影响现有 HTML 渲染功能 |

### FFmpeg 渲染底层实现坑
| Pitfall | 解决方案 |
|---|---|
| filter_complex 滤镜图字符串写起来很复杂容易出错 | 先构建分段的输入链，每个片段单独标记标签名，最后用 + 拼接，不要手工硬写一长串 |
| 多个输入视频流时间戳错位 | 用 -avoid_negative_ts make_zero 参数强制重置所有时间戳从0开始 |

## Migration Plan

1. 新增 ffmpeg_timeline.py 渲染模块放在 renderers/ 目录下
2. 新增 FinalVideoRendererAgent
3. 注册Agent到AgentRegistry
4. 更新 DynamicIntentPlanner 识别生成视频意图自动追加第6个Agent
5. 全向后兼容，无需修改之前5个Agent代码
