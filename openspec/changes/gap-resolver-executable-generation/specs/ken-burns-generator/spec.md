# Ken Burns Generator Spec

## Requirements
1. 输入一张静态图片，输出带视差放大运动效果的短视频片段
2. 支持参数：zoom_in/zoom_out运动方向、时长（1-3秒）、运动起点和终点坐标
3. 输出分辨率1080x1920 9:16竖屏
4. 用FFmpeg zoompan滤镜实现，无额外依赖
5. 生成完成后自动注册到共享记忆asset_index

## Acceptance Criteria
- 静态图片成功转换为流畅运动短视频
- 运动效果平滑无卡顿
- 时长符合指定要求
- 自动追加到asset_index.assets
