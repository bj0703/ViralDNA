# Timeline Validation Layer Specification

## Summary
Timeline前置校验层，在FFmpeg渲染入口前集中验证所有片段引用的合法性，消除静默失败隐患。

## Requirements
- 新增独立函数`validate_timeline(timeline_segments, asset_paths_list)`
- 校验项包括：
  1. 每个segment引用的asset_id必须真实存在于素材路径池中
  2. source_in >= 0 且 source_out > source_in 且 source_out <= 素材总时长
  3. 时间线上segment的timeline_start < timeline_end
  4. 没有重叠冲突（相邻片段end和下一个start允许精确相等）
- 任意校验失败必须抛出明确的异常信息，不得静默回退到索引0
- 生成详细的validation_report，列出所有警告和错误项
- 校验不通过时，终止渲染流程，返回结构化错误给调用方
