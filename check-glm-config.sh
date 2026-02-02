#!/bin/bash
# 检查GLM配置

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔍 Checking GLM Configuration...${NC}"
echo ""

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# 检查LLM_PROVIDER
PROVIDER=$(grep "^LLM_PROVIDER=" .env | cut -d'=' -f2)
echo -e "LLM_PROVIDER: ${YELLOW}${PROVIDER}${NC}"

# 检查GLM_API_KEY
API_KEY=$(grep "^GLM_API_KEY=" .env | cut -d'=' -f2)
if [ -z "$API_KEY" ]; then
    echo -e "GLM_API_KEY: ${RED}❌ Not set${NC}"
    echo ""
    echo -e "${YELLOW}Please add to .env file:${NC}"
    echo "GLM_API_KEY=your_id.your_secret"
    echo ""
    echo -e "${YELLOW}Get your API key from:${NC}"
    echo "https://bigmodel.cn/usercenter/proj-mgmt/apikeys"
    exit 1
fi

# 检查API key格式（应该包含一个点）
if [[ $API_KEY == *.* ]]; then
    # 隐藏显示
    MASKED_KEY="${API_KEY:0:10}...${API_KEY: -10}"
    echo -e "GLM_API_KEY: ${GREEN}✅ ${MASKED_KEY}${NC}"
    
    # 分割并检查两部分
    IFS='.' read -r ID SECRET <<< "$API_KEY"
    echo -e "  - ID part length: ${#ID}"
    echo -e "  - Secret part length: ${#SECRET}"
else
    echo -e "GLM_API_KEY: ${RED}❌ Invalid format (missing '.')${NC}"
    echo ""
    echo -e "${YELLOW}Expected format:${NC}"
    echo "GLM_API_KEY={id}.{secret}"
    echo ""
    echo -e "${YELLOW}Example (not real):${NC}"
    echo "GLM_API_KEY=1234567890abcdef.ABCDEF1234567890ABCDEF1234567890"
    exit 1
fi

# 检查GLM_MODEL
MODEL=$(grep "^GLM_MODEL=" .env | cut -d'=' -f2)
echo -e "GLM_MODEL: ${YELLOW}${MODEL:-glm-4.7 (default)}${NC}"

echo ""
echo -e "${GREEN}✅ Configuration looks good!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. docker-compose down"
echo "2. docker-compose build --no-cache"
echo "3. docker-compose up -d"
