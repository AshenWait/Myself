# Week 10：Docker 部署和 MCP 加分项说明

第 10 周的目标是把项目从“本机能跑”推进到“可以部署、可以解释部署方式，并具备一个 MCP 加分项”。

## Docker 部署

本项目当前支持用 Docker Compose 启动后端和数据库：

```txt
db   PostgreSQL + pgvector
api  FastAPI 后端
```

启动命令：

```powershell
docker compose up --build
```

验证命令：

```powershell
curl.exe http://127.0.0.1:8000/health
```

预期返回：

```json
{
  "status": "ok",
  "app": "Knowledge Agent",
  "version": "0.1.0",
  "environment": "local"
}
```

## 部署文件职责

| 文件 | 作用 |
| --- | --- |
| `Dockerfile` | 构建 FastAPI 后端镜像，安装 Python 依赖并启动 `app.main:app` |
| `.dockerignore` | 排除 `.env`、`.venv`、日志、上传文件、前端依赖等不该进入镜像的内容 |
| `docker-compose.yml` | 编排 PostgreSQL + pgvector 和 FastAPI 后端 |
| `.env.example` | 提供环境变量模板，不包含真实 API key |
| `docker/postgres/init.sql` | 初始化 PostgreSQL 的 pgvector 扩展 |
| `docs/day67-deployment-verification.md` | 记录新目录验证流程和常见部署问题 |

## 环境变量设计

本地直接运行后端时，数据库地址使用主机端口：

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/knowledge_agent
```

Docker Compose 内部运行后端时，数据库地址使用服务名 `db`：

```env
DOCKER_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/knowledge_agent
```

原因是容器里的 `127.0.0.1` 指的是容器自己，不是 Windows 主机。Compose 网络里的服务应该用服务名互相访问。

API key 不写入镜像，也不提交到 Git。运行时通过 `.env` 注入：

```env
DEEPSEEK_API_KEY=replace-with-your-deepseek-api-key
DASHSCOPE_API_KEY=replace-with-your-dashscope-api-key
```

## MCP 加分项

第 10 周还实现了一个最小 MCP server：

```txt
app/mcp_server.py
```

它使用 MCP Python SDK 的 `FastMCP` 暴露两个只读工具：

| MCP 工具 | 作用 | 是否写入数据库 |
| --- | --- | --- |
| `list_documents(limit)` | 查询已上传文档列表 | 否 |
| `search_documents(query, limit)` | 按关键词检索文档 chunks | 否 |

启动方式：

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe app\mcp_server.py
```

MCP 默认使用 stdio 通信，启动后不会打开网页。它会等待 MCP client 连接；手动停止时按 `Ctrl + C`。

## MCP 安全边界

当前 MCP server 只做只读查询，不开放：

```txt
create_note
delete_document
执行本地命令
读取任意本地文件
暴露 .env 或 API key
```

原因是 MCP 工具可能被模型或客户端触发。只读查询的风险较低，而写入、删除、命令执行会影响数据库或本机安全。

## 面试表达

```txt
第 10 周我把项目做了部署化处理。后端通过 Dockerfile 构建镜像，PostgreSQL + pgvector 和 FastAPI 用 docker compose 编排，数据库初始化时创建 vector 扩展，环境变量通过 .env 注入，API key 不写入镜像。为了验证可迁移性，我还补了新目录启动流程和常见问题记录。

MCP 加分项上，我实现了一个最小 MCP server，只暴露 list_documents 和 search_documents 两个只读工具。它复用项目已有数据库模型，只返回文档列表和 chunk 检索结果，不开放写入、删除或命令执行，保证工具边界清楚。
```
