## Why

当前 5 个Agent流水线跑完最后产出的 edit_timeline 纯数据结构，没有对应的最终视频生成能力。用户想要从时间线到实际可播放 mp4 一键全自动输出，不需要手动打开任何剪辑GUI（剪映/CapCut），也不需要调用外部云端渲染API。完全本地、零外部依赖、全自动后台渲染。

## What Changes

- 新增第6个Agent `FinalVideoRendererAgent`，read_keys=["edit_timeline", "inputs.uploaded_videos"], write_keys=["final_video_meta"]
- 新增 FFmpeg 渲染引擎，自动从 edit_timeline 生成复杂的 filter_complex 滤镜图命令行，subprocess 调用 FFmpeg 输出最终 .mp4
- 完全不需要打开任何GUI，完全不需要 VectCutAPI 手动打开剪映，全程自动化后台运行
- 渲染产物输出目录：`backend/data/outputs/{job_id}/final_rendered.mp4`
- 完全向后兼容：不影响前面5个Agent流水线，用户不需要渲染时完全可以不用第6个Agent

## Capabilities

### New Capabilities
- `final-video-renderer-ffmpeg`: 纯本地 FFmpeg 自动渲染最终视频，零GUI，零外部依赖

### Modified Capabilities
- `orchestration`: 新增 FinalVideoRendererAgent 注册

## Impact

新增文件：
- backend/app/agents/final_video_renderer.py
- backend/app/utils/ffmpeg_renderer.py
修改文件：
- backend/app/dependencies.py 新增 FinalVideoRendererAgent 注册
- backend/app/services/intent_planner.py 识别用户"生成视频"意图自动追加 FinalVideoRendererAgent 到执行计划
