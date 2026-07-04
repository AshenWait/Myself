# 3-5 分钟 Demo 演示脚本（Day 77）

这个脚本用于录制 Knowledge Agent 的项目 demo。目标不是把所有接口讲完，而是在 3-5 分钟内证明项目具备完整 RAG + Agent 工程能力：文档上传、检索问答、引用来源、工具调用、trace 排查。

## 录制前准备

启动数据库：

```powershell
docker start knowledge-agent-pgvector
docker ps --filter "name=knowledge-agent-pgvector"
```

启动后端：

```powershell
cd C:\Users\yangp\Desktop\knowledge-agent
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
cd C:\Users\yangp\Desktop\knowledge-agent\frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

打开页面：

```txt
http://127.0.0.1:5174/
http://127.0.0.1:8000/docs
```

准备测试文件：

```txt
tests/fixtures/sample.txt
tests/fixtures/sample.pdf
tests/fixtures/sample.md
```

## 3-5 分钟演示顺序

### 0:00 - 0:30 项目开场

画面：README 首页或前端工作台。

讲解词：

```txt
这是一个企业知识库 RAG + Agent 项目。用户上传文档后，系统会解析文本、切分 chunks、生成 embedding 并保存到 PostgreSQL + pgvector。用户提问时，系统会先检索相关文档片段，再调用大模型生成带引用来源的回答。这个 demo 我会演示上传文档、提问、引用来源、Agent 工具权限和 trace 排查。
```

### 0:30 - 1:20 上传文档

画面：前端上传区或 Swagger 的 `POST /api/documents/upload`。

操作：

1. 选择 `tests/fixtures/sample.txt` 上传。
2. 展示上传成功后的文档列表。
3. 如果用 Swagger，展示返回里的 `document_id`、`filename`、`page_count`。

讲解词：

```txt
这里我上传一份测试文档。后端会校验文件类型和大小，保存原始文件，然后解析文本。解析后的文本会继续切分成 chunks，每个 chunk 会保留文档 ID、页码和 chunk_index，后续用于向量检索和引用溯源。
```

### 1:20 - 2:10 展示切分和检索

画面：Swagger。

操作：

1. 调用 `GET /api/documents`，展示文档已经入库。
2. 调用 `GET /api/documents/{document_id}/chunks`，展示 chunk 内容。
3. 调用 `GET /api/documents/search?query=plain text&limit=3`，展示 pgvector 检索结果。

讲解词：

```txt
上传完成后，系统不是直接把整篇文档塞给模型，而是先切成 chunks。每个 chunk 会生成 embedding 并写入 pgvector。提问时，系统会把问题也转成向量，再用向量相似度检索最相关的 chunks，这一步决定了后续回答能不能拿到正确上下文。
```

### 2:10 - 3:00 RAG 问答和引用来源

画面：前端提问区或 Swagger 的 `POST /api/chat`。

操作：

请求示例：

```json
{
  "message": "这个文档是做什么用的？"
}
```

展示重点：

1. `reply`：模型回答。
2. `sources`：引用来源。
3. `sources` 里的文档名、页码、chunk_id、content、distance。
4. `run_id`：后续 trace 查询用。

讲解词：

```txt
这里是 RAG 问答结果。回答不是模型凭空生成的，后端会同时返回 sources。sources 里包含文档名、页码、chunk_id、原文片段和距离分数，所以用户可以追溯这句话来自哪份文档。这里的 run_id 是本次问答的追踪编号，后面可以用它查看完整执行过程。
```

### 3:00 - 3:40 Trace 排查

画面：前端 Trace 面板，或 Swagger 的 `GET /api/traces/{run_id}`。

操作：

1. 复制上一步返回的 `run_id`。
2. 调用 `GET /api/traces/{run_id}`。
3. 展示模型调用、输入输出摘要、耗时、状态。
4. 可选调用 `GET /api/traces/stats` 展示平均响应时间和失败率。

讲解词：

```txt
只看最终回答很难排查问题，所以项目里给每次问答生成 run_id。通过 run_id 可以看到模型调用、工具调用、输出检查等步骤，以及每一步的耗时和状态。如果回答不对，我会先看 trace，判断问题发生在检索、模型、工具、引用检查还是超时。
```

### 3:40 - 4:30 Agent 工具调用和权限控制

画面：终端。

当前项目的 Agent 工具能力在 `AgentService` 中，还没有独立 `/api/agent` 路由，所以 demo 用测试脚本展示工具调用和权限控制。

操作：

```powershell
cd C:\Users\yangp\Desktop\knowledge-agent
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe tests\check_tool_trace.py
.\.venv\Scripts\python.exe tests\check_tool_confirmation.py
```

预期输出：

```txt
Day 52 工具调用 Trace 检查通过。
未确认时，create_note 被正确拦截：
确认后，create_note 通过权限检查。
即使确认，危险工具也被正确拦截：
Day 44 工具确认检查通过。
```

讲解词：

```txt
Agent 部分我实现了工具注册表和权限控制。只读工具可以直接执行，比如 list_documents、retrieve_documents、summarize_document。create_note 会写入数据库，所以必须用户确认；delete_document 属于危险工具，当前不开放。这里的测试展示了工具调用会被 trace 记录，写入工具未确认会被拦截，危险工具即使确认也不能执行。
```

### 4:30 - 5:00 收尾总结

画面：README 的项目难点或简历项目描述。

讲解词：

```txt
这个项目的重点不是简单调用大模型，而是把 RAG 和 Agent 做成可解释、可排查、可评测的工程系统。RAG 部分解决文档检索和引用溯源，Guardrails 解决拒答和工具权限，trace 解决线上排查，评测集解决效果量化。后续还可以继续补 Docker Compose 一键部署、rerank 和更完整的 Agent API。
```

## 录制检查清单

- [ ] 展示 README 首页或前端工作台。
- [ ] 上传测试文档。
- [ ] 展示文档列表或文档入库结果。
- [ ] 展示 chunks 或 pgvector 检索结果。
- [ ] 提问并展示回答。
- [ ] 展示 sources 引用来源。
- [ ] 复制 run_id 并展示 trace。
- [ ] 运行工具调用和权限控制测试脚本。
- [ ] 用 20 秒总结项目价值和后续优化方向。

## 如果录屏时出错

- 后端启动失败：先检查 `.env` 和数据库容器是否运行。
- 上传失败：换用 `tests/fixtures/sample.txt`，它最稳定。
- 回答没有 sources：说明检索没有命中，先换成测试文档里更明确的问题。
- trace 查不到：确认使用的是 `/api/chat` 返回的 `run_id`，不是 `session_id`。
- 工具 demo 报 import 错：确认当前目录是项目根目录，并设置 `$env:PYTHONPATH="."`。
