# 部署指南

本文档详细说明如何将 Clash Config Manager 部署到 Ubuntu 24.04 服务器。

---

## 部署架构

```
本地开发 (Windows)
   │
   ├─ 推送代码 → GitHub
   │              │
   │              ├─ GitHub Actions 构建镜像
   │              ├─ 推送到 ghcr.io
   │              └─ 触发 Webhook
   │
   └─ 配置更新 → GitHub Actions → SSH 同步到服务器

服务器 (Ubuntu 24.04)
   │
   ├─ /opt/docker-apps/clash-config-manager  (项目目录)
   ├─ /opt/webhooks                          (Webhook 配置)
   └─ Webhook 服务监听更新 → 自动拉取镜像 → 重启容器
```

---

## 服务器路径规划

| 路径 | 用途 |
|------|------|
| `/opt/docker-apps/clash-config-manager` | 项目主目录 |
| `/opt/docker-apps/clash-config-manager/config` | 配置文件 |
| `/opt/docker-apps/clash-config-manager/logs` | 日志文件 |
| `/opt/docker-apps/clash-config-manager/output` | 生成的配置 |
| `/opt/docker-apps/clash-config-manager/backups` | 备份文件 |
| `/opt/webhooks` | Webhook 配置目录 |
| `/var/log/clash-config-update.log` | 更新日志 |
| `/var/log/webhook.log` | Webhook 日志 |

---

## 第一步：准备服务器环境

### 1.1 安装 Docker

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install -y docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

### 1.2 安装 Webhook

```bash
# 下载 webhook
cd /tmp
wget https://github.com/adnanh/webhook/releases/download/2.8.1/webhook-linux-amd64.tar.gz
tar -xzf webhook-linux-amd64.tar.gz
sudo mv webhook-linux-amd64/webhook /usr/local/bin/
sudo chmod +x /usr/local/bin/webhook

# 验证安装
webhook --version
```

### 1.3 安装必要工具

```bash
sudo apt install -y curl git
```

---

## 第二步：创建项目目录

```bash
# 创建目录结构
sudo mkdir -p /opt/docker-apps/clash-config-manager/{config,logs,output,backups}
sudo mkdir -p /opt/webhooks

# 进入项目目录
cd /opt/docker-apps/clash-config-manager
```

---

## 第三步：下载配置文件

**替换 `YOUR_GITHUB_USERNAME` 为你的 GitHub 用户名**

```bash
# 设置变量
GITHUB_USER="YOUR_GITHUB_USERNAME"
REPO_URL="https://raw.githubusercontent.com/${GITHUB_USER}/clash-config-manager/main"

# 下载 docker-compose.yml
curl -fsSL "${REPO_URL}/docker-compose.yml" -o docker-compose.yml

# 下载配置文件
curl -fsSL "${REPO_URL}/config/config.ini.example" -o config/config.ini.example
curl -fsSL "${REPO_URL}/config/rules.yaml" -o config/rules.yaml
curl -fsSL "${REPO_URL}/config/rules.schema.json" -o config/rules.schema.json

# 下载部署脚本
curl -fsSL "${REPO_URL}/server-deploy/update-from-github.sh" -o update-from-github.sh
curl -fsSL "${REPO_URL}/server-deploy/webhook.service" -o webhook.service
chmod +x update-from-github.sh

# 创建用户配置
cp config/config.ini.example config/config.ini
```

---

## 第四步：配置文件

### 4.1 编辑 config.ini

```bash
nano config/config.ini
```

填入你的订阅链接：
```ini
[subscription]
urls = 
    https://your-subscription-url-1
    https://your-subscription-url-2
```

### 4.2 编辑 docker-compose.yml

```bash
nano docker-compose.yml
```

**重要**：将 `YOUR_GITHUB_USERNAME` 替换为你的 GitHub 用户名：
```yaml
image: ghcr.io/YOUR_GITHUB_USERNAME/clash-config-manager:latest
```

### 4.3 编辑 update-from-github.sh

```bash
nano update-from-github.sh
```

修改以下配置：
```bash
PROJECT_DIR="/opt/docker-apps/clash-config-manager"
IMAGE_REPO="YOUR_GITHUB_USERNAME/clash-config-manager"
```

---

## 第五步：配置 Webhook

### 5.1 生成密钥

```bash
# 生成 Webhook 密钥
WEBHOOK_SECRET=$(openssl rand -base64 32)
echo "WEBHOOK_SECRET: $WEBHOOK_SECRET"

# ⚠️ 保存这个密钥，稍后需要添加到 GitHub Secrets
```

### 5.2 创建 Webhook 配置

```bash
cat > /opt/webhooks/hooks.json <<EOF
[
  {
    "id": "update-clash-config",
    "execute-command": "/opt/docker-apps/clash-config-manager/update-from-github.sh",
    "command-working-directory": "/opt/docker-apps/clash-config-manager",
    "response-message": "Update triggered successfully",
    "pass-arguments-to-command": [
      {
        "source": "payload",
        "name": "version"
      },
      {
        "source": "payload",
        "name": "image"
      }
    ],
    "trigger-rule": {
      "and": [
        {
          "match": {
            "type": "value",
            "value": "Bearer ${WEBHOOK_SECRET}",
            "parameter": {
              "source": "header",
              "name": "Authorization"
            }
          }
        }
      ]
    }
  }
]
EOF
```

### 5.3 安装 Webhook 服务

```bash
# 复制 service 文件
sudo cp webhook.service /etc/systemd/system/

# 重载 systemd
sudo systemctl daemon-reload

# 启动并启用 webhook
sudo systemctl enable webhook
sudo systemctl start webhook

# 检查状态
sudo systemctl status webhook
```

---

## 第六步：配置 SSH（用于配置同步）

### 6.1 生成 SSH 密钥

```bash
# 生成密钥对
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions -N ""

# 添加公钥到 authorized_keys
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 查看私钥（复制保存，稍后用于 GitHub Secret）
cat ~/.ssh/github_actions
```

**⚠️ 保存 SSH 私钥内容，稍后需要添加到 GitHub Secrets**

---

## 第七步：登录 GitHub Container Registry

### 7.1 创建 Personal Access Token

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选权限：`read:packages`, `write:packages`
4. 复制生成的 token

### 7.2 登录 ghcr.io

```bash
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

---

## 第八步：配置防火墙

```bash
# 如果使用 UFW
sudo ufw allow 9000/tcp  # Webhook 端口
sudo ufw allow 8080/tcp  # 应用端口（可选，如果需要外部访问）
sudo ufw reload
```

---

## 第九步：GitHub 配置

### 9.1 修改本地代码

**Windows 本地项目目录**，编辑以下文件：

#### docker-compose.yml
将 `YOUR_GITHUB_USERNAME` 替换为你的用户名

#### server-deploy/update-from-github.sh
```bash
PROJECT_DIR="/opt/docker-apps/clash-config-manager"
IMAGE_REPO="你的用户名/clash-config-manager"
```

### 9.2 设置 GitHub Secrets

访问：`https://github.com/你的用户名/clash-config-manager/settings/secrets/actions`

添加以下 6 个 Secrets：

| Secret 名称 | 值 |
|------------|-----|
| `WEBHOOK_SECRET` | 第五步生成的密钥 |
| `WEBHOOK_URL` | `http://服务器IP:9000/hooks/update-clash-config` |
| `SERVER_SSH_KEY` | 第六步生成的 SSH 私钥 |
| `SERVER_HOST` | 服务器 IP 或域名 |
| `SERVER_USER` | `root` |
| `SERVER_PATH` | `/opt/docker-apps/clash-config-manager` |

---

## 第十步：部署

### 10.1 推送代码

```bash
# Windows 本地项目目录
git add .
git commit -m "chore: 配置部署"
git push origin main
```

### 10.2 发布第一个版本

```bash
# 打标签
git tag v1.0.0
git push --tags

# GitHub Actions 会自动：
# 1. 构建 Docker 镜像
# 2. 推送到 ghcr.io
# 3. 触发服务器 Webhook
# 4. 服务器自动拉取镜像并启动
```

### 10.3 手动启动（如果自动部署未成功）

```bash
# 服务器上执行
cd /opt/docker-apps/clash-config-manager

# 拉取镜像
docker pull ghcr.io/你的用户名/clash-config-manager:latest

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f
```

---

## 验证部署

### 检查服务状态

```bash
# 检查容器
docker compose ps

# 检查日志
docker compose logs -f clash-config-manager

# 检查 Webhook
sudo systemctl status webhook

# 测试 API
curl http://localhost:8080/status
```

### 访问服务

```
http://服务器IP:8080/
```

---

## 日常使用

### 更新代码

```bash
# 本地修改代码后
git commit -am "feat: 新功能"
git tag v1.0.1
git push --tags

# 服务器会在 2-3 分钟后自动更新
```

### 更新配置

```bash
# 本地修改 config/rules.yaml
git commit -am "chore: 更新规则"
git push

# 服务器会在 30 秒内自动同步并重启
```

### 手动更新

```bash
# 服务器上执行
cd /opt/docker-apps/clash-config-manager
docker pull ghcr.io/你的用户名/clash-config-manager:latest
docker compose up -d
```

---

## 监控和维护

### 查看日志

```bash
# 应用日志
tail -f /opt/docker-apps/clash-config-manager/logs/app.log

# Webhook 日志
sudo journalctl -u webhook -f
tail -f /var/log/webhook.log

# 更新日志
tail -f /var/log/clash-config-update.log

# 容器日志
docker compose logs -f
```

### 重启服务

```bash
# 重启容器
docker compose restart

# 重启 Webhook
sudo systemctl restart webhook
```

### 备份配置

```bash
# 手动备份
tar -czf /opt/docker-apps/backups/config-$(date +%Y%m%d).tar.gz \
    /opt/docker-apps/clash-config-manager/config/

# 定时备份（可选）
crontab -e
# 添加：0 3 * * * tar -czf /opt/docker-apps/backups/config-$(date +\%Y\%m\%d).tar.gz /opt/docker-apps/clash-config-manager/config/
```

---

## 故障排查

### Webhook 不触发

```bash
# 检查服务状态
sudo systemctl status webhook

# 检查端口
sudo ss -tlnp | grep :9000

# 手动测试
curl -X POST \
  -H "Authorization: Bearer YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"version":"test"}' \
  http://localhost:9000/hooks/update-clash-config
```

### 镜像拉取失败

```bash
# 检查登录状态
docker login ghcr.io

# 手动拉取测试
docker pull ghcr.io/你的用户名/clash-config-manager:latest

# 查看镜像是否存在
# 访问：https://github.com/你的用户名?tab=packages
```

### 配置同步失败

```bash
# 检查 SSH 连接
ssh -i ~/.ssh/github_actions root@服务器IP

# 检查 GitHub Actions 日志
# 访问：https://github.com/你的用户名/clash-config-manager/actions
```

---

## 安全建议

### 1. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name clash.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 配置 SSL（推荐）

```bash
# 安装 certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d clash.yourdomain.com
```

### 3. 限制 SSH 访问

```bash
# 编辑 SSH 配置
sudo nano /etc/ssh/sshd_config

# 只允许密钥登录
PasswordAuthentication no
PubkeyAuthentication yes

# 重启 SSH
sudo systemctl restart sshd
```

---

## 总结

完成以上步骤后，你的 Clash Config Manager 已经成功部署并配置了自动化 CI/CD。

**自动化流程**：
- ✅ 推送代码 tag → 自动构建镜像 → 自动部署到服务器
- ✅ 修改配置 → 自动同步到服务器 → 自动重启容器
- ✅ 零停机更新、健康检查、日志记录

如有问题，请查看日志或提交 Issue。

