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
- Optional avatar image: `public/avatar/avatar.png`
- Optional resume image: `public/resume/resume.png`

If `public/avatar/avatar.png` exists and loads successfully, the homepage uses it as the default avatar. The avatar upload button can also preview a local image in the browser.

If `public/resume/resume.png` exists and loads successfully, the homepage displays it next to the resume. If it is absent, the image panel is hidden.

## Deploy To ECS

The GitHub Actions workflow builds this app from `apps/portfolio` and syncs `apps/portfolio/dist/` to `/var/www/personal-portfolio` on the ECS server.

Required GitHub repository secrets:

- `ALIYUN_HOST`: ECS public IP or domain
- `ALIYUN_USER`: SSH user, for example `root` or a deploy user
- `ALIYUN_SSH_KEY`: private SSH key with server access
- `ALIYUN_PORT`: SSH port, usually `22`

On the server, install Nginx and enable the config from the repository root at `deploy/nginx/personal-portfolio.conf`. The site can first be served by public IP over HTTP, then moved to domain + HTTPS later.

```bash
sudo mkdir -p /var/www/personal-portfolio
sudo chown -R "$USER":"$USER" /var/www/personal-portfolio
sudo cp deploy/nginx/personal-portfolio.conf /etc/nginx/sites-available/personal-portfolio
sudo ln -s /etc/nginx/sites-available/personal-portfolio /etc/nginx/sites-enabled/personal-portfolio
sudo nginx -t
sudo systemctl reload nginx
```
