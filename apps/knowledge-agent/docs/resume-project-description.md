# 简历项目描述（第一版）

## 项目名称

Knowledge Agent：企业知识库 RAG + Agent 系统

## 项目角色

AI 后端 / LLM 应用工程项目

## 技术栈

Python、FastAPI、SQLAlchemy、PostgreSQL、pgvector、React、LLM API、RAG、Tool Calling、Guardrails、Trace、离线评测

## 一句话项目描述

设计并实现企业知识库 Agent，支持 PDF、txt、markdown 文档上传解析、文本切分、embedding 向量检索、RAG 引用溯源、Agent 工具调用、权限控制、trace 追踪和离线评测。

## 简历项目经历写法

Knowledge Agent：企业知识库 RAG + Agent 系统

- 实现文档上传和解析链路，支持 PDF、txt、markdown 文件校验、原文件保存、文本抽取、chunk 切分和元数据入库。
- 设计基于 PostgreSQL + pgvector 的向量检索流程，将文档 chunk 生成 embedding 后写入数据库，并支持按问题向量检索 top_k 相关片段。
- 构建 RAG 问答链路，将用户问题、检索片段和回答规则拼接为 prompt，调用 LLM 生成答案，并返回文档名、页码、chunk_id、原文片段和距离分数作为引用来源。
- 设计拒答和输出检查机制，在检索结果不足或回答缺少引用来源时拦截输出，降低无来源回答和模型幻觉风险。
- 构建 Agent 工具系统，支持文档检索、文档总结、文档列表和创建笔记，并通过工具权限等级、会话白名单和用户确认控制写入类操作。
- 实现 trace 追踪能力，为每次问答生成 run_id，记录模型调用、工具调用、输入输出摘要、耗时和状态，支持前端按 run_id 查看完整执行步骤。
- 构建离线评测流程，使用固定评测集批量调用 RAG 接口，统计 top-3 检索命中率、引用完整率和失败原因，并用评测结果指导 chunk size、top_k 和阈值优化。

## 精简版

独立实现企业知识库 RAG + Agent 系统，支持文档上传解析、文本切分、embedding 向量检索、RAG 引用溯源、Agent 工具调用、权限控制和 trace 追踪；使用 PostgreSQL + pgvector 管理文档元数据和向量检索，构建离线评测流程统计检索命中率、引用完整率和失败原因，并根据评测结果优化检索参数和拒答策略。

## 面试口述版

这个项目是一个企业知识库 Agent。用户上传文档后，系统会解析文本、切分 chunks、生成 embedding 并保存到 PostgreSQL + pgvector。用户提问时，系统先做向量检索，再把相关片段交给 LLM 生成回答，并返回引用来源。为了让项目更接近真实工程，我还实现了 Agent 工具权限控制、无引用拒答、trace 追踪和离线评测，用来解决回答可信、工具安全和问题排查这三个核心问题。

## 不推荐写法

不要写：

```txt
会 RAG，会 Agent，用过向量数据库。
```

原因是这类表达只说明接触过，不能证明你独立完成过工程交付。

更好的写法是：

```txt
实现 RAG 问答链路，设计 Agent 工具权限控制，构建 trace 追踪和离线评测流程。
```
