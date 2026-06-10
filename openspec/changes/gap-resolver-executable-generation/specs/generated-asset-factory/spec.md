# Generated Asset Factory Spec

## Requirements
1. 生成素材根目录规范：`data/{job_id}/generated_assets/`，目录自动递归创建
2. 每个新生成素材分配唯一asset_id，格式：`gen_{uuid_hex}`
3. 自动生成标准 asset 结构，字段完全兼容现有 asset_index 数据格式
4. 提供统一的 `generate_unique_asset_path(asset_id, suffix)` 方法，生成绝对路径
5. 提供 `register_new_asset(shared_memory, new_asset)` 方法，自动调用 `shared_memory.append_to_array("asset_index", "assets", new_asset)` 写入共享记忆
6. 无任何外部依赖，完全线程安全

## Acceptance Criteria
- 生成的asset_id全局唯一不重复
- 新asset注册后能在asset_index.assets数组中找到
- 生成路径不会覆盖已有文件
