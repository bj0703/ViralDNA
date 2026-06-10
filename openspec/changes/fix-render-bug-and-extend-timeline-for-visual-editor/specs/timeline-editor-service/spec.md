# Timeline Editor Service Specification

## Summary
Timeline Editor中间层服务，提供原子操作API，封装所有对时间线的安全编辑操作，供后续前端剪辑UI直接调用。

## Requirements
- 服务模块路径：`backend/app/services/timeline_editor.py`
- 提供以下原子操作方法：
  - `get_full_timeline(job_id)`: 返回完整带tracks结构的时间线
  - `update_segment(job_id, segment_id, patch_data)`: 更新单个片段属性
  - `insert_new_segment(job_id, track_id, insert_position, segment_data)`: 从素材库拖入新片段
  - `delete_segment(job_id, segment_id)`: 删除指定片段
  - `reorder_segments(job_id, track_id, new_order_ids)`: 拖拽重新排序片段
  - `re_render(job_id)`: 触发FFmpeg重新渲染出片
- 所有操作必须内置合法性校验：时长不越界、引用素材必须真实存在、时间区间不能重叠
- 每次变更自动追加事件日志到shared_memory的event_log
- 提供对应的FastAPI路由端点，暴露为HTTP API
