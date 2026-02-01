# ccBot - Telegram Claude Code 控制机器人

在 Telegram 中远程操作 Claude Code，参考 [moltbot/clawdbot](https://github.com/moltbot/moltbot) 的记忆管理方式。

## 功能特性

- **Telegram Bot**: 在 Telegram 中直接与 Claude Code 交互
- **Web Dashboard**: Vue 3 构建的管理界面，查看会话历史和配置
- **记忆系统**: 使用 .md 文件管理 AI agent 记忆 (SOUL.md, USER.md 等)
- **会话持久化**: SQLite 存储会话历史，支持继续对话
- **安全控制**: 用户白名单 + 速率限制

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / python-telegram-bot |
| 前端 | Vue 3 + Vite + Pinia |
| 数据库 | SQLite |
| CC 调用 | CLI 子进程 |

## 服务器一键部署

### 前置要求

- Python 3.11+
- Node.js 18+ (构建前端)
- Claude Code CLI 已安装并配置

### 一键部署脚本

```bash
# 克隆仓库
git clone https://github.com/HK6666/opne-fake-clawd.git
cd opne-fake-clawd

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 手动部署步骤

**1. 克隆仓库**

```bash
git clone https://github.com/HK6666/opne-fake-clawd.git
cd opne-fake-clawd
```

**2. 配置环境变量**

```bash
cp .env.example .env
nano .env  # 编辑配置
```

必须配置的项目：

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_USERS=your_telegram_user_id
APPROVED_DIRECTORY=/path/to/your/projects
```

**3. 安装 Python 依赖**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

**4. 构建前端**

```bash
cd frontend
npm install
npm run build
cd ..
```

**5. 启动服务**

```bash
python -m backend.main
```

### 使用 systemd 管理服务

创建服务文件 `/etc/systemd/system/ccbot.service`:

```ini
[Unit]
Description=ccBot - Telegram Claude Code Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/opne-fake-clawd
Environment="PATH=/path/to/opne-fake-clawd/venv/bin"
ExecStart=/path/to/opne-fake-clawd/venv/bin/python -m backend.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ccbot
sudo systemctl start ccbot
sudo systemctl status ccbot
```

### Docker 部署 (可选)

```bash
docker build -t ccbot .
docker run -d \
  --name ccbot \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/workspace:/app/workspace \
  ccbot
```

## Telegram Bot 命令

### 会话管理
| 命令 | 功能 |
|------|------|
| `/start` | 显示帮助信息 |
| `/new` | 开始新会话 |
| `/continue` | 继续上次会话 |
| `/sessions` | 列出历史会话 |
| `/clear` | 🆕 清空会话历史（保持会话活跃） |
| `/end` | 结束当前会话 |
| `/export` | 导出会话记录 |

### 文件导航
| 命令 | 功能 |
|------|------|
| `/cd <path>` | 切换工作目录 |
| `/ls` | 列出当前目录 |
| `/tree [depth]` | 🆕 显示目录树结构 |
| `/pwd` | 显示当前目录 |

### 状态和控制
| 命令 | 功能 |
|------|------|
| `/status` | 查看当前状态 |
| `/stats` | 🆕 显示使用统计 |
| `/stop` | 停止当前任务 |

### 快捷功能
| 命令 | 功能 |
|------|------|
| `/menu` | 显示快捷菜单 |
| `/actions` | 快速编码操作 |
| `/help` | 帮助信息 |

直接发送消息即可与 Claude Code 交互。

> 🎉 **新增功能**: 智能消息分片、进度提示、错误恢复、活动追踪等！详见 `OPTIMIZATION_SUMMARY.md`

## Web Dashboard

访问 `http://your_server:8000` 查看：

- **Dashboard**: 总览统计
- **Sessions**: 会话历史
- **Memory**: 编辑 AI 记忆文件
- **Settings**: 查看配置

## 记忆系统

参考 clawdbot 设计，使用 markdown 文件管理 AI 记忆：

```
workspace/
├── SOUL.md      # AI 人格、语气、行为边界
├── USER.md      # 用户偏好，自动更新
├── AGENTS.md    # 可用代理配置
├── TOOLS.md     # 工具使用说明
├── memory/      # 长期记忆片段
└── sessions/    # 会话记录
```

## 配置说明

### 核心配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 必填 |
| `ALLOWED_USERS` | 允许的用户 ID (逗号分隔) | 空 (允许所有) |
| `APPROVED_DIRECTORY` | 允许访问的项目目录 | ~/projects |
| `CLAUDE_CLI_PATH` | Claude CLI 路径 | claude |
| `CLAUDE_TIMEOUT` | 执行超时 (秒) | 300 |
| `CLAUDE_MAX_TURNS` | 最大对话轮数 | 50 |

### 服务配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `API_HOST` | API 监听地址 | 0.0.0.0 |
| `API_PORT` | API 端口 | 8000 |
| `RATE_LIMIT_REQUESTS` | 速率限制请求数 | 10 |
| `RATE_LIMIT_WINDOW` | 速率限制窗口 (秒) | 60 |

### 性能优化 🆕
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MAX_CONCURRENT_SESSIONS` | 每用户最大并发会话 | 5 |
| `SESSION_TIMEOUT_MINUTES` | 会话超时时间 (分钟) | 120 |
| `MAX_MESSAGE_HISTORY` | 最大消息历史数 | 100 |
| `AUTO_SAVE_SESSIONS` | 自动保存会话 | true |

## API 文档

启动服务后访问 `http://your_server:8000/docs` 查看 Swagger API 文档。

## License

MIT

## 致谢

- [moltbot/clawdbot](https://github.com/moltbot/moltbot) - 记忆系统设计参考
- [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) - Telegram 集成参考
