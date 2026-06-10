# LLM Driven Intent Planning Specification

## Summary
LLM智能意图规划，基于用户输入自然语言指令和当前系统状态，自动动态生成最优Agent执行计划，完全替代旧版硬编码关键词匹配。

## Requirements
- 内置专用System Prompt，将当前Agent注册表声明、系统状态上下文全部注入传给LLM
- LLM返回严格JSON结构化输出：{ selected_agent_names[], skip_reasons{}, confidence }
- 结果经过白名单校验，只允许AgentRegistry中已注册的Agent名称通过
- 置信度低于0.6时，自动静默回退到原有规则判断逻辑
- LLM调用失败/异常时，自动降级到旧规则，绝不中断主流程
