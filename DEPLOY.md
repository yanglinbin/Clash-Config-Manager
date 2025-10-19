# 部署指南

本文档说明如何在Linux服务器上部署 Clash 配置管理器，并配置 GitHub Actions 实现自动部署。

## 📋 系统要求

- **操作系统**: Ubuntu 20.04+ / Debian 10+ / CentOS 7+
- **内存**: 最低 512MB
- **磁盘**: 2GB 可用空间
- **软件**: Docker 20.10+ 和 Docker Compose
- **网络**: 开放 SSH (22)、HTTP (80)、HTTPS (443) 端口

---

## 🔧 第一步：安装和配置 Docker

### 1. 安装 Docker

#### Ubuntu/Debian

```bash
# 更新包索引
sudo apt update

# 安装依赖
sudo apt install -y ca-certificates curl gnupg

# 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

#### CentOS/RHEL

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2. 配置 Docker 数据目录

将 Docker 数据存储到 `/opt/docker-apps`：

```bash
# 停止 Docker 服务
sudo systemctl stop docker

# 创建新的数据目录
sudo mkdir -p /opt/docker-apps

# 编辑 Docker 配置
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```

添加以下内容：

```json
{
  "data-root": "/opt/docker-apps",
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

保存后继续：

```bash
# 如果有旧数据，可以迁移（可选）
# sudo rsync -aP /var/lib/docker/ /opt/docker-apps/

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证配置
docker info | grep "Docker Root Dir"
# 应该显示: Docker Root Dir: /opt/docker-apps
```

### 3. 配置非 root 用户（可选）

```bash
# 添加当前用户到 docker 组
sudo usermod -aG docker $USER

# 重新登录或运行
newgrp docker

# 验证
docker ps
```

---

## 📦 第二步：部署应用容器

### 1. 准备项目目录

```bash
# 创建项目目录
sudo mkdir -p /opt/docker-apps/clash-config-manager
cd /opt/docker-apps/clash-config-manager

# 克隆项目
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# 如果是首次部署，需要配置 Git（用于后续自动部署）
git config user.email "your-email@example.com"
git config user.name "Your Name"
```

**重要提示**：
- 替换 `YOUR_USERNAME/YOUR_REPO` 为你的实际仓库地址
- 确保服务器可以访问 GitHub（可以使用 `ssh -T git@github.com` 测试）

### 2. 配置应用

```bash
# 复制配置示例
cp config/config.ini.example config/config.ini

# 编辑配置文件
nano config/config.ini
```

**必须修改的配置**:

```ini
[proxy_providers]
# 填入你的订阅链接（至少一个）
YOUR_PROVIDER = https://your-subscription-url

[server]
# 更新间隔（秒），默认3600=1小时
update_interval = 3600
```

### 3. 启动应用容器

```bash
# 构建并启动应用
docker compose up -d

# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 等待容器健康检查通过（约30秒）
docker ps
```

### 4. 验证应用

```bash
# 测试应用（本地访问）
curl http://localhost:8080/status

# 应该返回类似以下内容：
# {
#   "server": "Clash Config Manager",
#   "status": "running",
#   "timestamp": "2024-01-01T12:00:00",
#   ...
# }
```

---

## 🌐 第三步：部署 Nginx 容器

### 1. 创建 Nginx 配置目录

```bash
# 创建配置目录
sudo mkdir -p /opt/docker-apps/nginx/conf.d
sudo mkdir -p /opt/docker-apps/nginx/ssl
sudo mkdir -p /opt/docker-apps/nginx/logs
```

### 2. 创建 Nginx 主配置

```bash
sudo nano /opt/docker-apps/nginx/nginx.conf
```

内容：

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml;

    # 包含虚拟主机配置
    include /etc/nginx/conf.d/*.conf;
}
```

### 3. 创建应用反向代理配置

```bash
sudo nano /opt/docker-apps/nginx/conf.d/clash.conf
```

内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 修改为你的域名
    
    # 访问日志
    access_log /var/log/nginx/clash-access.log;
    error_log /var/log/nginx/clash-error.log;
    
    # 健康检查
    location /status {
        proxy_pass http://host.docker.internal:8080/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 手动更新接口
    location /manual-update {
        proxy_pass http://host.docker.internal:8080/manual-update;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Clash 配置文件（静态文件）
    location /clash_profile.yaml {
        alias /opt/docker-apps/clash-config-manager/output/clash_profile.yaml;
        
        # 设置正确的 Content-Type
        default_type text/yaml;
        add_header Content-Type "text/yaml; charset=utf-8";
        
        # 禁用缓存
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        
        # 允许跨域
        add_header Access-Control-Allow-Origin "*";
    }
    
    # 主页
    location / {
        proxy_pass http://host.docker.internal:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**重要**：
- 将 `your-domain.com` 替换为你的实际域名或服务器IP
- 如果没有域名，可以使用 `_`（监听所有域名）

### 4. 启动 Nginx 容器

```bash
# 启动 Nginx
docker run -d \
  --name nginx \
  --restart unless-stopped \
  -p 80:80 \
  -p 443:443 \
  -v /opt/docker-apps/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /opt/docker-apps/nginx/conf.d:/etc/nginx/conf.d:ro \
  -v /opt/docker-apps/nginx/ssl:/etc/nginx/ssl:ro \
  -v /opt/docker-apps/nginx/logs:/var/log/nginx \
  -v /opt/docker-apps/clash-config-manager/output:/opt/docker-apps/clash-config-manager/output:ro \
  --add-host=host.docker.internal:host-gateway \
  nginx:latest

# 查看 Nginx 状态
docker ps | grep nginx

# 查看 Nginx 日志
docker logs nginx
```

### 5. 测试 Nginx 配置

```bash
# 测试配置文件语法
docker exec nginx nginx -t

# 访问测试
curl http://localhost/status
curl http://localhost/clash_profile.yaml
```

---

## 🔥 第四步：配置防火墙

### ufw (Ubuntu/Debian)

```bash
# 允许 SSH（重要！）
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### firewalld (CentOS/RHEL)

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

---

## 🚀 第五步：配置 GitHub Actions 自动部署

使用 GitHub Actions，每次推送代码到 `main` 分支时，自动部署到服务器。

### 1. 配置服务器 SSH 访问

在服务器上生成 SSH 密钥：

```bash
# 生成 SSH 密钥对
cd ~
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy

# 按提示操作，建议不设置密码（否则自动部署会失败）
# 一路回车即可

# 将公钥添加到 authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys

# 设置正确的权限
chmod 600 ~/.ssh/github_deploy
chmod 644 ~/.ssh/github_deploy.pub
chmod 600 ~/.ssh/authorized_keys

# 查看私钥（稍后需要添加到 GitHub）
cat ~/.ssh/github_deploy
```

**重要**：
- 复制私钥内容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）
- 妥善保管私钥，不要泄露

### 2. 测试 SSH 连接

```bash
# 在本地测试 SSH 连接（使用私钥）
ssh -i ~/.ssh/github_deploy your_user@your_server_ip

# 如果能成功登录，说明配置正确
```

### 3. 在 GitHub 配置 Secrets

在你的 GitHub 仓库中配置密钥：

**步骤**：
1. 进入 GitHub 仓库
2. 点击 `Settings`（设置）
3. 左侧菜单选择 `Secrets and variables` → `Actions`
4. 点击 `New repository secret` 添加以下密钥：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `SERVER_HOST` | 服务器 IP 地址或域名 | `123.45.67.89` 或 `example.com` |
| `SERVER_USER` | SSH 登录用户名 | `root` 或 `ubuntu` |
| `SERVER_SSH_KEY` | SSH 私钥（完整内容） | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |
| `SERVER_PORT` | SSH 端口（可选） | `22`（默认值，可不填） |

**配置示例**：

```
Name: SERVER_HOST
Value: 123.45.67.89

Name: SERVER_USER
Value: root

Name: SERVER_SSH_KEY
Value: -----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
... (完整的私钥内容)
-----END OPENSSH PRIVATE KEY-----

Name: SERVER_PORT
Value: 22
```

### 4. 验证 GitHub Actions 工作流

项目中已包含 `.github/workflows/deploy.yml` 文件，内容如下：

```yaml
name: Deploy to Server

on:
  push:
    branches:
      - main
    paths:
      - 'src/**'
      - 'config/**'
      - 'Dockerfile'
      - 'docker-compose.yml'
      - 'requirements.txt'
      - '.github/workflows/deploy.yml'
  
  workflow_dispatch:  # 允许手动触发

jobs:
  deploy:
    name: Deploy to Production Server
    runs-on: ubuntu-latest
    
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
      
      - name: 部署到服务器
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          port: ${{ secrets.SERVER_PORT || 22 }}
          script: |
            echo "========================================="
            echo "开始部署 Clash Config Manager"
            echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
            echo "========================================="
            
            # 进入项目目录
            cd /opt/docker-apps/clash-config-manager || exit 1
            
            # 拉取最新代码
            echo "正在拉取最新代码..."
            git fetch origin
            git reset --hard origin/main
            
            # 重新构建并部署
            echo "正在重新构建镜像..."
            docker compose build --no-cache
            
            echo "正在重启容器..."
            docker compose down
            docker compose up -d
            
            # 等待容器启动
            echo "等待容器启动..."
            sleep 10
            
            # 检查容器状态
            if docker ps | grep -q "clash-config-manager"; then
              echo "✅ 容器运行正常"
              
              # 测试健康检查
              if curl -f http://localhost:8080/status; then
                echo "✅ 健康检查通过"
              else
                echo "⚠️ 健康检查失败"
                docker logs clash-config-manager --tail=50
                exit 1
              fi
            else
              echo "❌ 容器启动失败"
              docker logs clash-config-manager --tail=50
              exit 1
            fi
            
            echo "========================================="
            echo "✅ 部署完成"
            echo "========================================="
```

**触发条件**：
- 推送代码到 `main` 分支时，如果修改了以下文件会自动触发：
  - `src/**`（源代码）
  - `config/**`（配置文件）
  - `Dockerfile`
  - `docker-compose.yml`
  - `requirements.txt`
  - `.github/workflows/deploy.yml`
- 也可以在 GitHub Actions 页面手动触发

### 5. 测试自动部署

在本地修改代码并推送：

```bash
# 1. 修改任意文件（比如 README.md）
echo "# Test Auto Deploy" >> README.md

# 2. 提交更改
git add .
git commit -m "test: 测试自动部署"

# 3. 推送到 GitHub
git push origin main

# 4. 查看 GitHub Actions 执行情况
# 访问: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

**查看部署日志**：
1. 进入 GitHub 仓库
2. 点击 `Actions` 标签
3. 选择最新的工作流运行
4. 点击 `Deploy to Production Server` 查看详细日志

### 6. 手动触发部署

如果需要手动触发部署：

1. 进入 GitHub 仓库的 `Actions` 页面
2. 选择 `Deploy to Server` 工作流
3. 点击右侧的 `Run workflow` 按钮
4. 选择 `main` 分支
5. 点击 `Run workflow`

---

## 🔄 部署流程说明

### 自动部署流程

```
开发者推送代码到 GitHub (main 分支)
   ↓
GitHub Actions 自动触发
   ↓
通过 SSH 连接到服务器
   ↓
进入项目目录 /opt/docker-apps/clash-config-manager
   ↓
拉取最新代码 (git reset --hard origin/main)
   ↓
重新构建 Docker 镜像 (docker compose build --no-cache)
   ↓
停止旧容器 (docker compose down)
   ↓
启动新容器 (docker compose up -d)
   ↓
健康检查 (curl http://localhost:8080/status)
   ↓
部署完成 ✅
```

### 手动部署流程

如果不想使用自动部署，可以手动执行：

```bash
# 1. SSH 登录服务器
ssh your_user@your_server_ip

# 2. 进入项目目录
cd /opt/docker-apps/clash-config-manager

# 3. 拉取最新代码
git pull origin main

# 4. 重新构建并部署
docker compose down
docker compose build --no-cache
docker compose up -d

# 5. 查看日志
docker compose logs -f

# 6. 验证部署
curl http://localhost:8080/status
```

---

## 🔄 日常维护

### 查看容器状态

```bash
# 查看所有容器
docker ps -a

# 查看应用日志
docker logs -f clash-config-manager

# 查看 Nginx 日志
docker logs -f nginx

# 查看实时日志（应用）
cd /opt/docker-apps/clash-config-manager
docker compose logs -f
```

### 重启服务

```bash
# 重启应用
cd /opt/docker-apps/clash-config-manager
docker compose restart

# 重启 Nginx
docker restart nginx

# 重启所有服务
docker compose restart && docker restart nginx
```

### 更新配置文件

```bash
# 修改配置
cd /opt/docker-apps/clash-config-manager
nano config/config.ini

# 重启应用使配置生效
docker compose restart

# 查看日志确认
docker compose logs -f
```

### 更新 Nginx 配置

```bash
# 编辑配置
sudo nano /opt/docker-apps/nginx/conf.d/clash.conf

# 测试配置
docker exec nginx nginx -t

# 重载配置（不重启）
docker exec nginx nginx -s reload

# 如果需要重启
docker restart nginx
```

### 手动触发配置更新

```bash
# 方式1：通过 API
curl -X POST http://localhost:8080/manual-update

# 方式2：通过浏览器
# 访问 http://your-server 点击"手动更新配置"按钮

# 方式3：进入容器执行
docker exec clash-config-manager python main.py
```

### 备份重要数据

```bash
# 备份配置文件
sudo cp /opt/docker-apps/clash-config-manager/config/config.ini ~/config.ini.backup.$(date +%Y%m%d)

# 备份输出文件
sudo cp /opt/docker-apps/clash-config-manager/output/clash_profile.yaml ~/clash_profile.yaml.backup.$(date +%Y%m%d)

# 备份 Nginx 配置
sudo tar -czf ~/nginx-config-backup.$(date +%Y%m%d).tar.gz /opt/docker-apps/nginx/

# 查看备份
ls -lh ~/*.backup* ~/*.tar.gz
```

### 查看磁盘使用

```bash
# 查看 Docker 占用
docker system df

# 清理未使用的资源
docker system prune -a

# 查看目录占用
du -sh /opt/docker-apps/*
```

---

## 🐛 故障排除

### 问题 1: 应用容器无法启动

**症状**：
```bash
docker ps
# 没有看到 clash-config-manager 容器
```

**排查**：
```bash
# 查看容器状态（包括已停止的）
docker ps -a | grep clash

# 查看日志
docker logs clash-config-manager

# 查看最近的错误
docker compose logs --tail=50
```

**常见原因**：
1. **配置文件错误**：检查 `config/config.ini` 格式
2. **端口被占用**：`sudo lsof -i :8080` 检查端口
3. **权限问题**：确保 `config/config.ini` 存在且可读

**解决方法**：
```bash
# 重新构建
cd /opt/docker-apps/clash-config-manager
docker compose down
docker compose build --no-cache
docker compose up -d

# 查看详细日志
docker compose logs -f
```

### 问题 2: Nginx 无法访问应用

**症状**：
```bash
curl http://localhost/status
# 502 Bad Gateway 或连接超时
```

**排查**：
```bash
# 检查 Nginx 日志
docker logs nginx
tail -f /opt/docker-apps/nginx/logs/error.log

# 测试应用是否正常
curl http://localhost:8080/status

# 测试网络连接
docker exec nginx ping host.docker.internal
```

**常见原因**：
1. **应用未运行**：`docker ps | grep clash`
2. **网络配置错误**：`host.docker.internal` 无法解析

**解决方法**：
```bash
# 方案1：使用 --add-host（推荐）
docker stop nginx
docker rm nginx
docker run -d \
  --name nginx \
  --restart unless-stopped \
  -p 80:80 \
  -p 443:443 \
  --add-host=host.docker.internal:host-gateway \
  -v /opt/docker-apps/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /opt/docker-apps/nginx/conf.d:/etc/nginx/conf.d:ro \
  -v /opt/docker-apps/nginx/ssl:/etc/nginx/ssl:ro \
  -v /opt/docker-apps/nginx/logs:/var/log/nginx \
  -v /opt/docker-apps/clash-config-manager/output:/opt/docker-apps/clash-config-manager/output:ro \
  nginx:latest

# 方案2：使用宿主机 IP
# 获取宿主机 Docker 网桥 IP
ip addr show docker0 | grep inet
# 修改 nginx 配置中的 proxy_pass 为: http://172.17.0.1:8080
```

### 问题 3: GitHub Actions 部署失败

**症状**：
- GitHub Actions 工作流显示失败 ❌
- SSH 连接超时或权限错误

**排查**：
```bash
# 1. 检查 SSH 配置
cat ~/.ssh/authorized_keys | grep github-deploy

# 2. 测试 SSH 连接
ssh -i ~/.ssh/github_deploy your_user@your_server_ip

# 3. 检查服务器防火墙
sudo ufw status | grep 22
sudo firewall-cmd --list-all | grep ssh

# 4. 查看 GitHub Actions 日志
# 访问: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

**常见原因**：
1. **SSH 密钥错误**：检查 GitHub Secrets 中的 `SERVER_SSH_KEY`
2. **用户权限不足**：确保用户有 Docker 权限
3. **防火墙阻止**：开放 SSH 端口（22）
4. **项目目录不存在**：确保 `/opt/docker-apps/clash-config-manager` 存在

**解决方法**：
```bash
# 添加用户到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 确保 SSH 服务运行
sudo systemctl status sshd
sudo systemctl start sshd
sudo systemctl enable sshd

# 检查 SSH 端口
sudo netstat -tuln | grep :22

# 测试 Docker 权限
docker ps
```

### 问题 4: 配置文件无法访问

**症状**：
```bash
curl http://your-server/clash_profile.yaml
# 404 Not Found 或 403 Forbidden
```

**排查**：
```bash
# 检查文件是否存在
ls -lh /opt/docker-apps/clash-config-manager/output/clash_profile.yaml

# 检查文件权限
stat /opt/docker-apps/clash-config-manager/output/clash_profile.yaml

# 检查 Nginx 配置
docker exec nginx cat /etc/nginx/conf.d/clash.conf | grep clash_profile
```

**解决方法**：
```bash
# 生成配置文件
cd /opt/docker-apps/clash-config-manager
docker compose exec clash-config-manager python main.py

# 或通过 API
curl -X POST http://localhost:8080/manual-update

# 设置正确权限
sudo chmod 644 /opt/docker-apps/clash-config-manager/output/clash_profile.yaml
```

### 问题 5: 端口被占用

**症状**：
```bash
docker compose up -d
# Error: port is already allocated
```

**排查**：
```bash
# 查找占用端口的进程
sudo lsof -i :8080
sudo lsof -i :80
sudo netstat -tuln | grep 8080
```

**解决方法**：
```bash
# 停止占用端口的服务
sudo systemctl stop nginx  # 如果有系统级 nginx
sudo systemctl stop apache2  # 如果有 Apache

# 或修改应用端口
# 编辑 docker-compose.yml，修改端口映射
nano docker-compose.yml
# 将 127.0.0.1:8080:8080 改为 127.0.0.1:8081:8080

# 同时修改 Nginx 配置
sudo nano /opt/docker-apps/nginx/conf.d/clash.conf
# 将 proxy_pass http://host.docker.internal:8080 改为 8081
```

---

## 📝 常用命令速查

```bash
# === 应用容器 ===
cd /opt/docker-apps/clash-config-manager

# 启动
docker compose up -d

# 停止
docker compose down

# 重启
docker compose restart

# 查看日志
docker compose logs -f

# 查看状态
docker compose ps

# 重新构建
docker compose build --no-cache

# 手动生成配置
docker compose exec clash-config-manager python main.py

# 进入容器
docker exec -it clash-config-manager bash


# === Nginx 容器 ===

# 启动
docker start nginx

# 停止
docker stop nginx

# 重启
docker restart nginx

# 查看日志
docker logs -f nginx

# 重载配置
docker exec nginx nginx -s reload

# 测试配置
docker exec nginx nginx -t

# 进入容器
docker exec -it nginx bash


# === Git 操作 ===
cd /opt/docker-apps/clash-config-manager

# 拉取最新代码
git pull origin main

# 查看状态
git status

# 查看提交历史
git log --oneline -10

# 重置到最新版本（慎用）
git fetch origin
git reset --hard origin/main


# === Docker 管理 ===

# 查看所有容器
docker ps -a

# 查看镜像
docker images

# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a

# 查看 Docker 数据目录
docker info | grep "Docker Root Dir"

# 查看网络
docker network ls


# === 系统监控 ===

# 查看磁盘使用
df -h

# 查看目录大小
du -sh /opt/docker-apps/*

# 查看内存使用
free -h

# 查看 CPU 负载
top

# 查看端口占用
sudo netstat -tuln | grep -E ':(80|443|8080)'
```

---

## ✅ 部署完成

现在你的 Clash 配置管理器已经成功部署！

### 访问地址

- **Clash 配置**: `http://your-server/clash_profile.yaml`
- **服务状态**: `http://your-server/status`
- **管理页面**: `http://your-server/`

### 访问架构

```
外部访问
   ↓
Nginx 容器 (80/443端口)
   ↓ 反向代理
应用容器 (127.0.0.1:8080)
   ↓
返回响应
```

### 数据存储

所有数据存储在 `/opt/docker-apps` 目录：

```
/opt/docker-apps/
├── clash-config-manager/     # 应用数据
│   ├── config/               # 配置文件
│   ├── output/               # 生成的配置
│   ├── logs/                 # 应用日志
│   └── backups/              # 备份文件
└── nginx/                    # Nginx 配置
    ├── conf.d/               # 虚拟主机配置
    ├── ssl/                  # SSL 证书
    └── logs/                 # Nginx 日志
```

### 自动部署

- ✅ 推送代码到 GitHub `main` 分支自动部署
- ✅ 可在 GitHub Actions 页面手动触发部署
- ✅ 部署日志清晰可查

### 下一步

1. **配置域名和 SSL**（推荐）
2. **设置定期备份**
3. **配置监控告警**
4. **优化 Nginx 性能**

---

**祝使用愉快！** 🎉

如有问题，请查看[项目 README](README.md) 或提交 Issue。
