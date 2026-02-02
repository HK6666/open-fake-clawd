#!/bin/bash
# ccBot Git 自动更新脚本
# 当检测到 Git 仓库有更新时，自动重新部署

set -e

echo "🔄 Git Auto-Update Script"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 获取当前 commit hash
OLD_COMMIT=$(git rev-parse HEAD)

# 拉取最新代码
echo -e "${YELLOW}📥 Fetching latest changes from Git...${NC}"
git fetch origin

# 检查是否有更新
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")
BASE=$(git merge-base @ "$UPSTREAM")

if [ $LOCAL = $REMOTE ]; then
    echo -e "${GREEN}✅ Already up to date. No deployment needed.${NC}"
    exit 0
elif [ $LOCAL = $BASE ]; then
    echo -e "${YELLOW}🆕 New changes detected!${NC}"
    
    # 拉取更新
    git pull origin main || git pull origin master
    
    NEW_COMMIT=$(git rev-parse HEAD)
    
    echo -e "${YELLOW}📋 Changes:${NC}"
    git log --oneline $OLD_COMMIT..$NEW_COMMIT
    
    # 重新部署
    echo -e "${YELLOW}🚀 Redeploying application...${NC}"
    ./deploy.sh
    
    echo -e "${GREEN}✅ Update and deployment completed!${NC}"
elif [ $REMOTE = $BASE ]; then
    echo -e "${RED}⚠️  Local changes detected. Please push or stash them first.${NC}"
    exit 1
else
    echo -e "${RED}⚠️  Diverged. Manual intervention required.${NC}"
    exit 1
fi
