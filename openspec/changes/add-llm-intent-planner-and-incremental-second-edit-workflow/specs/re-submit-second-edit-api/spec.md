# Re-Submit Second Edit API Specification

## Summary
二次提交API接口，用户在已有Job基础上提交新需求，快速生成第2版及后续迭代视频。

## Requirements
- 新增 POST /api/orchestration/jobs/{job_id}/re-submit 端点
- 请求Body字段：{ new_user_prompt: str, force_run_agent_names?: [], added_assets?: [] }
- 执行流程：自动打当前状态快照 → LLM增量意图规划 → 推导最小Agent子集 → 增量执行 → 快速产出下一版视频
- 返回新版job状态和version号，用户立即可以看到新结果
- 完全向后兼容，旧的create_job接口不受任何影响
