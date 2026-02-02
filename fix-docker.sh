#!/bin/bash
# 修复 Docker 部署问题

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔧 Fixing Docker deployment issues...${NC}"

# 1. 停止容器
echo -e "${YELLOW}📦 Stopping containers...${NC}"
docker-compose down 2>/dev/null || true

# 2. 修复 docker-compose.yml (移除 version)
echo -e "${YELLOW}📝 Updating docker-compose.yml...${NC}"
if grep -q "^version:" docker-compose.yml; then
    sed -i '/^version:/d' docker-compose.yml
    echo -e "${GREEN}✅ Removed obsolete 'version' field${NC}"
fi

# 3. 创建目录结构
echo -e "${YELLOW}📁 Creating workspace directories...${NC}"
mkdir -p workspace/memory workspace/sessions

# 4. 设置权限（容器内用户 UID=1000）
echo -e "${YELLOW}🔐 Setting workspace permissions...${NC}"
if [ "$(id -u)" -eq 0 ]; then
    chown -R 1000:1000 workspace
    echo -e "${GREEN}✅ Set owner to UID 1000${NC}"
else
    if sudo chown -R 1000:1000 workspace 2>/dev/null; then
        echo -e "${GREEN}✅ Set owner to UID 1000${NC}"
    else
        echo -e "${YELLOW}⚠️  Cannot use sudo, setting 777 permissions instead${NC}"
        chmod -R 777 workspace
    fi
fi
chmod -R 755 workspace

# 5. 创建数据库文件（如果不存在）
if [ ! -f workspace/ccbot.db ]; then
    echo -e "${YELLOW}📊 Creating database file...${NC}"
    touch workspace/ccbot.db
    if [ "$(id -u)" -eq 0 ]; then
        chown 1000:1000 workspace/ccbot.db
    else
        sudo chown 1000:1000 workspace/ccbot.db 2>/dev/null || chmod 666 workspace/ccbot.db
    fi
    echo -e "${GREEN}✅ Database file created${NC}"
fi

# 6. 清理旧的数据库文件（如果在根目录）
if [ -f ccbot.db ]; then
    echo -e "${YELLOW}🗑️  Moving old database file...${NC}"
    if [ ! -f workspace/ccbot.db ]; then
        mv ccbot.db workspace/ccbot.db
        echo -e "${GREEN}✅ Moved ccbot.db to workspace/${NC}"
    else
        echo -e "${YELLOW}⚠️  Backup old database as ccbot.db.backup${NC}"
        mv ccbot.db ccbot.db.backup
    fi
fi

# 7. 重新构建并启动
echo -e "${YELLOW}🚀 Rebuilding and starting containers...${NC}"
docker-compose build --no-cache
docker-compose up -d

# 8. 等待启动
echo -e "${YELLOW}⏳ Waiting for containers to start...${NC}"
sleep 8

# 9. 检查状态
echo -e "${YELLOW}📊 Checking container status...${NC}"
docker-compose ps

echo ""
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Deployment fixed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📝 View logs:${NC}"
    echo "   docker-compose logs -f"
    echo ""
    echo -e "${YELLOW}🌐 Dashboard:${NC}"
    echo "   http://your-server:14532"
else
    echo -e "${RED}❌ Container failed to start. Check logs:${NC}"
    echo "   docker-compose logs"
fi
