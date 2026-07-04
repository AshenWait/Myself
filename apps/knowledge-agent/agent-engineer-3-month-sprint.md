# Agent 工程师 3 个月冲刺计划

开始日期：待确定
结束日期：待确定（约 91 天）
目标岗位：Agent 工程师、LLM 应用工程师、RAG 工程师、AI 后端工程师

## 核心策略

3 个月内不要做很多分散项目，只做一个能打的主项目：

> 企业知识库 Agent：支持文档上传、RAG 问答、引用溯源、tool calling、权限确认、调用日志、评测集、Docker 部署。

这个项目要证明：

- [ ] 你会 Python 后端开发。
- [ ] 你会接入 LLM API。
- [ ] 你会做 RAG。
- [ ] 你会做 Agent 工具调用。
- [ ] 你知道怎么评估、部署和排查问题。

## 数据库选择

你的电脑没有安装 MySQL，所以 3 个月冲刺版切换为 PostgreSQL。

推荐组合：

- [ ] PostgreSQL：保存用户、文档元数据、chunk 元数据、会话、消息、调用日志、评测结果。
- [ ] pgvector：后续保存 embedding 向量并做相似度检索。
- [ ] 本地文件夹：保存上传的 PDF、txt、markdown 原文件。

选择 PostgreSQL 的原因：它既能做成熟的关系型数据库，也能通过 pgvector 扩展支持向量检索。这样 RAG 项目后期可以少维护一个独立向量库，项目结构更接近真实工程。

## 最终交付物

- [ ] GitHub 主项目仓库：`knowledge-agent`。
- [ ] 本地 Docker 一键启动版本。
- [ ] 一个可演示的前端页面。
- [ ] 完整 README。
- [ ] 项目架构图。
- [ ] 3-5 分钟 demo 视频或演示脚本。
- [ ] 50 条问题的 RAG/Agent 评测集。
- [ ] 一版可以投递的简历。

## 技术栈

- [ ] 后端：Python + FastAPI。
- [ ] 业务数据库：PostgreSQL。
- [ ] 向量检索：pgvector。
- [ ] ORM：SQLAlchemy。
- [ ] 数据迁移：Alembic，可选。
- [ ] 文档解析：PyMuPDF 或 pypdf。
- [ ] LLM：OpenAI、Claude、通义、智谱、DeepSeek 任选一个稳定可用的。
- [ ] 前端：React 或极简 HTML。
- [ ] 部署：Docker + docker compose。

## 每天时间安排

最低版本，每天 2.5 小时：

- [ ] 30 分钟：学当天要用的知识。
- [ ] 100 分钟：写项目代码。
- [ ] 20 分钟：调试和记录问题。

如果当天只有 1 小时，只推进项目代码，不看长视频。

## 第 1 周：项目启动和 FastAPI 最小后端

目标：项目能启动，有基础 API，有 PostgreSQL 连接。

### Day 1

- [x] 建 GitHub 远程仓库：`knowledge-agent`。
- [x] 初始化本地 Git 仓库：`knowledge-agent`。
- [x] 初始化 Python 虚拟环境。
- [x] 建目录：`app/api`、`app/core`、`app/models`、`app/services`、`app/schemas`、`tests`。
- [x] 写 README：项目目标、技术栈、最终功能。
- [x] 确认项目能运行。

### Day 2

- [x] 学 FastAPI 路由、请求参数、响应模型。
- [x] 写 `/health` 接口。
- [x] 写 `/api/chat` 空接口。
- [x] 用浏览器或 curl 调通接口。

### Day 3

- [x] 学 Pydantic。
- [x] 定义 `ChatRequest`。
- [x] 定义 `ChatResponse`。
- [x] 定义 `DocumentUploadResponse`。

### Day 4

- [x] 用 SQLAlchemy 连接 PostgreSQL。
- [x] 建表：`documents`、`chunks`、`chat_sessions`、`chat_messages`。
- [x] 写数据库连接配置。
- [x] 保存一条测试消息到 PostgreSQL。

### Day 5

- [x] 写 `ChatService`。
- [x] 写 `DocumentService`。
- [x] 把业务逻辑从 router 拆出去。
- [x] 提交一次 Git commit。

### Day 6

- [x] 接入 LLM API。
- [x] 完成一轮普通聊天。
- [x] 记录模型调用耗时。
- [x] 把用户问题和模型回答保存到 PostgreSQL。

### Day 7

- [x] 写本地运行说明。
- [x] 检查别人是否能按 README 启动项目。
- [x] 复盘 FastAPI、PostgreSQL、LLM 调用卡点。
- [x] 推送 GitHub。

## 第 2 周：文件上传和 PDF 解析

目标：用户能上传文档，系统能解析并入库。

### Day 8

- [x] 实现 PDF 上传接口。
- [x] 限制文件类型。
- [x] 限制文件大小。
- [x] 保存原文件到本地目录。

### Day 9

- [x] 学 PyMuPDF 或 pypdf。
- [x] 抽取 PDF 每页文本。
- [x] 保存页码和文本。
- [x] 处理空页。

### Day 10

- [x] 把文档元数据保存到 PostgreSQL。
- [x] 保存文件名、页数、上传时间、文件路径。
- [x] 写文档入库 service。

### Day 11

- [x] 实现文档列表接口。
- [x] 实现文档详情接口。
- [x] 实现文档删除接口，先只删数据库记录。

### Day 12

- [x] 支持 txt 文件解析。
- [x] 支持 markdown 文件解析。
- [x] 统一不同格式的解析返回结构。

### Day 13

- [x] 处理解析失败。
- [x] 处理空文件。
- [x] 处理扫描版 PDF。
- [x] 给错误返回清晰提示。

### Day 14

- [x] README 增加文档上传和解析说明。
- [x] 准备 3 个测试文档。
- [x] 推送 GitHub。

## 第 3 周：文本切分、Embedding、pgvector 检索

目标：输入问题后，能检索到相关文档片段。

### Day 15

- [x] 学 chunk size 和 overlap。
- [x] 实现固定长度切分。
- [x] 每个 chunk 保存 `document_id`、`page`、`chunk_index`。

### Day 16

- [x] 把 chunk 元数据保存到 PostgreSQL。
- [x] 保存 chunk 原文。
- [x] 写查询某篇文档 chunks 的接口。

### Day 17

- [x] 接入 embedding API。
- [x] 给 chunk 生成 embedding。
- [x] 记录 embedding 模型名称。

### Day 18

- [x] 安装并启用 pgvector。
- [x] 为 chunk 表增加 embedding 字段。
- [x] 把 chunk 文本、metadata、embedding 写入 PostgreSQL。

### Day 19

- [x] 实现 `/api/retrieve` 接口。
- [x] 输入问题，返回 top_k 相关片段。
- [x] 返回来源文档名、页码、chunk_id。

### Day 20

- [x] 用 5 个问题测试检索效果。
- [x] 调整 chunk size。
- [x] 调整 top_k。
- [x] 记录失败案例。

### Day 21

- [x] README 增加 pgvector 检索说明。
- [x] 写一段"为什么 PostgreSQL + pgvector 适合 RAG 项目"的说明。
- [x] 推送 GitHub。

## 第 4 周：RAG 问答和引用溯源

目标：系统能基于文档回答，并显示引用来源。

### Day 22

- [x] 设计 RAG prompt。
- [x] 明确回答规则。
- [x] 明确无法回答时要拒答。
- [x] 明确必须带引用。

### Day 23

- [x] 实现 RAG 链路：问题 -> 检索 -> 拼上下文 -> 调模型。
- [x] 返回最终回答。
- [x] 保存问答记录。

### Day 24

- [x] 给回答增加引用来源。
- [x] 返回文档名、页码、chunk_id。
- [x] 展示引用片段。

### Day 25

- [x] 实现拒答逻辑。
- [x] 检索分数过低时不让模型胡编。
- [x] 记录拒答案例。

### Day 26

- [x] 实现流式输出。
- [x] 前端或 curl 能看到逐步返回。
- [x] 保存完整回答。

### Day 27

- [x] 记录每次 RAG 调用日志。
- [x] 保存问题、检索片段、回答、耗时。
- [x] 支持按会话查看日志。

### Day 28

- [x] 整理 README。
- [x] 录制 2 分钟 RAG demo。
- [x] 推送 GitHub。

## 第 5 周：前端最小可用

目标：可以直接给面试官演示。

### Day 29

- [x] 建一个简单前端。
- [x] 页面包含上传区、文档列表、提问框、回答区。
- [x] 跑通前端开发服务器。

### Day 30

- [x] 接入文档上传接口。
- [x] 页面能上传 PDF。
- [x] 上传后刷新文档列表。

### Day 31

- [x] 接入文档列表接口。
- [x] 页面能显示文件名、页数、上传时间。
- [x] 加空状态。

### Day 32

- [x] 接入问答接口。
- [x] 页面能提问。
- [x] 页面能展示回答。

### Day 33

- [x] 展示引用来源。
- [x] 点击引用能看到 chunk 原文。
- [x] 引用显示文档名和页码。

### Day 34

- [x] 加 loading 状态。
- [x] 加错误提示。
- [x] 加清空输入框。

### Day 35

- [x] 前后端联调。
- [x] README 增加截图。
- [x] 推送 GitHub。

## 第 6 周：Tool Calling 和 Agent 化

目标：从 RAG 问答升级为能调用工具的 Agent。

### Day 36

- [x] 学 tool calling 基本概念。
- [x] 定义工具：`retrieve_documents(query)`。
- [x] 让模型决定是否调用检索工具。

### Day 37

- [x] 定义工具：`summarize_document(document_id)`。
- [x] 支持总结某篇文档。
- [x] 总结结果带引用。

### Day 38

- [x] 定义工具：`list_documents()`。
- [x] Agent 能回答"我上传了哪些文档"。
- [x] 记录工具调用结果。

### Day 39

- [x] 定义工具：`create_note(title, content, source_ids)`。
- [x] 保存笔记到 PostgreSQL。
- [x] 笔记保留来源 chunk。

### Day 40

- [x] 手写简单 agent loop。
- [x] 限制最大工具调用次数为 5。
- [x] 工具失败时给出错误信息。

### Day 41

- [x] 给工具参数加 Pydantic 校验。
- [x] 错误参数不执行工具。
- [x] 保存校验失败日志。

### Day 42

- [x] README 增加 Agent 工具列表。
- [x] 写清楚每个工具的权限等级。
- [x] 推送 GitHub。

## 第 7 周：权限确认和 Guardrails

目标：Agent 有边界，不乱调用工具。

### Day 43

- [x] 给工具分级：只读工具、写入工具、危险工具。
- [x] 写工具权限表。
- [x] 只读工具允许直接执行。

### Day 44

- [x] 写入工具执行前要求用户确认。
- [x] `create_note` 需要确认。
- [x] 删除类操作暂时不开放。

### Day 45

- [x] 实现工具白名单。
- [x] 不同会话只开放必要工具。
- [x] 未开放工具不能执行。

### Day 46

- [x] 加输入检查。
- [x] 拦截明显 prompt injection。
- [x] 记录风险输入。

### Day 47

- [x] 加输出检查。
- [x] 回答没有引用时要求重新生成或拒答。
- [x] 保存输出检查结果。

### Day 48

- [x] 准备 20 条安全测试样例。
- [x] 测试越权、删除、注入、无引用回答。
- [x] 记录通过和失败结果。

### Day 49

- [x] 修复本周发现的问题。
- [x] README 增加安全设计说明。
- [x] 推送 GitHub。

## 第 8 周：日志追踪和成本延迟统计

目标：能讲清楚 Agent 出错怎么排查。

### Day 50

- [x] 设计 trace 数据结构。
- [x] 字段包含 run_id、step、tool_name、input、output、latency、status。
- [x] 建 trace 表。

### Day 51

- [x] 记录每次模型调用。
- [x] 保存模型名、token、耗时、是否成功。
- [x] 失败时保存错误信息。

### Day 52

- [x] 记录每次工具调用。
- [x] 保存参数、返回摘要、错误信息。
- [x] 支持按 run_id 查询。

### Day 53

- [x] 前端展示 trace。
- [x] 用户能看到 Agent 每一步做了什么。
- [x] 隐藏过长的原始参数。

### Day 54

- [x] 统计平均响应时间。
- [x] 统计失败率。
- [x] 统计平均工具调用次数。

### Day 55

- [x] 制造 5 个错误场景。
- [x] 练习排查检索不到、工具报错、模型格式错、引用缺失、超时。
- [x] 写排查案例文档。

### Day 56

- [x] README 增加 observability 章节。
- [x] 截图展示 trace 面板。
- [x] 推送 GitHub。

## 第 9 周：评测集和检索优化

目标：项目从 demo 变成可评估系统。

### Day 57

- [x] 从测试文档中整理 30 个问题。
- [x] 标注标准答案。
- [x] 标注来源页码。
- [x] 保存为 `eval/questions.json`。

### Day 58

- [x] 写批量评测脚本。
- [x] 自动调用 RAG 接口。
- [x] 保存每条问题的结果。

### Day 59

- [x] 计算 top-3 检索命中率。
- [x] 统计没有命中的问题。
- [x] 找出检索失败原因。

### Day 60

- [x] 计算引用完整率。
- [x] 统计没有引用的回答。
- [x] 修复 prompt 或输出检查。

### Day 61

- [x] 统计失败原因。
- [x] 分类为切分问题、检索问题、prompt 问题、模型幻觉、文档缺失。
- [x] 写失败分析表。

### Day 62

- [x] 优化 chunk size。
- [x] 优化 top_k。
- [x] 优化 score threshold。
- [x] 记录指标前后对比。

### Day 63

- [x] README 增加评测报告。
- [x] 写清楚指标不是拍脑袋。
- [x] 推送 GitHub。

## 第 10 周：Docker 部署和 MCP 加分项

目标：项目可部署。主项目稳定后，再做一个只读 MCP 工具。

### Day 64

- [x] 写后端 Dockerfile。
- [x] 构建后端镜像。
- [x] 容器中能启动 FastAPI。

### Day 65

- [x] 写 docker compose。
- [x] 编排后端、PostgreSQL。
- [x] 一条命令启动完整项目。

### Day 66

- [x] 配置环境变量。
- [x] API key 不写死。
- [x] 数据库地址不写死。

### Day 67

- [x] 在新目录完整启动一次。
- [x] 按 README 验证流程。
- [x] 修复环境问题。

### Day 68

- [x] 可选：学习 MCP 基本概念。
- [x] 只做只读工具。
- [x] 不做删除文件或执行命令。

### Day 69

- [x] 可选：实现最小 MCP server。
- [x] 工具为 `list_documents` 或 `search_documents`。
- [x] Agent 能通过 MCP 查询文档。

### Day 70

- [x] README 增加部署说明。
- [x] 如果 MCP 完成，增加 MCP 设计说明。
- [ ] 推送 GitHub。

## 第 11 周：项目包装和简历

目标：让项目能被面试官快速看懂。

### Day 71

- [x] 重写 README 首页。
- [x] 第一屏写清楚项目是什么。
- [x] 写清楚解决什么问题。
- [x] 写清楚核心亮点。

### Day 72

- [x] 画架构图。
- [x] 包含前端、FastAPI、PostgreSQL、pgvector、LLM、工具系统、trace。
- [x] 加到 README。

### Day 73

- [x] 写核心流程图。
- [x] 覆盖上传文档、切分、向量化、检索、生成、引用、trace。
- [x] 加到 README。

### Day 74

- [x] 写项目难点。
- [x] 至少包含引用溯源、拒答、工具权限、trace、评测。
- [x] 每个难点写你怎么解决。

### Day 75

- [x] 写简历项目描述第一版。
- [x] 不写"了解"和"熟悉"。
- [x] 用"实现、设计、优化、构建、统计"这类动词。

### Day 76

- [x] 准备 20 个项目面试问题。
- [x] 每个问题写 3-5 句话答案。
- [x] 重点准备 RAG 和 Agent 深挖。

### Day 77

- [ ] 录制 3-5 分钟 demo。
- [x] 演示上传文档、提问、引用、工具调用、trace。
- [x] 保存演示脚本。

## 第 12 周：面试冲刺和投递

目标：开始投递，不继续躲在学习里。

### Day 78

- [ ] 整理简历。
- [ ] 项目经历放在前面。
- [ ] 技能栈匹配 JD 关键词。

### Day 79

- [ ] 准备后端面试基础。
- [ ] 复习 HTTP、SQL、索引、事务、Docker。
- [ ] 写一页后端面试笔记。

### Day 80

- [ ] 准备 LLM 面试基础。
- [ ] 复习 token、上下文、结构化输出、tool calling、流式输出。
- [ ] 写一页 LLM 面试笔记。

### Day 81

- [ ] 准备 RAG 面试基础。
- [ ] 复习 chunk、embedding、向量检索、rerank、引用、评估。
- [ ] 写一页 RAG 面试笔记。

### Day 82

- [ ] 准备 Agent 面试基础。
- [ ] 复习工具设计、权限控制、失败重试、trace、guardrails。
- [ ] 写一页 Agent 面试笔记。

### Day 83

- [ ] 投递 20 个岗位。
- [ ] 方向：AI 后端、LLM 应用、RAG 工程、Agent 工程、Python 后端。
- [ ] 建投递表。

### Day 84

- [ ] 做一次模拟面试。
- [ ] 录音复盘。
- [ ] 修改简历和面试回答。

## 最后 7 天缓冲

### Day 85

- [ ] 修 README、截图、运行说明。
- [ ] 确保别人能按照 README 跑起来。

### Day 86

- [ ] 修复 demo 中最影响观感的 bug。
- [ ] 不做大重构。

### Day 87

- [ ] 把评测结果写得更清楚。
- [ ] 给指标配失败案例。

### Day 88

- [ ] 简历改第二版。
- [ ] 每条项目经历都写成结果导向。

### Day 89

- [ ] 再投 20 个岗位。
- [ ] 给不同岗位微调简历标题和技能词。

### Day 90

- [ ] 模拟面试第二次。
- [ ] 重点练项目深挖。

### Day 91

- [ ] 总复盘。
- [ ] 整理项目链接、demo、简历、投递表。
- [ ] 写下一阶段计划。

## 每周检查

- [ ] 本周至少 5 次 commit。
- [ ] 主项目还能正常启动。
- [ ] README 跟上了最新功能。
- [ ] 有可展示截图。
- [ ] 记录了失败案例。
- [ ] 能用 3 分钟讲清楚本周做了什么。

## 简历写法

不要写：

```md
熟悉 RAG、了解 Agent、使用过 LangChain。
```

建议写：

```md
独立实现企业知识库 Agent，支持 PDF 上传解析、文本切分、embedding 向量检索、RAG 引用溯源、tool calling、敏感操作确认和调用 trace；使用 PostgreSQL 保存文档元数据、会话和日志，使用 pgvector 管理向量检索；构建 50 条评测集，统计 top-3 检索命中率、引用完整率和失败原因，并通过调整 chunk size、top_k 和拒答阈值优化回答稳定性。
```

## 每天学习记录模板

```md
## 2026-xx-xx

### 今天完成
- [ ] 

### 今天提交
- [ ] 

### 今天卡点
- [ ] 

### 明天任务
- [ ] 

### 项目当前是否能运行
- [ ] 是
- [ ] 否
```

## 参考官方文档

- [ ] FastAPI Tutorial：https://fastapi.tiangolo.com/tutorial/
- [ ] PostgreSQL Windows Download：https://www.postgresql.org/download/windows/
- [ ] pgvector：https://github.com/pgvector/pgvector
- [ ] OpenAI Agents SDK：https://developers.openai.com/api/docs/guides/agents
- [ ] LangChain RAG：https://docs.langchain.com/oss/python/langchain/rag
- [ ] Model Context Protocol：https://modelcontextprotocol.io/docs/getting-started/intro
