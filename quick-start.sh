#!/bin/bash
# ccBot 快速开始脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     ccBot 自动部署快速设置向导       ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# 检查前置条件
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git not found. Please install Git first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met!${NC}"
echo ""

# 选择部署方式
echo -e "${BLUE}🎯 Choose your deployment method:${NC}"
echo ""
echo "1) Manual deployment (run ./deploy.sh when needed)"
echo "2) Git Hooks (auto-deploy after 'git pull')"
echo "3) GitHub Actions (auto-deploy on push to GitHub)"
echo "4) Webhook Server (auto-deploy via webhook)"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo -e "${YELLOW}📦 Setting up manual deployment...${NC}"
        
        if [ ! -f .env ]; then
            echo -e "${RED}❌ .env file not found!${NC}"
            read -p "Create .env from template? (y/n): " create_env
            if [ "$create_env" = "y" ]; then
                if [ -f .env.example ]; then
                    cp .env.example .env
                    echo -e "${GREEN}✅ .env created. Please edit it before deploying.${NC}"
                    exit 0
                else
                    echo -e "${RED}❌ .env.example not found. Please create .env manually.${NC}"
                    exit 1
                fi
            else
                exit 1
            fi
        fi
        
        echo -e "${YELLOW}🚀 Running deployment...${NC}"
        ./deploy.sh
        
        echo ""
        echo -e "${GREEN}✅ Manual deployment complete!${NC}"
        echo -e "${BLUE}ℹ️  To redeploy later, run: ./deploy.sh${NC}"
        ;;
        
    2)
        echo -e "${YELLOW}🔧 Setting up Git Hooks...${NC}"
        ./setup-git-hooks.sh
        
        echo ""
        echo -e "${GREEN}✅ Git Hooks installed!${NC}"
        echo -e "${BLUE}ℹ️  Now 'git pull' will auto-deploy.${NC}"
        
        read -p "Deploy now? (y/n): " deploy_now
        if [ "$deploy_now" = "y" ]; then
            ./deploy.sh
        fi
        ;;
        
    3)
        echo -e "${YELLOW}🔧 Setting up GitHub Actions...${NC}"
        echo ""
        echo "GitHub Actions workflow file already created at:"
        echo "  .github/workflows/deploy.yml"
        echo ""
        echo "Next steps:"
        echo "1. Generate SSH key pair:"
        echo "   ssh-keygen -t ed25519 -C 'github-actions' -f ~/.ssh/github_actions"
        echo ""
        echo "2. Add public key to server:"
        echo "   ssh-copy-id -i ~/.ssh/github_actions.pub user@your-server"
        echo ""
        echo "3. Add secrets to GitHub (Settings → Secrets):"
        echo "   - SERVER_HOST: your server IP"
        echo "   - SERVER_USER: SSH username"
        echo "   - SSH_PRIVATE_KEY: content of ~/.ssh/github_actions"
        echo "   - DEPLOY_PATH: $(pwd)"
        echo ""
        echo "4. Push code to GitHub:"
        echo "   git push origin main"
        echo ""
        echo -e "${BLUE}📖 See DEPLOYMENT.md for detailed instructions.${NC}"
        ;;
        
    4)
        echo -e "${YELLOW}🔧 Setting up Webhook Server...${NC}"
        
        read -p "Install as systemd service? (recommended) (y/n): " install_service
        
        if [ "$install_service" = "y" ]; then
            ./install-webhook-service.sh
        else
            echo ""
            echo "To start webhook server manually:"
            echo "  export WEBHOOK_SECRET='your-secret-token'"
            echo "  python3 webhook-server.py"
            echo ""
            echo "Configure your Git webhook:"
            echo "  URL: http://$(hostname -I | awk '{print $1}'):9000/webhook"
            echo "  Secret: (use the same as WEBHOOK_SECRET)"
            echo ""
            echo -e "${BLUE}📖 See DEPLOYMENT.md for detailed instructions.${NC}"
        fi
        ;;
        
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✨ Setup complete!${NC}"
echo -e "${BLUE}📖 For more information, see DEPLOYMENT.md${NC}"
