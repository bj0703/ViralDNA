## 1. Reference Analyzer 升级

- [x] 1.1 更新 backend/app/prompts/reference_analyzer.py 中的system prompt，新增"抽象可迁移创作结构"的核心指令
- [x] 1.2 修改ReferenceAnalyzerAgent实现代码，升级_parse_and_repair和_validate_and_fill逻辑，支持新structural_slots等字段的容错填充
- [x] 1.3 将max_tokens参数调整至3000，temperature保持0.1，保证JSON输出完整度
- [x] 1.4 保留原有script_structure/rhythm_structure/packaging_and_sound所有旧字段，完全向后兼容

## 2. Asset Indexer 升级

- [x] 2.1 更新 backend/app/prompts/asset_indexer.py 中的system prompt，新增"拆解细粒度可剪辑segments"核心指令
- [x] 2.2 修改AssetIndexerAgent的_analyze_single_asset方法，升级LLM调用逻辑以支持新字段解析
- [x] 2.3 max_tokens调整至1200，temperature 0.1
- [x] 2.4 保留原有顶层content_type/tags/visual_description等旧字段，完全向后兼容

## 3. Slot Matcher 完全重写

- [x] 3.1 更新 backend/app/prompts/slot_matcher.py，替换任务描述为"以结构slot为中心为每个槽位选择最合适素材片段"
- [x] 3.2 完全移除原有硬编码循环取模分配逻辑，改为调用LLM执行智能匹配
- [x] 3.3 输出结构包含slot_assignments、unfilled_slots、low_confidence_slots数组
- [x] 3.4 max_tokens设为2000，temperature 0.1
- [x] 3.5 保留旧的matches和gaps字段作为向后兼容别名，防止旧消费者崩溃

## 4. Gap Resolver 完全重写

- [x] 4.1 更新 backend/app/prompts/gap_resolver.py，升级为7级统一优先级策略（新增structure_reorder）
- [x] 4.2 移除原有简单规则判断逻辑，改为调用LLM生成可执行补齐方案
- [x] 4.3 输出resolved_gaps数组，每个项包含chosen_strategy、attempted_strategies、resolution、impact_on_template、requires_human_review等完整字段
- [x] 4.4 max_tokens设为2000，temperature 0.1
- [x] 4.5 保留旧的resolved_gaps基础结构向后兼容

## 5. Edit Planner 升级

- [x] 5.1 更新 backend/app/prompts/edit_planner.py，升级为"生成多轨可执行剪辑方案"核心指令
- [x] 5.2 实现多轨结构生成：视频timeline轨、caption_track字幕轨、packaging_track包装轨、audio_track音频轨
- [x] 5.3 增加cover_design封面设计生成逻辑
- [x] 5.4 增加validation自动校验层，检查所有槽位填充、素材引用、时间线重叠、结构保真度
- [x] 5.5 增加human_review_points人工复核入口输出
- [x] 5.6 max_tokens设为3000，temperature 0.1
- [x] 5.7 保留旧timeline数组字段完全向后兼容

## 6. 整体验证与兼容性检查

- [x] 6.1 Python语法检查全部通过，无编译错误
- [x] 6.2 所有Agent降级fallback逻辑完整，LLM不可用时系统可正常运行
- [x] 6.3 检查所有Agent输出中旧字段完全存在，向后兼容未破坏
- [x] 6.4 新字段structural_slots/segments/slot_assignments/executable_gaps/multi-track timeline完整实现
