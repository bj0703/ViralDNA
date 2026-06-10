# Gap Resolver Execution Layer Spec

## Requirements
1. 在原有LLM分析输出resolved_gaps之后，追加后置执行阶段
2. 遍历所有resolved_gaps条目，根据chosen_strategy分发到对应的生成器执行
3. reuse / structure_reorder 策略直接跳过生成，仅引用已有素材
4. text_card / static_graphic / ai_generate 策略自动调用对应的生成器
5. 生成失败时自动降级到text_card策略，保证流水线不中断
6. 执行完成后所有新生成素材已自动写入asset_index
7. 完全向后兼容，不改变任何原有数据结构和接口

## Acceptance Criteria
- 原有分析逻辑输出结果与修改前完全一致
- 所有需要生成的gap条目都成功生成对应视频文件
- 生成的新素材在asset_index中可被后续EditPlanner正常索引和引用
- 生成失败时自动降级，不会抛出异常中断全流程
