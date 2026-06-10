# ============================================
# Stage 1: 前端构建阶段 - 基于 Node.js 构建 React 应用
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /app

# 复制前端依赖文件
COPY frontend/package*.json ./
RUN npm ci

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# ============================================
# Stage 2: 后端运行阶段 - 基于 Python 运行 FastAPI 服务
# ============================================
FROM python:3.11-slim

LABEL maintainer="emo-transfer"
LABEL description="EmoTransfer AI Video Processing Platform"

# 安装系统依赖: ffmpeg (视频处理) 和其他基础工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码
COPY backend/ ./backend/

# 复制前端构建产物 (从 Stage 1)
COPY --from=frontend-builder /app/dist ./static

# 复制项目根目录的脚本、数据目录
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY VectCutAPI/ ./VectCutAPI/

# 创建必要的目录
RUN mkdir -p logs uploads static data/outputs data/generated_assets

# 环境变量配置
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
