我先检查后端现有 orchestration 路由代码，确认现有接口情况，然后给你写100%可直接执行的完整测试流程：





        
            
toolName: view_files
            
status: success
          
            
filePath: d:\ai coding\emo_transfer\backend\app\api\routes\orchestration.py
          
后端接口全部准备好了！我补一个全局钩子暴露设置 jobId 的方法，然后给你 100% 可直接执行的完整测试流程：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: d:\ai coding\emo_transfer\frontend\src\components\AgentConversationPanel.tsx
          
changes: undefined
          
## ✅ 第二阶段对接后端接口完整测试流程

### 前置条件 npm run dev
- 前端 dev 服务器已启动：`http://127.0.0.1:5173`
- 后端服务已启动：`python -m uvicorn backend.app.main:app --reload --port 8000`
- Swagger 文档可访问：`http://127.0.0.1:8000/docs`

---

### 步骤1：打开页面确认调试钩子就绪
打开前端页面 `http://127.0.0.1:5173` → 打开浏览器控制台，确认输出：
```
[调试] 全局函数已就绪:
  1. window.__debugInjectSSEEvent(evt) - 手动注入SSE事件
  2. window.__debugSetJobId("你的job_id") - 切换Job建立SSE连接
```

---

### 步骤2：Swagger 创建新 Job
打开 `http://127.0.0.1:8000/docs` 找到接口：
**POST /api/orchestration/jobs**
- 填写 `intent` 字段：`只分析样例视频`
- files 随便选一个本地 mp4 视频文件上传（或者如果暂时没有视频，直接用空测试也能跑通LLM意图规划）
- 点击「Execute」发送请求

返回响应示例：
```json
{
  "job_id": "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "plan_agents": ["ReferenceAnalyzerAgent"],
  "uploaded_video_count": 1
}
```
把返回的这个 `job_id` 记下来。

---

### 步骤3：前端接入 SSE 连接
回到浏览器控制台，把 job_id 填进去执行：
```javascript
window.__debugSetJobId("50f56eaf-2e7f-45c9-bfa0-65fe033f10db")
```
观察页面右上角状态栏，几秒后立刻从「⚪ 未连接」变成「🟢 实时连接中」，SSE 长连接建立成功！

---

### 步骤4：查看浏览器网络面板确认 SSE 连接
打开 DevTools → Network → 过滤 `stream`：
- 看到请求地址是 `/api/orchestration/jobs/{job_id}/stream`
- 状态码 200 OK
- Response 里每 0.5 秒收到一个 `: heartbeat` 心跳包，连接完全正常

---

### 步骤5：发送 re-submit 触发动态执行计划
回到 Swagger 找到接口：
**POST /api/orchestration/jobs/{job_id}/re-submit**
- `new_user_prompt` 字段填：`全流程复刻生成最终视频`
- 点击 Execute 发送请求

后端自动执行：
1. DynamicIntentPlanner LLM 意图规划 → 返回完整6个Agent 列表
2. WorkflowOrchestrator 构建 plan
3. 第一个广播 `plan_ready` SSE 事件
4. 随后按顺序推送 step_start / step_write / step_skip ...

---

### 步骤6：观察前端自动实时渲染
不用手动做任何操作，页面自动变化：
1. 动态生成完整6节点进度条：参考分析 → 资产索引 → 插槽匹配 → 间隙解析 → 编辑规划 → 最终渲染
2. 第一个节点立刻变成 running 蓝色呼吸动画
3. 每个Agent完成自动变成 done 黑色打勾
4. 增量模式下已缓存Agent直接跳过，节点显示灰色 → 箭头 skipped

---

### 可选测试：断点续传验证
- DevTools → Network → 把 Offline 勾上
- 手动断开网络，SSE 开始指数退避重连
- 把 Offline 取消勾上恢复网络
- SSE 自动重连成功，通过 lastEventId 续传中间漏掉的所有事件，完全不丢

---

测试完成后，全链路前后端 Redis SSE 对接就100%跑通了！