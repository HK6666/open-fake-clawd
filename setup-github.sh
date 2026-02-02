#!/bin/bash
# GitHub 配置助手

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   ccBot GitHub 配置助手              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 检查Git状态
if [ -z "$(git status --porcelain)" ]; then
    echo -e "${GREEN}✅ 工作目录干净${NC}"
else
    echo -e "${YELLOW}📝 有未提交的改动${NC}"
    echo ""
    read -p "提交并推送所有改动？(y/n): " commit_changes
    
    if [ "$commit_changes" = "y" ]; then
        git add .
        echo "请输入提交信息（或按回车使用默认）："
        read -r commit_msg
        
        if [ -z "$commit_msg" ]; then
            commit_msg="feat: Add Docker deployment and auto-update system"
        fi
        
        git commit -m "$commit_msg"
        git push origin main
        
        echo -e "${GREEN}✅ 代码已推送到 GitHub${NC}"
    fi
fi

echo ""
echo -e "${BLUE}选择你的部署方案：${NC}"
echo ""
echo "1) Git Hooks - 简单，手动 git pull（推荐个人）"
echo "2) GitHub Actions - 全自动（推荐团队）"
echo "3) Webhook - 实时监听（高级）"
echo ""
read -p "选择 (1-3): " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}✅ 已选择: Git Hooks${NC}"
        echo ""
        echo -e "${YELLOW}📋 在服务器上运行以下命令：${NC}"
        echo ""
        echo "  git clone https://github.com/HK6666/opne-fake-clawd.git ccBot"
        echo "  cd ccBot"
        echo "  cp .env.example .env"
        echo "  vim .env  # 编辑配置"
        echo "  ./setup-git-hooks.sh"
        echo "  ./deploy.sh"
        echo ""
        echo -e "${BLUE}ℹ️  以后更新：${NC}"
        echo "  git pull origin main  # 自动触发部署"
        echo ""
        ;;
        
    2)
        echo ""
        echo -e "${GREEN}✅ 已选择: GitHub Actions${NC}"
        echo ""
        echo -e "${YELLOW}步骤1: 生成SSH密钥${NC}"
        
        if [ ! -f ~/.ssh/ccbot_deploy ]; then
            read -p "现在生成SSH密钥？(y/n): " gen_key
            if [ "$gen_key" = "y" ]; then
                ssh-keygen -t ed25519 -C "github-actions-ccbot" -f ~/.ssh/ccbot_deploy -N ""
                echo -e "${GREEN}✅ 密钥已生成${NC}"
            fi
        fi
        
        echo ""
        echo -e "${YELLOW}步骤2: 复制公钥到服务器${NC}"
        echo ""
        echo "运行以下命令（替换your-server）："
        echo ""
        echo -e "${BLUE}cat ~/.ssh/ccbot_deploy.pub | ssh your-user@your-server 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'${NC}"
        echo ""
        
        echo -e "${YELLOW}步骤3: 获取私钥内容${NC}"
        echo ""
        if [ -f ~/.ssh/ccbot_deploy ]; then
            echo "复制以下内容作为 SSH_PRIVATE_KEY："
            echo ""
            echo "----------------------------------------"
            cat ~/.ssh/ccbot_deploy
            echo "----------------------------------------"
        fi
        echo ""
        
        echo -e "${YELLOW}步骤4: 在GitHub设置Secrets${NC}"
        echo ""
        echo "打开: https://github.com/HK6666/opne-fake-clawd/settings/secrets/actions"
        echo ""
        echo "添加以下 Secrets："
        echo "  - SERVER_HOST: 服务器IP"
        echo "  - SERVER_USER: SSH用户名"
        echo "  - SSH_PRIVATE_KEY: (上面的私钥内容)"
        echo "  - DEPLOY_PATH: 服务器上的项目路径"
        echo ""
        echo -e "${GREEN}✅ 配置完成后，git push 将自动部署${NC}"
        ;;
        
    3)
        echo ""
        echo -e "${GREEN}✅ 已选择: Webhook${NC}"
        echo ""
        echo -e "${YELLOW}步骤1: 在服务器安装webhook服务${NC}"
        echo ""
        echo "SSH到服务器后运行："
        echo "  ./install-webhook-service.sh"
        echo ""
        echo -e "${YELLOW}步骤2: 在GitHub设置Webhook${NC}"
        echo ""
        echo "打开: https://github.com/HK6666/opne-fake-clawd/settings/hooks"
        echo ""
        echo "点击 'Add webhook'，填写："
        echo "  - Payload URL: http://服务器IP:9000/webhook"
        echo "  - Content type: application/json"
        echo "  - Secret: (服务器上生成的token)"
        echo "  - Events: Just the push event"
        echo ""
        echo -e "${GREEN}✅ 配置完成后，git push 将自动部署${NC}"
        ;;
        
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}📖 详细文档: DEPLOYMENT.md${NC}"
