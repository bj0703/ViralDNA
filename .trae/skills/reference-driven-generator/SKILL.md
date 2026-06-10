---
name: "reference-driven-generator"
description: "参考驱动AIGC素材生成器，基于参考视频片段/关键帧图片生成新的图片或短视频素材。Invoke when GapResolverAgent选中ai_generate策略需要生成补充素材，或者用户明确要求生成AIGC补充片段。"
---

# Reference-Driven Generator 参考驱动AIGC素材生成器

## 功能概述
基于参考样例的视频片段或关键帧图片，生成语义对齐的图片/短视频补充素材，自动写入共享工作记忆的asset_index，下游EditPlanner可直接引用生成的新asset_id。

## 核心能力
1. **参考片段提取**：从指定源视频时间区间自动抽帧提取关键帧图片
2. **语义理解**：调用LLM分析参考帧画面内容，生成精准的AIGC Prompt
3. **多类型生成**：
   - 图片生成：生成与参考帧风格/语义一致的高清图片
   - 短视频生成：生成1-3秒匹配参考画面动态逻辑的短视频片段
4. **自动入库**：生成完成后自动追加到共享记忆的asset_index.assets数组

## 调用流程
```
输入:  gap_resolved_item (包含 slot_id, chosen_strategy, 参考片段引用)
  ↓
1. 从源视频提取指定time_in→time_out区间的关键帧
  ↓
2. LLM分析关键帧画面，生成优化后的AIGC Prompt
  ↓
3. 调用配置的文生图/文生视频API（支持Pika/Runway/Sora兼容接口）
  ↓
4. 下载生成的媒体文件到 data/{job_id}/generated_assets/ 目录
  ↓
5. 分配唯一asset_id，自动追加写入 shared_memory.append_to_array("asset_index", "assets", new_generated_asset)
  ↓
输出: new_generated_asset (包含完整路径、标签、时长信息)
```

## 数据结构规范
```python
new_generated_asset = {
    "asset_id": "gen_<uuid>",
    "source_type": "aigc_generated",  # 标记是AI生成素材
    "content_type": "video/mp4",      # 或 "image/png"
    "storage_path": "data/xxx/generated_assets/gen_xxx.mp4",
    "duration_seconds": 2.0,
    "tags": ["aigc", slot_id, "generated", semantic_tags...],
    "reference_source": {
        "original_asset_id": original_ref_asset_id,
        "time_in": 12.5,
        "time_out": 14.5
    }
}
```

## 配置要求
环境变量可选：
- `AIGC_IMAGE_API_KEY` - 文生图API密钥
- `AIGC_VIDEO_API_KEY` - 文生视频API密钥
- `AIGC_VIDEO_ENDPOINT` - 文生视频兼容接口地址

API未配置时自动静默回退到 text_card 策略，不破坏现有流水线。
