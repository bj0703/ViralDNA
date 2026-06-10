# Text Card Generator Spec

## Requirements
1. 完全基于FFmpeg drawtext滤镜实现，不引入PIL/Pillow等额外图片依赖
2. 支持自定义参数：文字内容、背景色、文字颜色、字体大小、时长（0.5-3秒）、分辨率
3. 默认输出 1080x1920 竖屏9:16比例，与项目主流视频格式完全对齐
4. 支持简单的渐变背景，支持居中粗体文字
5. 生成完成后自动调用GeneratedAssetFactory注册新素材到共享记忆

## Acceptance Criteria
- 生成的视频文件能正常播放
- 文字清晰居中显示
- 时长与指定值误差不超过0.1秒
- 自动追加到asset_index.assets
