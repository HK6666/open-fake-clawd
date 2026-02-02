#!/bin/bash
# ccBot 部署脚本

set -e  # 遇到错误立即退出

echo "🚀 Starting ccBot deployment..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found. Please create it first.${NC}"
    exit 1
fi

# 停止旧容器
echo -e "${YELLOW}📦 Stopping old containers...${NC}"
docker-compose down

# 创建必要的目录
echo -e "${YELLOW}📁 Creating workspace directories...${NC}"
mkdir -p workspace/memory workspace/sessions

# 设置权限（容器内用户 UID=1000）
echo -e "${YELLOW}🔐 Setting workspace permissions...${NC}"
if [ "$(id -u)" -eq 0 ]; then
    chown -R 1000:1000 workspace
    chmod -R 755 workspace
else
    sudo chown -R 1000:1000 workspace 2>/dev/null || chmod -R 777 workspace
fi

# 拉取最新代码（如果在 Git 仓库中）
if [ -d .git ]; then
    echo -e "${YELLOW}🔄 Pulling latest code from Git...${NC}"
    git pull origin main || git pull origin master || echo "Git pull failed or not configured"
fi

# 构建镜像
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker-compose build --no-cache

# 清理旧镜像
echo -e "${YELLOW}🧹 Cleaning up old images...${NC}"
docker image prune -f

# 启动容器
echo -e "${YELLOW}🚀 Starting containers...${NC}"
docker-compose up -d

# 等待容器启动
echo -e "${YELLOW}⏳ Waiting for containers to be healthy...${NC}"
sleep 5

# 检查容器状态
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ ccBot deployed successfully!${NC}"
    echo ""
    echo "📊 Container status:"
    docker-compose ps
    echo ""
    echo "📝 View logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🌐 Dashboard should be available at:"
    echo "   http://your-server-ip:14532"
else
    echo -e "${RED}❌ Deployment failed. Check logs:${NC}"
    docker-compose logs
    exit 1
fi
