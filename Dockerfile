# ccBot Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml .
COPY frontend/package.json frontend/

# 安装 Python 依赖
RUN pip install --no-cache-dir -e .

# 安装前端依赖并构建
WORKDIR /app/frontend
RUN npm install --silent
COPY frontend/ .
RUN npm run build

# 复制后端代码
WORKDIR /app
COPY backend/ backend/
COPY workspace/ workspace/

# 创建必要目录
RUN mkdir -p workspace/memory workspace/sessions

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "backend.main"]
