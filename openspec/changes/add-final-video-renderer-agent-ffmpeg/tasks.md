## 1. FFmpeg 工具层实现

- [ ] 1.1 创建 backend/app/utils/ffmpeg_renderer.py
- [ ] 1.2 实现 detect_ffmpeg_path() 自动检测系统 FFmpeg 位置
- [ ] 1.3 实现 build_filter_graph() 从 edit_timeline 构建 filter_complex 滤镜图
- [ ] 1.4 实现 render_timeline_to_video() 执行 subprocess 调用 FFmpeg

## 2. 新增 FinalVideoRendererAgent

- [ ] 2.1 创建 backend/app/agents/final_video_renderer.py
- [ ] 2.2 继承 BaseAgent，read_keys = ["edit_timeline", "inputs.uploaded_videos"]，write_keys = ["final_video_meta"]
- [ ] 2.3 实现 detect_ffmpeg_path 不存在时返回友好降级提示

## 3. 注册与集成

- [ ] 3.1 在 dependencies.py 实例化 FinalVideoRendererAgent
- [ ] 3.2 把 FinalVideoRendererAgent 注册到 AgentRegistry
- [ ] 3.3 在 DynamicIntentPlanner 中识别用户"生成视频"语义自动追加到执行计划尾部

## 4. 验证测试

- [ ] 4.1 语法检查全部通过
- [ ] 4.2 简单时间线样例渲染冒烟测试
