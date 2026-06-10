## 0. 兼容性修复（前置必做）

- [x] 0.1 修复FinalVideoRendererAgent：从asset_index.assets额外收集生成素材的storage_path，合并到source_paths
- [x] 0.2 修复AssetIndexerAgent：执行前备份已有aigc_generated素材，执行完成后自动合并回新结果，永不覆盖生成素材
- [x] 0.3 修复ffmpeg_timeline.py：扩展asset_id直接映射机制，支持gen_<uuid>格式的生成素材asset_id快速索引

## 1. Generated Asset Factory 基础实现

- [x] 1.1 创建 `backend/app/providers/generated_asset_factory.py` 模块
- [x] 1.2 实现唯一asset_id生成方法，gen_前缀+uuid
- [x] 1.3 实现生成目录自动创建，路径规范 `data/{job_id}/generated_assets/`
- [x] 1.4 实现 register_new_asset 方法，自动写入 shared_memory.asset_index.assets
- [ ] 1.5 编写单元测试验证工厂基础功能

## 2. Text Card Generator 文字卡片生成器

- [x] 2.1 实现基于FFmpeg drawtext的文字卡片生成方法
- [x] 2.2 支持自定义参数：文字内容、背景色、文字颜色、字号、时长
- [x] 2.3 默认输出1080x1920 9:16竖屏格式
- [x] 2.4 生成完成后自动注册到共享记忆
- [ ] 2.5 编写测试脚本验证生成的文字卡片可正常播放

## 3. Ken Burns Generator 视差动效生成器

- [x] 3.1 实现基于FFmpeg zoompan滤镜的Ken Burns动效方法
- [x] 3.2 支持zoom_in/zoom_out运动方向参数
- [x] 3.3 支持自定义时长1-3秒
- [x] 3.4 生成完成后自动注册到共享记忆
- [ ] 3.5 编写测试脚本验证动效流畅无卡顿

## 4. GapResolver 后置执行层集成

- [ ] 4.1 在 GapResolverAgent 的 analyze 方法中导入 GeneratedAssetFactory
- [ ] 4.2 在LLM分析输出resolved_gaps之后，新增执行循环遍历所有需要生成的gap
- [ ] 4.3 根据chosen_strategy分发到对应的生成器
- [ ] 4.4 实现生成失败自动降级到text_card策略，确保不中断流水线
- [ ] 4.5 执行完成后所有新生成素材自动在asset_index中可被索引
- [ ] 4.6 编写完整端到端测试，构造空素材库场景验证整套生成流程

## 5. 全流程回归验证

- [ ] 5.1 验证原有6个Agent全流程仍然正常运行
- [ ] 5.2 验证不触发任何生成场景下结果完全不变
- [ ] 5.3 运行现有test_full_pipeline.py确认无回归
