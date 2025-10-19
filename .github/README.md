# GitHub 自动部署说明

本项目支持通过 GitHub 自动部署到服务器，有两种方案可选。

## 🚀 方案对比

| 特性 | GitHub Actions | Webhook + 脚本 |
|------|----------------|----------------|
| **配置难度** | ⭐⭐⭐ 简单 | ⭐⭐ 中等 |
| **可靠性** | ⭐⭐⭐ 高 | ⭐⭐ 中等 |
| **执行速度** | 快（直接 SSH） | 较快（需要轮询） |
| **日志查看** | GitHub Actions 页面 | 服务器日志文件 |
| **网络要求** | 服务器需开放 SSH (22) | 服务器需开放 HTTP (80) |
| **推荐场景** | ✅ 生产环境 | 开发测试环境 |

## 方案A：GitHub Actions（推荐）

### 优点
- ✅ 配置简单，只需设置 GitHub Secrets
- ✅ 可靠性高，直接在 GitHub 基础设施上运行
- ✅ 日志清晰，可在 GitHub Actions 页面查看
- ✅ 支持手动触发
- ✅ 失败时可以重新运行

### 配置步骤

1. **在服务器生成 SSH 密钥**
   ```bash
   ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy
   cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
   cat ~/.ssh/github_deploy  # 复制私钥
   ```

2. **在 GitHub 配置 Secrets**
   
   进入仓库 `Settings` → `Secrets and variables` → `Actions`，添加：
   - `SERVER_HOST`: 服务器 IP 或域名
   - `SERVER_USER`: SSH 用户名
   - `SERVER_SSH_KEY`: SSH 私钥（完整内容）
   - `SERVER_PORT`: SSH 端口（可选，默认 22）

3. **完成！**
   
   现在每次推送代码到 `main` 分支，GitHub Actions 会自动：
   - SSH 连接到服务器
   - 拉取最新代码
   - 重新构建 Docker 镜像
   - 重启容器
   - 验证健康状态

### 触发条件

自动触发（修改以下文件时）：
- `src/**`（源代码）
- `config/**`（配置文件）
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `.github/workflows/deploy.yml`

手动触发：
- 在 GitHub Actions 页面点击 "Run workflow"

### 查看部署日志

访问：`https://github.com/YOUR_USERNAME/YOUR_REPO/actions`

---

## 方案B：Webhook + 自动监听脚本

### 优点
- ✅ 不需要开放 SSH 端口
- ✅ 容器内自动拉取代码
- ✅ 可以处理配置文件变更

### 缺点
- ⚠️ 需要运行额外的守护进程
- ⚠️ 依赖服务器端轮询检测
- ⚠️ 配置相对复杂

### 配置步骤

1. **配置 GitHub Webhook**
   
   进入仓库 `Settings` → `Webhooks` → `Add webhook`：
   - Payload URL: `http://your-server-domain/webhook`
   - Content type: `application/json`
   - Secret: 填入 `config.ini` 中的 `webhook_secret`
   - Events: 选择 `Just the push event`

2. **在服务器安装自动部署守护进程**
   ```bash
   cd /opt/docker-apps/clash-config-manager
   chmod +x scripts/deploy.sh scripts/auto_deploy.sh
   sudo scripts/auto_deploy.sh install
   sudo systemctl start clash-auto-deploy
   sudo systemctl enable clash-auto-deploy
   ```

3. **查看日志**
   ```bash
   tail -f /var/log/clash-auto-deploy.log
   ```

### 工作原理

```
GitHub 推送代码
   ↓
发送 Webhook 到服务器
   ↓
容器内 webhook_server.py 接收
   ↓
拉取最新代码 (git pull)
   ↓
创建标记文件 .update_required
   ↓
宿主机守护进程 auto_deploy.sh 检测标记
   ↓
执行 deploy.sh 重新构建并重启容器
```

---

## 📝 手动部署

如果不想使用自动部署，可以手动运行部署脚本：

```bash
cd /opt/docker-apps/clash-config-manager

# 完整部署（拉取代码 + 重新构建 + 重启）
bash scripts/deploy.sh deploy

# 快速重启（仅重启容器）
bash scripts/deploy.sh restart

# 查看日志
bash scripts/deploy.sh logs

# 健康检查
bash scripts/deploy.sh health
```

---

## 🐛 故障排除

### GitHub Actions 部署失败

**检查 SSH 连接**：
```bash
# 在本地测试 SSH 连接
ssh -i ~/.ssh/github_deploy user@your-server

# 检查服务器防火墙
sudo ufw status
sudo ufw allow 22/tcp
```

**检查权限**：
```bash
# 确保用户有 Docker 权限
sudo usermod -aG docker $USER
newgrp docker
```

**查看 Actions 日志**：
- 访问 GitHub Actions 页面查看详细错误信息

### Webhook 不触发

**检查 Webhook 配置**：
- 进入 GitHub `Settings` → `Webhooks`
- 查看 "Recent Deliveries" 是否有请求
- 检查响应状态码

**检查容器日志**：
```bash
docker logs -f clash-config-manager
```

**测试 Webhook 端点**：
```bash
curl http://your-server/webhook
```

### 容器无法拉取代码

**检查 Git 配置**：
```bash
# 进入容器
docker exec -it clash-config-manager bash

# 测试 git 命令
git status
git pull origin main
```

**权限问题**：
确保 `docker-compose.yml` 中挂载了项目目录：
```yaml
volumes:
  - .:/app:rw
```

---

## 📚 更多信息

详细部署文档请参考：
- [DEPLOY.md](../DEPLOY.md) - 完整部署指南
- [README.md](../README.md) - 项目说明

---

## 🎯 推荐配置

**生产环境**：
- ✅ 使用 GitHub Actions
- ✅ 配置 SSH 密钥认证
- ✅ 在 GitHub 配置 Secrets
- ✅ 监控 Actions 执行日志

**开发环境**：
- 可以使用 Webhook + 脚本
- 或者直接手动部署

---

**祝部署顺利！** 🚀

