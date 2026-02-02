#!/bin/bash
# 修复 Docker 部署问题

set -e

echo "🔧 Fixing Docker deployment issues..."

# 1. 停止容器
echo "📦 Stopping containers..."
docker-compose down 2>/dev/null || true

# 2. 修复 docker-compose.yml (移除 version)
echo "📝 Updating docker-compose.yml..."
if grep -q "^version:" docker-compose.yml; then
    sed -i '/^version:/d' docker-compose.yml
    echo "✅ Removed obsolete 'version' field"
fi

# 3. 创建目录结构
echo "📁 Creating workspace directories..."
mkdir -p workspace/memory workspace/sessions

# 4. 设置权限（容器内用户 UID=1000）
echo "🔐 Setting permissions..."
if [ "$(id -u)" -eq 0 ]; then
    chown -R 1000:1000 workspace
else
    sudo chown -R 1000:1000 workspace
fi
chmod -R 755 workspace

# 5. 重新构建并启动
echo "🚀 Rebuilding and starting containers..."
docker-compose build --no-cache
docker-compose up -d

# 6. 等待启动
echo "⏳ Waiting for containers to start..."
sleep 5

# 7. 检查状态
echo "📊 Checking container status..."
docker-compose ps

echo ""
echo "✅ Deployment fixed!"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f"
