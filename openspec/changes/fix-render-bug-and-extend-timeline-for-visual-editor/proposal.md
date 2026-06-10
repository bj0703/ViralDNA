## Why

当前流水线存在致命Bug：FFmpeg渲染层字段名不匹配导致所有生成的视频都在重复剪辑参考样例视频，没有真正使用素材。同时为了给后续前端可视化剪辑轨道界面预留完整的数据基础，需要在不破坏现有架构的前提下扩展timeline数据模型。

## What Changes

- 修复FFmpeg渲染层字段名不一致Bug，兼容asset和asset_id两个字段
- 从FFmpeg渲染源路径池中过滤掉参考样例视频，确保素材不会和样例混用
- 新增Timeline预校验层，在渲染前验证所有片段引用的素材真实存在
- 扩展edit_timeline数据结构，增加完整多轨道定义（tracks数组）
- 在片段级别新增asset_full_path、timeline_start_px、timeline_end_px等预留字段
- 新增TimelineEditor中间层服务，提供原子编辑API
- 完全向后兼容：保留原有扁平timeline数组字段作为兼容别名，不破坏现有逻辑

## Capabilities

### New Capabilities
- `timeline-visualization-data-model`: 扩展后的带多轨道和可视化预留字段的时间线数据模型规范
- `timeline-editor-service`: Timeline Editor中间层原子编辑服务API，支持拖拽、裁剪、重排序等操作
- `timeline-validation-layer`: Timeline前置校验层，渲染前验证所有素材引用的合法性

### Modified Capabilities
- `ffmpeg-final-renderer`: 修改FFmpeg最终渲染器，修复字段名Bug，排除参考样例视频，增加预校验

## Impact

- `backend/app/renderers/ffmpeg_timeline.py` - 修改渲染逻辑和字段兼容
- `backend/app/agents/final_video_renderer.py` - 过滤参考视频，增加校验逻辑
- `backend/app/agents/edit_planner.py` - 输出扩展后的多轨道timeline结构
- `backend/app/services/timeline_editor.py` - 新增中间层服务文件
- `backend/app/api/routes/orchestration.py` - 扩展增加timeline编辑API端点
