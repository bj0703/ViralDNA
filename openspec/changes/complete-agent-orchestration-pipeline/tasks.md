## 1. 基础Agent抽象层

- [x] 1.1 创建 BaseAgent 抽象基类，统一定义 read_keys / write_keys 属性和 analyze 方法签名
- [x] 1.2 升级 ReferenceAnalyzerAgent 继承 BaseAgent，补全标准接口，按约定定义读写键

## 2. 实现剩余4个真实Agent

- [x] 2.1 实现 AssetIndexerAgent：读取 uploaded_videos（仅素材），输出素材内容类型、标签、可用片段
- [x] 2.2 实现 SlotMatcherAgent：读取 reference_analysis + asset_index，输出素材槽位匹配结果和缺口列表
- [x] 2.3 实现 GapResolverAgent：读取 slot_matches，基于6级优先级策略补齐所有素材缺口
- [x] 2.4 实现 EditPlannerAgent：读取所有前置输出，生成最终可编辑剪辑时间线
- [x] 2.5 在 prompts 目录补充 4 个新 Agent 对应的系统提示词文件

## 3. 增强 SessionSharedMemory

- [x] 3.1 升级 SessionSharedMemory 数据结构，新增 inputs 嵌套子域
- [x] 3.2 定义 UploadedVideo 数据结构，加入 is_reference 布尔字段标记样例/素材
- [x] 3.3 新增辅助方法 set_input_user_prompt() 和 append_uploaded_video()
- [x] 3.4 实现 get_nested(key_path: str) 工具函数，支持点号分隔的嵌套key路径穿透取值

## 4. 修复拓扑排序算法

- [x] 4.1 升级 _resolve_dependency_order，支持嵌套key路径判断依赖是否满足
- [x] 4.2 当检测到依赖永远无法满足时，抛出明确的 AgentDependencyUnsatisfiedError 异常，不再静默跳过剩余Agent

## 5. 重写 DynamicIntentPlanner

- [x] 5.1 移除原 IntentPlanner 硬编码的幽灵 Agent 列表
- [x] 5.2 基于 user_prompt + 当前共享记忆状态，动态生成下一批要执行的 Agent 列表
- [x] 5.3 支持场景判断：单样例分析 / 全流水线迁移 / 素材仅索引 三种模式

## 6. 修复 WorkflowOrchestrator 执行逻辑

- [x] 6.1 修复 run 方法中 sync 阻塞调用在 async 上下文中的问题，用 asyncio.to_thread 包装
- [x] 6.2 修复 Agent.analyze 调用传参签名，传入完整 shared_memory 对象而非仅零散 job_id 字典
- [x] 6.3 拓扑排序验证：保证所有依赖满足后才开始执行Agent

## 7. 改造 API 支持文件上传和类型标记

- [x] 7.1 更新 orchestration.py 的请求体，从纯文本intent改为multipart/form-data
- [x] 7.2 新增 files 上传数组，每个文件附带 is_reference 布尔字段
- [x] 7.3 补全样例数量边界校验逻辑：0个样例→跳过ReferenceAnalyzerAgent，≥2个样例→取第一个打warning

## 8. 统一注册与端到端测试

- [x] 8.1 更新 dependencies.py 中 AgentRegistry，完整注册全部5个Agent
- [x] 8.2 冒烟测试验证全流水线从上传→5个Agent顺序执行→全部结果落进共享记忆
