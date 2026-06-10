# Timeline Visualization Data Model Specification

## Summary
扩展edit_timeline数据结构，增加完整多轨道定义和可视化预留字段，为前端剪辑轨道界面直接提供开箱即用的数据格式。

## Requirements
- 新增顶层`tracks[]`数组，支持多轨道定义（video/audio/text/effect等类型）
- 每个track包含：track_id, track_type, track_name, height_px, locked, segments[]字段
- 每个segment必须新增：asset_full_path, timeline_start_px, timeline_end_px三个预留字段
- 保留原有扁平`timeline[]`数组作为完全向后兼容别名，不得删除
- timeline_meta下新增timeline_width_pixels字段，默认值设为1920（前端画布标准宽度）
- 所有新增字段均为可选，下游未升级时使用默认值即可正常工作
- segment中的source_in/source_out字段含义保持不变：源素材中截取的开始/结束时间（秒）
