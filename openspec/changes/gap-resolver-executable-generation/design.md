## Context

当前 GapResolverAgent 只输出抽象的补齐方案描述字符串，没有实际执行生成能力。7级策略中只有前2级reuse/structure_reorder可以不生成新文件直接工作，其他策略都缺失实际实现，导致素材缺口无法真正解决。项目已有FFmpeg全依赖，直接利用FFmpeg能力生成素材零外部依赖成本最低。

## Goals / Non-Goals

**Goals:**
- 完全落地7级补齐策略中的可执行生成逻辑，生成真实可直接用于后续剪辑的视频片段
- 自动追加生成的新素材到共享记忆的 asset_index，下游EditPlanner零修改直接引用
- 所有生成操作不破坏现有流水线，完全向后兼容
- 优先用FFmpeg内置能力解决90%常见缺口场景，零额外付费依赖

**Non-Goals:**
- 不接入复杂的第三方AIGC视频生成API作为必需依赖
- 不修改现有Agent的任何公开接口
- 不改变现有的resolved_gaps数据结构

## Decisions

1. **新增独立GeneratedAssetFactory工厂类**
   - 替代直接把生成逻辑耦合进GapResolverAgent的方案，所有生成逻辑集中管理，后续扩展方便
   - 理由：生成素材是独立的关注点，工厂类封装后其他Agent也可以复用生成能力

2. **GapResolverAgent分为两个阶段**
   - 阶段1：LLM分析输出抽象补齐方案（保留原有逻辑，完全不动）
   - 阶段2：遍历resolved_gaps，传入GeneratedAssetFactory逐个执行生成
   - 理由：最小侵入原则，原有分析逻辑完全保留，只在后置追加执行层

3. **text_card策略完全用FFmpeg drawtext实现**
   - 不用PIL/Pillow生成图片再转视频，直接一条FFmpeg命令生成完整的视频文件
   - 理由：减少额外依赖，FFmpeg的drawtext滤镜对文字渲染更专业，支持动效

4. **AI生成能力做成优雅降级模式**
   - reference-driven-generator Skill未配置/API Key不存在时，ai_generate策略自动fallback到text_card策略，整个流水线不中断
   - 理由：避免因为外部服务不可用导致全流程崩溃

## Risks / Trade-offs

- [Risk] FFmpeg drawtext滤镜在不同平台的字体路径不一致 → Mitigation 做自动字体探测兜底，优先用系统默认sans-serif字体
- [Risk] 生成的新asset_id和上游生成的asset_id命名冲突 → Mitigation 所有生成素材前缀统一加 gen_ 和 uuid，完全避免冲突
- [Risk] 执行生成操作消耗额外时间 → Mitigation 生成的都是1-3秒超短视频，单文件生成耗时<2秒，对总时长影响可忽略
