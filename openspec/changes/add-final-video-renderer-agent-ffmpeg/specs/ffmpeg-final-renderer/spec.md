## ADDED Requirements

### Requirement: FinalVideoRendererAgent 自动渲染最终视频
FinalVideoRendererAgent SHALL 从共享记忆读取 edit_timeline，用 FFmpeg 自动渲染生成最终可播放 mp4 文件，不需要打开任何GUI，零外部依赖。

#### Scenario: 从 edit_timeline 生成最终视频
- **WHEN** FinalVideoRendererAgent 执行
- **THEN** 系统 SHALL 构建完整的 FFmpeg filter_complex 滤镜图命令行
- **AND** 调用 subprocess 执行 FFmpeg 输出最终视频文件到 backend/data/outputs/{job_id}/final_rendered.mp4

#### Scenario: 输出目录自动创建
- **WHEN** 渲染输出目录不存在
- **THEN** 系统 SHALL 自动递归创建完整目录

#### Scenario: 找不到 FFmpeg 友好提示
- **WHEN** 系统找不到 FFmpeg 可执行文件
- **THEN** 系统 SHALL 返回友好提示，不崩溃抛出异常
