# Week 8 Day 55 排查案例

## 今天目标

用 trace 和 guardrails 练习排查 5 类 Agent/RAG 常见问题：

1. 检索不到资料
2. 工具调用报错
3. 模型返回格式不符合预期
4. 回答缺少引用来源
5. 请求超时或响应过慢

## 排查入口

用户从前端提问后，请求进入：

```txt
frontend/src/App.jsx
-> POST /api/chat
-> app/api/chat.py
-> app/services/chat.py
-> app/services/llm.py 或 app/services/agent.py
-> app/services/trace.py 写入 trace
-> GET /api/traces/{run_id} 查看步骤
```

## Case 1：检索不到资料

现象：工具或检索流程执行成功，但返回 0 条资料。

判断方法：

```txt
status = success
tool_name = retrieve_documents
output.count = 0
```

说明：这不是程序崩溃，而是知识库没有命中。下一步应该检查文档是否上传、chunk 是否存在、query 是否太偏、相似度阈值是否过严。

## Case 2：工具调用报错

现象：工具没有真正执行成功，trace 中出现 failed。

判断方法：

```txt
status = failed
output.error 有错误原因
input.arguments 是当时传给工具的参数
```

说明：先看参数是否合法，再看工具权限和数据库数据是否存在。

## Case 3：模型格式错

现象：模型应该返回结构化工具决策，但返回了自然语言或缺字段 JSON。

判断方法：

```txt
type = tool_decision
status = failed
output.error 说明格式问题
```

说明：这类问题通常要靠更明确的 prompt、Pydantic 校验或重试机制解决。

## Case 4：回答缺少引用来源

现象：模型给了确定性回答，但 sources 为空。

判断方法：

```txt
output guardrail allowed = false
risk_level = high
reasons 包含没有引用来源
```

说明：RAG 项目里，确定性回答必须能追溯来源。没有来源时应该拒答或要求重新生成。

## Case 5：请求超时或响应过慢

现象：接口没有报错，但用户体感很慢。

判断方法：

```txt
查看每一步 latency_ms
平均响应时间看 /api/traces/stats
最慢步骤通常是 LLM、embedding 或数据库检索
```

说明：trace 的价值是把“感觉很慢”拆成“哪一步慢”。

## 如果只记住一句话

排查 Agent 问题时，不要先猜模型错了；先拿 run_id 看 trace，确认问题发生在检索、工具、模型、输出检查还是耗时。
