## 1. 修复致命渲染Bug

- [x] 1.1 修改 ffmpeg_timeline.py 中的 build_filter_graph，同时兼容 asset 和 asset_id 两个字段
- [x] 1.2 修改 FinalVideoRendererAgent，过滤 source_paths，排除 is_reference=True 的参考样例视频
- [x] 1.3 移除静默回退到索引0的逻辑，找不到匹配时抛出明确警告

## 2. 实现 Timeline 前置校验层

- [x] 2.1 在 ffmpeg_timeline.py 中新增独立的 validate_timeline 函数
- [x] 2.2 校验所有素材引用真实存在，source_in/source_out 时长合法
- [x] 2.3 在 render_timeline_to_video 入口处调用校验层，校验失败直接终止渲染

## 3. 扩展 Timeline 可视化数据模型

- [x] 3.1 修改 EditPlannerAgent 的输出逻辑，新增 tracks 多轨道数组结构
- [x] 3.2 在 segment 中加入 asset_full_path、timeline_start_px、timeline_end_px 预留字段
- [x] 3.3 保留原有扁平 timeline 数组作为向后兼容别名
- [x] 3.4 扩展 timeline_meta，新增 timeline_width_pixels 默认字段

## 4. 实现 Timeline Editor 中间层服务

- [x] 4.1 新建 backend/app/services/timeline_editor.py 模块
- [x] 4.2 实现所有6个原子操作方法（get_full_timeline/update_segment/insert_new_segment/delete_segment/reorder_segments/re_render）
- [x] 4.3 在 orchestration.py 路由中新增对应的 FastAPI HTTP 端点
- [x] 4.4 所有操作变更自动追加事件日志到 shared_memory

## 5. 全链路端到端验证

- [ ] 5.1 运行 test_full_pipeline.py，验证最终产出视频真正使用素材片段而非样例
- [x] 5.2 验证新旧数据结构完全向后兼容
- [x] 5.3 生成完整可视化timeline输出，检查tracks和所有预留字段完整
