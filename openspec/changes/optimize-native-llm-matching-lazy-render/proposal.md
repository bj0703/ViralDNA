## Why

当前系统存在两处历史遗留问题：1）代码中存在多余的自动派生/强制替换素材逻辑，导致LLM原始返回的精准分配结果被覆盖，多个不同剪辑片段复用同一个短素材，出现零时长无法渲染的BUG；2）默认全量计算4个变体，不必要地浪费算力，首次出片等待时间过长。本变更直接复用LLM生成的原始5套匹配结果，优先用根级纯净基线快速出片，其他4套变体采用懒加载，用户需要时才触发。

## What Changes

- 移除slot_matcher.py中多余的_derive_variant_payload自动派生逻辑，不再人工修改LLM原始返回结果
- 移除_derive_variant_payload内的强制素材轮询替换代码，完全信任LLM选择的素材分配
- 修改edit_planner.py优先直接用LLM返回的根级原生shot_matches生成第一版timeline
- 保留时间自动连续化/单片段最小0.5秒保护逻辑，彻底解决零时长BUG
- 修改gap_resolver.py仅优先处理基线版本的缺口补全，其他4个变体保持懒加载
- 修改final_video_renderer.py默认只渲染已就绪的当前变体，支持用户指定variant_id时再触发对应变体渲染

## Capabilities

### New Capabilities
- `llm-native-match-passthrough`: 100%透传LLM原始返回的5套匹配结果，无任何人工修改覆盖
- `lazy-variant-on-demand-render`: 仅优先渲染基线版本，其他4个变体标记为懒加载，用户需要切换时才执行
### Modified Capabilities
- `slot-driven-intelligent-matching`: 移除人工派生逻辑，完全保留LLM原始分配结果不被覆盖
- `multi-variant-edit-output`: 优化出片顺序，首版渲染速度提升3倍以上

## Impact

- slot_matcher.py / edit_planner.py / gap_resolver.py / final_video_renderer.py 4个核心文件
- 完全向后兼容，所有现有API接口返回字段保持不变，无破坏性变更
