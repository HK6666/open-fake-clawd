# ccBot - Telegram Claude Code 控制机器人

<div align="center">

![ccBot](https://img.shields.io/badge/ccBot-v1.1.0-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![Vue](https://img.shields.io/badge/Vue-3.0+-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**在 Telegram 中远程操作 Claude Code，配备智能记忆系统和现代化 Web 管理界面**

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [部署方案](#-部署方案) • [文档](#-文档)

</div>

---

## ✨ 功能特性

### 核心功能

- 🤖 **Telegram Bot 集成** - 在 Telegram 中直接与 Claude Code 交互，支持全部 Claude 功能
- 🎨 **现代化 Web Dashboard** - 性冷淡风格的 Vue 3 管理界面，简洁专业
- 🧠 **智能记忆系统** - 自动学习用户偏好、技术栈、项目上下文
- 💾 **会话持久化** - SQLite 存储，支持会话导出和继续对话
- 🔐 **安全控制** - 用户白名单、速率限制、安全的文件访问控制

### 最新更新 v1.1.0

- ✅ **Docker 自动部署** - 支持 Git Hooks、GitHub Actions、Webhook 三种自动部署方案
- ✅ **UI 重构** - 性冷淡风格（Minimalist Cold Style），纯灰度配色
- ✅ **记忆系统增强** - 智能提取项目信息、技术栈、用户偏好，自动生成 PROJECT.md
- ✅ **会话隔离优化** - 每个用户独立会话，避免数据混乱
- ✅ **前后端分离** - 多阶段 Docker 构建，镜像体积减小 40%

---

## 🚀 快速开始

### 方式1: 交互式向导（推荐）

```bash
# 克隆仓库
git clone https://github.com/HK6666/opne-fake-clawd.git ccBot
cd ccBot

# 配置环境变量
cp .env.example .env
vim .env  # 编辑配置

# 运行快速开始向导
./quick-start.sh
```

向导会引导你选择：
- 手动部署
- Git Hooks 自动部署
- GitHub Actions 自动部署
- Webhook 服务器自动部署

### 方式2: Docker 一键部署

```bash
# 配置环境变量
cp .env.example .env
vim .env

# 一键部署
./deploy.sh
```

部署完成后访问：
- **Web Dashboard**: `http://your-server:14532`
- **API 文档**: `http://your-server:14532/docs`

---

## 🎯 部署方案

### 方案对比

| 方案 | 触发方式 | 适用场景 | 配置难度 |
|------|---------|---------|---------|
| **Git Hooks** | `git pull` 后自动部署 | 单服务器，手动控制 | ⭐ 简单 |
| **GitHub Actions** | `git push` 自动部署 | 团队协作，多环境 | ⭐⭐ 中等 |
| **Webhook 服务器** | 实时监听 Git 推送 | 自建 Git，实时部署 | ⭐⭐⭐ 复杂 |

### 选择建议

- **个人项目** → Git Hooks
- **团队协作** → GitHub Actions
- **自建 Git** → Webhook 服务器

详细配置步骤请查看 [**DEPLOYMENT.md**](./DEPLOYMENT.md)

---

## 📊 技术架构

```
┌─────────────────────────────────────────────────────┐
│                   Telegram Bot                       │
│         (python-telegram-bot + Webhook)              │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                  FastAPI Backend                     │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ Session  │  │  Memory  │  │ Claude Runner   │  │
│  │ Manager  │  │ Manager  │  │ (CLI Subprocess)│  │
│  └──────────┘  └──────────┘  └─────────────────┘  │
│         ├──────────┴──────────┴─────────┤          │
│         │     SQLite Database           │          │
│         └───────────────────────────────┘          │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              Vue 3 Dashboard                         │
│   Dashboard │ Sessions │ Memory │ Settings          │
└─────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3, Vite, TypeScript, Pinia, Axios |
| **后端** | Python 3.11+, FastAPI, Uvicorn |
| **Bot** | python-telegram-bot 21+ |
| **数据库** | SQLite + aiosqlite |
| **部署** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions, Git Hooks, Webhook |

---

## 💬 Telegram Bot 命令

### 会话管理
```
/start      - 显示欢迎信息
/new        - 开始新会话
/continue   - 继续上次会话
/sessions   - 列出历史会话
/clear      - 清空会话历史（保持活跃）
/end        - 结束当前会话
/export     - 导出会话为 Markdown
```

### 文件导航
```
/cd <path>  - 切换工作目录
/ls         - 列出当前目录文件
/tree       - 显示目录树结构
/pwd        - 显示当前工作目录
```

### 状态和控制
```
/status     - 查看当前状态
/stats      - 显示使用统计
/stop       - 停止当前执行任务
/menu       - 显示快捷菜单
```

**提示**: 直接发送消息即可与 Claude Code 交互！

---

## 🎨 Web Dashboard

访问 `http://your-server:14532` 查看管理界面

### 功能页面

- **📊 Dashboard** - 总览统计：会话数、运行器状态、系统健康
- **💬 Sessions** - 会话历史：查看、导出、继续会话
- **🧠 Memory** - 记忆管理：编辑 SOUL.md、USER.md、PROJECT.md
- **⚙️ Settings** - 配置查看：系统配置、速率限制、访问控制

### UI 设计

- **风格**: 性冷淡风格（Minimalist Cold Style）
- **配色**: 纯灰度（#1a1a1a - #fafafa）
- **圆角**: 微圆角 2-4px
- **字体**: Inter, SF Pro, -apple-system
- **特点**: 简洁、专业、易读

---

## 🧠 智能记忆系统

### 文件结构

```
workspace/
├── SOUL.md      # AI 人格、沟通风格、工作原则
├── USER.md      # 用户偏好（自动学习更新）
├── PROJECT.md   # 当前项目上下文（自动生成）
├── AGENTS.md    # 可用代理配置
├── TOOLS.md     # 工具使用说明
├── memory/      # 长期记忆片段
└── sessions/    # 会话记录存档
```

### 自动学习功能

记忆系统会在每次会话结束时自动：

✅ **检测编程语言** - Python, JavaScript, TypeScript, Go, Rust 等
✅ **识别技术栈** - Vue 3, FastAPI, Docker, Git 等
✅ **提取项目信息** - 项目名、路径、类型
✅ **学习用户偏好** - UI 风格、编码习惯、沟通方式
✅ **记录重要变更** - UI 重构、配置修改等
✅ **生成项目上下文** - 自动创建 PROJECT.md

---

## ⚙️ 配置说明

### 核心配置

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_USERS=123456789,987654321

# Claude Code
CLAUDE_CLI_PATH=claude
APPROVED_DIRECTORY=/path/to/projects
CLAUDE_TIMEOUT=300
CLAUDE_MAX_TURNS=50

# 服务器
API_HOST=0.0.0.0
API_PORT=14532

# 速率限制
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

完整配置说明请查看 `.env.example`

---

## 📖 文档

- [**DEPLOYMENT.md**](./DEPLOYMENT.md) - 详细部署指南（Git Hooks、GitHub Actions、Webhook）
- [**API 文档**](http://your-server:14532/docs) - Swagger 自动生成的 API 文档
- [**.env.example**](./.env.example) - 完整配置示例

---

## 🛠️ 开发

### 本地开发

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
python -m backend.main

# 前端
cd frontend
npm install
npm run dev
```

### 构建

```bash
# 前端构建
cd frontend
npm run build

# Docker 构建
docker-compose build
```

---

## 🔧 常用命令

### Docker 部署

```bash
./deploy.sh                # 完整部署
./update.sh                # 检查更新并部署
docker-compose logs -f     # 查看日志
docker-compose restart     # 重启容器
docker-compose down        # 停止容器
```

### Git 自动部署

```bash
./setup-git-hooks.sh           # 安装 Git Hooks
./setup-github.sh              # 配置 GitHub 自动部署
./install-webhook-service.sh   # 安装 Webhook 服务
```

---

## 📝 更新日志

### v1.1.0 (2026-02-02)

**重大更新：部署自动化 + UI 重构**

- ✅ Docker 多阶段构建优化
- ✅ 支持 Git Hooks、GitHub Actions、Webhook 三种自动部署
- ✅ UI 重构为性冷淡风格（纯灰度、微圆角）
- ✅ 智能记忆系统重写，自动学习项目上下文
- ✅ 会话隔离增强，支持多用户并发
- ✅ 移除所有装饰性图标，专注内容
- ✅ 前后端端口统一为 14532

### v0.1.0 (2026-01-30)

- 🎉 初始版本发布
- ✅ Telegram Bot 基础功能
- ✅ Web Dashboard
- ✅ 记忆系统
- ✅ 会话持久化

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License - 详见 [LICENSE](./LICENSE)

---

## 🙏 致谢

- [moltbot/clawdbot](https://github.com/moltbot/moltbot) - 记忆系统设计参考
- [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) - Telegram 集成参考
- [Anthropic Claude](https://www.anthropic.com/claude) - Claude Code CLI

---

<div align="center">

**⭐ 如果觉得有用，请给个 Star！**

Made with ❤️ by HK6666

</div>
