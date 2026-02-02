#!/bin/bash
# 设置 Git Hooks 实现自动部署

set -e

echo "🔧 Setting up Git Hooks for auto-deployment"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查是否在 Git 仓库中
if [ ! -d .git ]; then
    echo -e "${RED}❌ Not a Git repository. Run 'git init' first.${NC}"
    exit 1
fi

# 创建 post-merge hook（本地仓库，当 git pull 后自动执行）
echo -e "${YELLOW}📝 Creating post-merge hook...${NC}"
cat > .git/hooks/post-merge << 'HOOK_EOF'
#!/bin/bash
# Post-merge hook: 自动重新部署

echo "🔄 Git merge detected, triggering deployment..."

# 检查是否有 Docker 相关文件变更
if git diff-tree -r --name-only --no-commit-id HEAD | grep -qE '^(Dockerfile|docker-compose.yml|requirements.txt|frontend/package.json)'; then
    echo "📦 Docker configuration changed, rebuilding..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
else
    echo "🔄 Restarting containers with latest code..."
    docker-compose restart
fi

echo "✅ Deployment completed!"
HOOK_EOF

chmod +x .git/hooks/post-merge

echo -e "${GREEN}✅ Post-merge hook installed!${NC}"
echo -e "${YELLOW}   Now when you run 'git pull', deployment will happen automatically.${NC}"

# 如果用户想要服务器端 hook（bare repository）
echo ""
echo -e "${YELLOW}📌 For server-side auto-deployment (bare repository):${NC}"
echo ""
echo "1. On your server, create a bare repository:"
echo "   git clone --bare <your-repo> /path/to/ccbot.git"
echo ""
echo "2. In the bare repository, create post-receive hook:"
echo "   vim /path/to/ccbot.git/hooks/post-receive"
echo ""
echo "3. Add this content:"
echo ""
cat << 'SERVER_HOOK'
#!/bin/bash
# Post-receive hook for bare repository

# 工作目录（实际部署目录）
DEPLOY_DIR="/path/to/ccbot-deploy"

echo "🔄 Received push, deploying to $DEPLOY_DIR"

# 进入工作目录
cd $DEPLOY_DIR || exit 1

# 拉取最新代码
git pull origin main

# 重新部署
./deploy.sh

echo "✅ Deployment completed!"
SERVER_HOOK
echo ""
echo "4. Make it executable:"
echo "   chmod +x /path/to/ccbot.git/hooks/post-receive"
echo ""
echo "5. On your local machine, add the remote:"
echo "   git remote add production ssh://user@your-server/path/to/ccbot.git"
echo ""
echo "6. Push to deploy:"
echo "   git push production main"
echo ""
echo -e "${GREEN}Done! Your Git hooks are ready.${NC}"
