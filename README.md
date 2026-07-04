# AshenWait Monorepo

这个仓库把个人作品集和 Knowledge Agent 复刻版放在一起，保持一个总项目、两个清晰应用。

## Apps

- `apps/portfolio`: 个人作品集网站，展示简历、项目和实验区。
- `apps/knowledge-agent`: 企业知识库 RAG + Agent 项目复刻版。

## Common Commands

作品集：

```powershell
cd apps/portfolio
npm install
npm run dev
npm run lint
npm run build
```

Knowledge Agent 前端：

```powershell
cd apps/knowledge-agent/frontend
npm install
npm run dev
npm run lint
npm run build
```

Knowledge Agent 后端：

```powershell
cd apps/knowledge-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Notes

- `apps/knowledge-agent/.env.example` 是环境变量模板，真实 `.env` 不提交。
- 上传文件只保留 `storage/uploads/.gitkeep`，运行时上传内容不进仓库。
- 作品集部署 workflow 只构建 `apps/portfolio` 并同步到阿里云 ECS 的 `/var/www/personal-portfolio`。
