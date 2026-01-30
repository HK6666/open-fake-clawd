#!/bin/bash

# ccBot 一键部署脚本
# Usage: ./deploy.sh

set -e

echo "======================================"
echo "  ccBot - 一键部署脚本"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}错误: $1 未安装${NC}"
        exit 1
    fi
}

# 检查依赖
echo -e "\n${YELLOW}[1/6] 检查依赖...${NC}"
check_command python3
check_command pip3
check_command node
check_command npm

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python 版本: $PYTHON_VERSION"

NODE_VERSION=$(node -v)
echo "  Node.js 版本: $NODE_VERSION"

# 检查 Claude CLI
if command -v claude &> /dev/null; then
    echo -e "  Claude CLI: ${GREEN}已安装${NC}"
else
    echo -e "  Claude CLI: ${RED}未找到${NC}"
    echo "  请先安装 Claude Code CLI: https://docs.anthropic.com/claude-code"
fi

# 配置环境变量
echo -e "\n${YELLOW}[2/6] 配置环境变量...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  已创建 .env 文件，请编辑配置:"
    echo -e "  ${RED}nano .env${NC}"
    echo ""
    echo "  必须配置的项目:"
    echo "  - TELEGRAM_BOT_TOKEN: 从 @BotFather 获取"
    echo "  - ALLOWED_USERS: 你的 Telegram User ID"
    echo "  - APPROVED_DIRECTORY: 允许访问的项目目录"
    echo ""
    read -p "配置完成后按 Enter 继续..."
else
    echo "  .env 文件已存在"
fi

# 创建虚拟环境并安装 Python 依赖
echo -e "\n${YELLOW}[3/6] 安装 Python 依赖...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -e . --quiet
echo "  Python 依赖安装完成"

# 构建前端
echo -e "\n${YELLOW}[4/6] 构建前端...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    npm install --silent
fi
npm run build --silent
cd ..
echo "  前端构建完成"

# 初始化工作空间
echo -e "\n${YELLOW}[5/6] 初始化工作空间...${NC}"
mkdir -p workspace/memory workspace/sessions
echo "  工作空间初始化完成"

# 启动服务
echo -e "\n${YELLOW}[6/6] 启动服务...${NC}"
echo ""
echo "======================================"
echo -e "${GREEN}部署完成!${NC}"
echo "======================================"
echo ""
echo "启动命令:"
echo "  source venv/bin/activate"
echo "  python -m backend.main"
echo ""
echo "或使用后台运行:"
echo "  nohup python -m backend.main > ccbot.log 2>&1 &"
echo ""
echo "Web Dashboard: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""

read -p "是否立即启动服务? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python -m backend.main
fi
