# Day 67 部署验证记录

Day 67 的目标是模拟一个新目录里的启动流程，确认项目不依赖当前电脑上的 Python 虚拟环境或已有数据库状态。

## 验证目标

- 在新目录中准备 `.env`。
- 使用 Docker Compose 启动 PostgreSQL + pgvector 和 FastAPI 后端。
- 按 README 验证 `/health` 和 `/docs`。
- 记录启动过程中遇到的问题和修复方式。

## 新目录验证流程

建议复制项目到一个临时目录，或者从 GitHub 重新 clone 一份项目：

```powershell
cd C:\Users\yangp\Desktop
git clone <你的仓库地址> knowledge-agent-day67-check
cd knowledge-agent-day67-check
```

如果当前还没有远程仓库可 clone，也可以手动复制项目目录。复制时不要复制这些内容：

```txt
.venv
.env
frontend/node_modules
frontend/dist
storage/uploads
*.log
```

## 准备环境变量

```powershell
Copy-Item .env.example .env
```

然后打开 `.env`，至少确认这些变量存在：

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/knowledge_agent
DOCKER_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/knowledge_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=knowledge_agent
POSTGRES_HOST_PORT=5433
API_HOST_PORT=8000
API_IMAGE_TAG=day67
DEEPSEEK_API_KEY=replace-with-your-deepseek-api-key
DASHSCOPE_API_KEY=replace-with-your-dashscope-api-key
```

如果只验证 `/health`，API key 可以先保持占位值。  
如果要验证上传、embedding、RAG 问答，需要替换成真实 key。

## 启动服务

```powershell
docker compose up --build
```

另开一个 PowerShell 验证：

```powershell
curl.exe http://127.0.0.1:8000/health
```

预期结果：

```json
{
  "status": "ok",
  "app": "Knowledge Agent",
  "version": "0.1.0",
  "environment": "local"
}
```

浏览器访问：

```txt
http://127.0.0.1:8000/docs
```

查看容器：

```powershell
docker compose ps
```

停止服务：

```powershell
docker compose down
```

不要随便运行：

```powershell
docker compose down -v
```

因为 `-v` 会删除数据库 volume。

## 常见问题和修复

### 1. `.env` 变量缺失

现象：

```txt
variable is not set
```

修复：

```powershell
Copy-Item .env.example .env
```

然后确认 `.env` 里包含 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`DOCKER_DATABASE_URL` 等变量。

### 2. API 容器连不上数据库

现象：

```txt
connection refused
could not translate host name
```

修复：

Docker Compose 里的后端数据库地址必须使用服务名 `db`：

```env
DOCKER_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/knowledge_agent
```

不要在容器里使用 `127.0.0.1` 连接数据库。

### 3. 端口被占用

现象：

```txt
port is already allocated
```

修复：

修改 `.env`：

```env
API_HOST_PORT=8001
POSTGRES_HOST_PORT=5434
```

然后重新启动：

```powershell
docker compose up --build
```

### 4. pgvector 扩展不存在

现象：

```txt
type "vector" does not exist
```

修复：

确认 `docker/postgres/init.sql` 存在：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

如果数据库 volume 是旧的，初始化脚本可能不会重复执行。开发环境可以在确认不需要旧数据后执行：

```powershell
docker compose down -v
docker compose up --build
```

注意：这会删除当前 compose 的数据库数据。

## Day 67 验证结论模板

```md
### Day 67 验证结论

- 新目录位置：
- 是否成功复制或 clone 项目：
- 是否已根据 `.env.example` 创建 `.env`：
- `docker compose up --build` 是否成功：
- `/health` 是否返回 ok：
- `/docs` 是否能打开：
- 遇到的问题：
- 修复方式：
```
