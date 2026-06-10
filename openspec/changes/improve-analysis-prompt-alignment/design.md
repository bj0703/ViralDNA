## Context

当前 `ReferenceAnalyzerAgent` 的问题不是“prompt 没写好”，而是底层输入形态不对。代码里现在通过 `ArkChatProvider` 调用 `chat/completions`，发送的是系统提示词和用户提示词字符串；用户提示词里包含文件名、时长、notes 和 heuristic 基线，但没有把视频内容本身提交给模型。

因此，即使 `.env` 中 API key、endpoint 和 base url 都配置正确，当前能力边界依然只是文本推断，而不是真实视频分析。既然这次目标已经明确为“真正调用 API 分析视频”，设计必须围绕“视频如何进入模型”展开，而不是继续围绕 prompt 对齐做局部修补。

## Goals / Non-Goals

**Goals:**
- 让样例分析请求真正把视频内容提交给可用的模型 API。
- 保留结构化 JSON 输出约束，让真实视频分析结果仍能进入现有标准化结果结构。
- 明确区分“真实视频分析失败”和“本地 heuristic 降级”两类情况。
- 让前端和调试接口能够验证本次结果是否真的基于视频输入产生。

**Non-Goals:**
- 不在本次 change 中继续增强纯文本推断质量。
- 不把 heuristic 结果伪装成真实视频分析结果。
- 不在本次 change 中实现完整多 agent 编排系统。

## Decisions

### 1. 真实视频输入是主目标，不再把文本推断视为等价方案

本次 change 的一等目标是调用实际可用的模型 API 分析视频，因此设计上必须满足：

- 模型请求包含真实视频输入
- 视频输入方式与目标 API 的要求一致
- 如果当前 API 形态不支持该输入方式，返回明确错误

这意味着“把文件路径、notes 和 heuristic 摘要发给模型”不再视为成功实现。

### 2. 保留 analysis instruction，但它从属视频分析，不替代视频输入

用户的分析诉求仍然重要，但它的作用是指导模型“重点分析什么”，而不是在没有视频输入时替代视频本身。因此：

- `analysis_instruction` 作为独立字段保留
- 模型请求同时包含视频输入和分析指令
- instruction 只控制分析重点，不改变“必须基于视频内容”的基本要求

### 3. provider 适配层必须显式支持视频上传/视频引用

当前 `ArkChatProvider` 仅封装纯文本 `chat/completions` 请求。本次需要在 provider 层明确支持以下至少一种真实视频输入模式：

- 直接上传视频文件到目标 API
- 向目标 API 提交可访问的视频 URL
- 先上传文件并拿到媒体引用，再以媒体引用发起分析

最终选型由目标 API 实际支持的输入协议决定，但实现层不得继续假设“纯文本消息即可完成视频理解”。

### 4. 真实视频分析失败时返回能力错误，再决定是否允许显式降级

当用户发起的是“真实视频分析”请求时，如果底层 API 不支持当前输入方式、上传失败或返回不支持的视频能力错误，系统应：

- 返回清晰的能力错误或配置错误
- 在结果或任务状态中声明“真实视频分析未执行成功”
- 只有在产品明确允许的前提下，才提供显式的 heuristic 降级入口

也就是说，不能默默把真实视频分析请求替换成文本推断结果。

### 5. provider trace 需要升级为“输入形态可见”

原本的 provider trace 主要描述模型与 fallback 来源。现在需要进一步暴露本次任务的输入形态，至少包括：

- `requested_provider`
- `actual_provider`
- `input_modality`，如 `video`, `video_url`, `text_context_only`
- `used_fallback`
- `fallback_reason`
- `analysis_instruction`
- `known_limitations`

这样用户才能判断“这次到底是不是视频分析”。

## Risks / Trade-offs

- [目标 API 实际不支持当前设想的视频输入] -> 先做 provider 能力探测与显式报错，不继续伪造视频分析结果。
- [视频上传导致请求体变大、耗时增加] -> 在任务状态中展示真实处理阶段，并对超时与失败进行标准化处理。
- [真实视频分析输出不稳定] -> 保留现有 JSON 提取、校验与修复逻辑，但输出来源必须标明是视频分析结果。
- [前端仍沿用旧心智] -> 在工作台中显式展示输入形态与 provider trace。

## Migration Plan

第一步确认目标模型 API 支持的真实视频输入协议，并在 provider 层实现该协议。  
第二步让 `ReferenceAnalyzerAgent` 改为基于真实视频输入发起分析。  
第三步更新结果结构与前端状态展示，明确输入形态与真实分析状态。  
第四步仅在必要时保留显式 heuristic 降级，并把其标记为非等价替代。  

## Open Questions

- 当前 `.env` 指向的 endpoint 是否已经支持视频输入，还是仅支持文本 `chat/completions`？
- 目标 API 接收的是原始视频上传、远程 URL，还是预上传后的媒体引用？
- 如果真实视频分析不可用，产品是否允许用户手动选择“退回文本推断/heuristic”而不是直接报错？
