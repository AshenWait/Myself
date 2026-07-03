# Personal Portfolio

AshenWait 的个人作品集网站，展示简历、项目和后续实验区。当前首个项目是 [Knowledge Agent](https://github.com/AshenWait/knowledge-agent)。

## Tech Stack

- Vite
- React
- TypeScript
- React Router
- Lucide React
- Oxlint

## Development

```powershell
npm install
npm run dev
```

## Checks

```powershell
npm run lint
npm run build
```

## Content

- Resume content: `src/content/resume.ts`
- Project content: `src/content/projects.ts`
- Resume image: `public/resume/resume.png`

Replace `public/resume/resume.png` with the real resume image while keeping the same file name.

## Deploy To ECS

The GitHub Actions workflow builds the static site and syncs `dist/` to `/var/www/personal-portfolio` on the ECS server.

Required GitHub repository secrets:

- `ALIYUN_HOST`: ECS public IP or domain
- `ALIYUN_USER`: SSH user, for example `root` or a deploy user
- `ALIYUN_SSH_KEY`: private SSH key with server access
- `ALIYUN_PORT`: SSH port, usually `22`

On the server, install Nginx and enable the config in `deploy/nginx/personal-portfolio.conf`. The site can first be served by public IP over HTTP, then moved to domain + HTTPS later.

```bash
sudo mkdir -p /var/www/personal-portfolio
sudo chown -R "$USER":"$USER" /var/www/personal-portfolio
sudo cp deploy/nginx/personal-portfolio.conf /etc/nginx/sites-available/personal-portfolio
sudo ln -s /etc/nginx/sites-available/personal-portfolio /etc/nginx/sites-enabled/personal-portfolio
sudo nginx -t
sudo systemctl reload nginx
```
