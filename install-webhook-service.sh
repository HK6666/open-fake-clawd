#!/bin/bash
# 安装 Webhook 服务为 systemd 服务

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 获取当前目录
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo -e "${YELLOW}🔧 Installing ccBot Webhook Service${NC}"

# 提示输入 webhook secret
read -p "Enter webhook secret token (or press Enter to generate random): " SECRET
if [ -z "$SECRET" ]; then
    SECRET=$(openssl rand -hex 32)
    echo -e "${GREEN}✅ Generated random secret: $SECRET${NC}"
    echo -e "${YELLOW}   Save this for your Git webhook configuration!${NC}"
fi

# 创建 systemd 服务文件
echo -e "${YELLOW}📝 Creating systemd service file...${NC}"

sudo tee /etc/systemd/system/ccbot-webhook.service > /dev/null << SERVICE_EOF
[Unit]
Description=ccBot Webhook Auto-Deploy Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="WEBHOOK_SECRET=$SECRET"
ExecStart=/usr/bin/python3 $CURRENT_DIR/webhook-server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# 重新加载 systemd
echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
sudo systemctl daemon-reload

# 启动服务
echo -e "${YELLOW}🚀 Starting webhook service...${NC}"
sudo systemctl start ccbot-webhook

# 设置开机自启
echo -e "${YELLOW}✅ Enabling service on boot...${NC}"
sudo systemctl enable ccbot-webhook

# 检查状态
echo -e "${GREEN}✅ Webhook service installed successfully!${NC}"
echo ""
echo "📊 Service status:"
sudo systemctl status ccbot-webhook --no-pager

echo ""
echo -e "${GREEN}📌 Webhook Configuration:${NC}"
echo "   URL: http://$(hostname -I | awk '{print $1}'):9000/webhook"
echo "   Secret: $SECRET"
echo ""
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo "   View logs:    sudo journalctl -u ccbot-webhook -f"
echo "   Stop service: sudo systemctl stop ccbot-webhook"
echo "   Start service: sudo systemctl start ccbot-webhook"
echo "   Restart:      sudo systemctl restart ccbot-webhook"
echo "   Status:       sudo systemctl status ccbot-webhook"
