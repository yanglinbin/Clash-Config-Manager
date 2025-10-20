#!/bin/bash
#
# 自动更新脚本 - 从 GitHub Container Registry 拉取新镜像并重启服务
# 由 webhook 触发执行
#

set -e

# ==================== 配置 ====================
PROJECT_DIR="/opt/docker-apps/clash-config-manager"
LOG_FILE="/var/log/clash-config-update.log"
IMAGE_REGISTRY="ghcr.io"
IMAGE_REPO="YOUR_GITHUB_USERNAME/clash-config-manager"

# ==================== 参数 ====================
VERSION="${1:-latest}"
IMAGE="${2:-${IMAGE_REGISTRY}/${IMAGE_REPO}:latest}"

# ==================== 函数 ====================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ==================== 主流程 ====================
log "=========================================="
log "🚀 开始更新流程"
log "版本: $VERSION"
log "镜像: $IMAGE"
log "=========================================="

cd "$PROJECT_DIR" || exit 1

# 1. 拉取最新镜像
log "📦 拉取新镜像..."
if docker pull "$IMAGE" >> "$LOG_FILE" 2>&1; then
    log "✅ 镜像拉取成功"
else
    log "❌ 镜像拉取失败"
    exit 1
fi

# 2. 备份当前配置
log "💾 备份配置文件..."
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r "$PROJECT_DIR/config/"*.{yaml,json,ini} "$BACKUP_DIR/" 2>/dev/null || true
log "✅ 配置已备份到 $BACKUP_DIR"

# 3. 更新 docker-compose.yml 中的镜像
log "📝 更新 docker-compose.yml..."
sed -i "s|image:.*clash-config-manager.*|image: $IMAGE|" docker-compose.yml
log "✅ docker-compose.yml 已更新"

# 4. 重启容器
log "🔄 重启容器..."
if docker-compose up -d >> "$LOG_FILE" 2>&1; then
    log "✅ 容器重启成功"
else
    log "❌ 容器重启失败"
    exit 1
fi

# 5. 等待服务就绪
log "⏳ 等待服务启动..."
sleep 10

# 6. 健康检查
log "🏥 执行健康检查..."
if curl -f http://localhost:8080/status > /dev/null 2>&1; then
    log "✅ 健康检查通过"
else
    log "⚠️  健康检查失败（服务可能仍在启动中）"
fi

# 7. 清理旧镜像
log "🧹 清理旧镜像..."
docker image prune -f >> "$LOG_FILE" 2>&1
log "✅ 清理完成"

log "=========================================="
log "🎉 更新完成！版本: $VERSION"
log "=========================================="

exit 0

