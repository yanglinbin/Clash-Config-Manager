# Clash 配置管理器 - Docker 镜像
# 多阶段构建，优化镜像大小

# ==================== 构建阶段 ====================
FROM python:3.9-slim AS builder

# 设置工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt .

# 安装依赖到临时目录
RUN pip install --no-cache-dir --user -r requirements.txt

# ==================== 运行阶段 ====================
FROM python:3.9-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    APP_HOME=/app

# 安装必要的系统工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tzdata && \
    rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -m -s /bin/bash appuser

# 设置工作目录
WORKDIR ${APP_HOME}

# 从构建阶段复制Python依赖
COPY --from=builder /root/.local /home/appuser/.local

# 复制应用代码
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/rules.yaml ./config/rules.yaml
COPY --chown=appuser:appuser config/rules.schema.json ./config/rules.schema.json
# 注意：config.ini 由用户通过 docker-compose.yml 卷挂载提供

# 创建必要的目录并设置权限
RUN mkdir -p logs output backups config && \
    chown -R appuser:appuser ${APP_HOME}

# 切换到非root用户
USER appuser

# 设置Python路径
ENV PATH="/home/appuser/.local/bin:${PATH}"

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/status || exit 1

# 启动应用
CMD ["python", "src/app.py"]

