## 1. SlotMatcher 精简优化

- [ ] 1.1 删除 _derive_variant_payload 手动派生函数
- [ ] 1.2 删除强制素材轮询替换逻辑，完全保留LLM原始选择的素材分配
- [ ] 1.3 简化 _attach_variant_views，直接透传 LLM 返回的4个变体结果

## 2. EditPlanner 优化

- [ ] 2.1 直接优先使用根级原生 shot_matches 生成第一版 timeline
- [ ] 2.2 保留已实现的时间自动连续化逻辑，前一个片段 end 自动作为下一个片段 start
- [ ] 2.3 保留单片段最小 0.5 秒保护，彻底消灭零时长
- [ ] 2.4 4个非基础版本体标记为 _lazy=True，不预先计算

## 3. GapResolver 简化

- [ ] 3.1 简化为仅处理当前激活的基础版本缺口补全
- [ ] 3.2 其他4个变体保持懒加载占位，不占用算力

## 4. FinalVideoRenderer 适配

- [ ] 4.1 默认仅渲染已就绪的基础版本，快速出片
- [ ] 4.2 当用户指定 requested_variant_id 时，单独渲染对应变体
- [ ] 4.3 全流程验证所有功能正常，端到端跑出最终成片
