# ccBot 自动部署指南

本文档介绍如何设置 ccBot 的 Docker 部署和 Git 自动更新。

## 📋 目录

- [快速开始](#快速开始)
- [部署方式对比](#部署方式对比)
- [方式1: 本地 Git Hooks](#方式1-本地-git-hooks)
- [方式2: GitHub Actions](#方式2-github-actions)
- [方式3: Webhook 服务器](#方式3-webhook-服务器)
- [常见问题](#常见问题)

---

## 快速开始

### 前置要求

- Docker 和 Docker Compose 已安装
- Git 已安装
- 已配置 `.env` 文件

### 首次部署

```bash
# 1. 克隆仓库
git clone <your-repo-url> ccbot
cd ccbot

# 2. 配置环境变量
cp .env.example .env
vim .env  # 编辑配置

# 3. 部署
./deploy.sh
```

---

## 部署方式对比

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **本地 Git Hooks** | 单服务器，手动 `git pull` | 简单，无需额外配置 | 需要手动拉取代码 |
| **GitHub Actions** | GitHub 托管，多服务器 | 完全自动化，支持多环境 | 需要 GitHub，配置稍复杂 |
| **Webhook 服务器** | 自建 Git 或 GitLab | 实时响应，灵活 | 需要开放端口，维护服务 |

---

## 方式1: 本地 Git Hooks

适合单服务器部署，每次 `git pull` 后自动重新部署。

### 设置步骤

```bash
# 运行设置脚本
./setup-git-hooks.sh
```

### 使用方法

```bash
# 在服务器上拉取最新代码
git pull origin main

# Git hooks 会自动触发部署
# 无需手动运行 deploy.sh
```

### 工作原理

- 在 `.git/hooks/post-merge` 安装钩子
- 检测到文件变更后自动重启容器
- 如果 Docker 配置变更，自动重新构建

---

## 方式2: GitHub Actions

适合使用 GitHub 托管代码，推送后自动部署到服务器。

### 设置步骤

#### 1. 生成 SSH 密钥对

在本地生成密钥（如果还没有）：

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```

#### 2. 添加公钥到服务器

```bash
# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github_actions.pub user@your-server

# 或手动添加
cat ~/.ssh/github_actions.pub
# 复制内容，然后在服务器上：
echo "粘贴的公钥内容" >> ~/.ssh/authorized_keys
```

#### 3. 配置 GitHub Secrets

在 GitHub 仓库中设置以下 Secrets：

1. 进入仓库 **Settings** → **Secrets and variables** → **Actions**
2. 添加以下 secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SERVER_HOST` | 服务器 IP 或域名 | `123.456.789.0` |
| `SERVER_USER` | SSH 登录用户名 | `ubuntu` |
| `SSH_PRIVATE_KEY` | SSH 私钥内容 | `cat ~/.ssh/github_actions` 的内容 |
| `DEPLOY_PATH` | 项目部署路径 | `/home/ubuntu/ccbot` |
| `SSH_PORT` | SSH 端口（可选） | `22` |

#### 4. 推送代码自动部署

```bash
git add .
git commit -m "feat: add new feature"
git push origin main

# GitHub Actions 会自动：
# 1. 检测到推送
# 2. SSH 连接到服务器
# 3. 拉取最新代码
# 4. 执行 deploy.sh
```

#### 5. 查看部署状态

- 进入仓库 **Actions** 标签查看部署日志
- 绿色✅ 表示部署成功
- 红色❌ 表示部署失败，点击查看详细日志

---

## 方式3: Webhook 服务器

适合自建 Git 服务器（GitLab, Gitea 等）或需要更灵活的触发机制。

### 设置步骤

#### 1. 启动 Webhook 服务器

```bash
# 设置 Secret Token（推荐）
export WEBHOOK_SECRET="your-random-secret-token"

# 启动服务器
python3 webhook-server.py

# 或使用 systemd 守护进程（推荐生产环境）
```

#### 2. 配置 Systemd 服务（可选但推荐）

创建服务文件：

```bash
sudo vim /etc/systemd/system/ccbot-webhook.service
```

内容：

```ini
[Unit]
Description=ccBot Webhook Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/ccbot
Environment="WEBHOOK_SECRET=your-random-secret-token"
ExecStart=/usr/bin/python3 /path/to/ccbot/webhook-server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start ccbot-webhook
sudo systemctl enable ccbot-webhook
sudo systemctl status ccbot-webhook
```

#### 3. 配置 Git 仓库 Webhook

**GitHub:**

1. 进入仓库 **Settings** → **Webhooks** → **Add webhook**
2. 配置：
   - Payload URL: `http://your-server:9000/webhook`
   - Content type: `application/json`
   - Secret: 你设置的 `WEBHOOK_SECRET`
   - Events: `Just the push event`

**GitLab:**

1. 进入项目 **Settings** → **Webhooks**
2. 配置：
   - URL: `http://your-server:9000/webhook`
   - Secret Token: 你设置的 `WEBHOOK_SECRET`
   - Trigger: `Push events`
   - 分支过滤: `main` 或 `master`

#### 4. 测试 Webhook

推送代码到仓库，webhook 服务器日志应显示：

```
🔔 Received push to refs/heads/main
🚀 Starting deployment...
✅ Deployment successful
```

---

## 手动部署命令

### 部署最新版本

```bash
./deploy.sh
```

### 检查更新并部署

```bash
./update.sh
```

### 查看容器日志

```bash
docker-compose logs -f
```

### 重启容器

```bash
docker-compose restart
```

### 停止容器

```bash
docker-compose down
```

### 完全重新构建

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 常见问题

### Q1: 端口 14532 被占用

**问题**: 启动时提示端口已被占用

**解决方案**:
```bash
# 查看占用端口的进程
sudo lsof -i :14532

# 停止占用的进程或修改 .env 中的端口
```

### Q2: Docker 构建失败

**问题**: `npm install` 或 `pip install` 失败

**解决方案**:
```bash
# 清理 Docker 缓存
docker system prune -a

# 重新构建
./deploy.sh
```

### Q3: Git Hooks 不执行

**问题**: `git pull` 后没有自动部署

**解决方案**:
```bash
# 检查 hook 是否有执行权限
chmod +x .git/hooks/post-merge

# 检查 hook 内容
cat .git/hooks/post-merge

# 重新运行设置脚本
./setup-git-hooks.sh
```

### Q4: GitHub Actions 连接失败

**问题**: SSH 连接服务器失败

**解决方案**:
1. 检查 `SSH_PRIVATE_KEY` 是否正确（包含完整的 BEGIN/END 标记）
2. 检查服务器防火墙是否允许 GitHub Actions IP
3. 确认 `SERVER_HOST` 和 `SERVER_USER` 正确

### Q5: Webhook 不触发

**问题**: 推送代码后 webhook 服务器没反应

**解决方案**:
```bash
# 检查服务器是否运行
sudo systemctl status ccbot-webhook

# 检查防火墙
sudo ufw status
sudo ufw allow 9000/tcp

# 查看 webhook 服务器日志
journalctl -u ccbot-webhook -f
```

---

## 安全建议

1. **使用 HTTPS**: 生产环境建议使用 Nginx 反向代理 + SSL 证书
2. **设置 Webhook Secret**: 防止未授权的部署请求
3. **限制 SSH 访问**: 使用密钥认证，禁用密码登录
4. **定期更新**: 及时更新 Docker 镜像和系统依赖
5. **备份数据**: 定期备份 `workspace/` 和 `ccbot.db`

---

## 监控和日志

### 查看实时日志

```bash
docker-compose logs -f ccbot
```

### 查看最近 100 行日志

```bash
docker-compose logs --tail=100 ccbot
```

### 导出日志到文件

```bash
docker-compose logs ccbot > ccbot.log
```

### 容器健康检查

```bash
docker inspect --format='{{.State.Health.Status}}' ccbot
```

---

## 更多资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [GitHub Actions 文档](https://docs.github.com/actions)

---

**需要帮助？** 提交 Issue 或查看项目文档。
