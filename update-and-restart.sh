#!/bin/bash
# 更新代码并重新构建镜像

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Updating and rebuilding with GLM support...${NC}"

# 1. 拉取最新代码
echo -e "${YELLOW}📥 Pulling latest code...${NC}"
git pull origin main || echo "Already up to date"

# 2. 停止容器
echo -e "${YELLOW}🛑 Stopping containers...${NC}"
docker-compose down

# 3. 重新构建镜像（无缓存）
echo -e "${YELLOW}🔨 Rebuilding Docker image with new code...${NC}"
docker-compose build --no-cache

# 4. 启动容器
echo -e "${YELLOW}🚀 Starting containers...${NC}"
docker-compose up -d

# 5. 等待启动
echo -e "${YELLOW}⏳ Waiting for startup...${NC}"
sleep 8

# 6. 查看日志
echo -e "${YELLOW}📋 Recent logs:${NC}"
docker-compose logs --tail=30

echo ""
echo -e "${GREEN}✅ Update complete!${NC}"
echo ""
echo "Check status with: docker-compose ps"
echo "View logs with: docker-compose logs -f"
