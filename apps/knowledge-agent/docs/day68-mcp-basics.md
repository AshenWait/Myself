# Day 68：MCP 基本概念和本项目设计边界

## 今天目标

Day 68 不急着写 MCP server。今天先回答三个问题：

- MCP 是什么？
- 它和我们已经写过的 Agent 工具有什么关系？
- 本项目为什么只做只读 MCP 工具？

## MCP 是什么

MCP 全称是 Model Context Protocol，可以理解成 AI 应用和外部系统之间的标准连接协议。

如果不用 MCP，每接一个外部系统都要为当前 Agent 单独写一套接入方式：

```txt
Agent -> GitHub API
Agent -> 数据库 API
Agent -> 文件系统 API
Agent -> 日历 API
```

用了 MCP 之后，可以变成：

```txt
AI Client -> MCP Server -> 外部系统
```

MCP server 负责把某个外部系统的能力暴露出来，AI client 负责连接这些 server，并把可用能力交给模型或应用使用。

一句话定义：

```txt
MCP 是让 AI 应用用统一方式连接外部工具、数据源和提示模板的协议。
```

## MCP 的三个核心能力

| 能力 | 谁来使用 | 作用 | 本项目怎么理解 |
| --- | --- | --- | --- |
| Tools | 模型主动调用 | 执行一个带参数的操作 | `list_documents`、`search_documents` 这类可调用函数 |
| Resources | 应用读取 | 暴露只读上下文数据 | 某篇文档、某个 chunk、某个评测报告 |
| Prompts | 用户选择 | 提供可复用提示词模板 | “总结文档”“分析检索失败原因”这类固定工作流 |

Day 68 只学习概念。Day 69 如果继续做，会先实现最小 MCP server，并只暴露只读工具。

## MCP 和本项目已有 Agent 工具的关系

我们第 6 周已经做过 Agent 工具：

```txt
AgentService
  -> list_documents()
  -> retrieve_documents(query)
  -> summarize_document(document_id)
  -> create_note(...)
```

这些工具目前是项目内部 Python 函数，由 `AgentService` 直接调用。

MCP 做的是把类似能力包装成一个标准服务：

```txt
MCP Client
  -> 发现工具列表
  -> 调用 list_documents
  -> 调用 search_documents
  -> 拿到结构化结果
```

这样其他支持 MCP 的 AI 客户端，也可以用同一种方式访问 Knowledge Agent 的文档查询能力。

## 为什么 Day 68 只做只读工具

MCP 工具可能被模型主动调用，所以边界必须非常清楚。

本项目 Day 68 / Day 69 的 MCP 范围只允许：

```txt
允许：
- list_documents：查询文档列表
- search_documents：按关键词或向量检索文档片段

不允许：
- delete_document：删除文档
- create_note：写入数据库
- 执行本地命令
- 读取任意本地文件
- 暴露 API key 或数据库密码
```

原因很简单：只读工具出错时通常只是返回错数据；写入、删除和命令执行一旦出错，可能破坏数据或影响本机安全。

## Day 69 的最小设计草图

如果下一天继续实现，建议只做一个最小 MCP server：

```txt
knowledge_agent_mcp_server
  -> tool: list_documents()
  -> tool: search_documents(query: str, limit: int = 3)
```

数据流：

```txt
MCP client
  -> 调用 search_documents
  -> MCP server 接收 query
  -> 调用项目已有 DocumentService 或检索逻辑
  -> 返回文档名、页码、chunk_id、片段内容
```

返回结果要保持只读：

```json
{
  "results": [
    {
      "document_id": 1,
      "filename": "sample.txt",
      "page_number": 1,
      "chunk_id": 3,
      "content": "..."
    }
  ]
}
```

## 面试表达

```txt
我把 MCP 理解为 AI 应用连接外部系统的标准协议。它可以把工具、资源和提示模板暴露给支持 MCP 的客户端。本项目里已经有 Agent 工具系统，所以 MCP 加分项不是重新发明工具，而是把文档查询能力包装成标准 MCP server。考虑到安全边界，我只计划暴露 list_documents 和 search_documents 这类只读能力，不开放删除、写入或命令执行。
```

## 参考资料

- 官方 MCP server 概念文档：https://modelcontextprotocol.io/docs/learn/server-concepts
- 官方 MCP SDK 文档：https://modelcontextprotocol.io/docs/sdk
