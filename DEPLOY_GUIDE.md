# Clash Config Manager 完整部署指南

> 📘 本指南涵盖从零开始的完整部署流程，包括 Docker 安装、Nginx 容器配置和本项目部署。

---

## 📋 目录

1. [架构说明](#架构说明)
2. [环境准备](#环境准备)
3. [Docker 安装](#docker-安装)
4. [部署 Nginx 容器](#部署-nginx-容器)
5. [部署本项目](#部署本项目)
6. [验证测试](#验证测试)
7. [故障排查](#故障排查)
8. [常用命令](#常用命令)

---

## 架构说明

### 🏗️ 网络拓扑

```
                外部请求
                   │
                   ▼
        ┌──────────────────────┐
        │   宿主机              │
        │   (端口 80/443)       │
        └──────────┬────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │     docker-shared-net (bridge)       │
    │                                      │
    │  ┌───────────┐    ┌──────────────┐ │
    │  │  Nginx    │───▶│ Clash Config │ │
    │  │  容器     │    │ Manager      │ │
    │  │ (80/443)  │    │ (5000)       │ │
    │  └───────────┘    └──────────────┘ │
    │                                      │
    │  ┌──────────────┐  ┌─────────────┐ │
    │  │ 其他 Web 项目│  │ 其他 Web    │ │
    │  │     #1       │  │   项目 #2   │ │
    │  └──────────────┘  └─────────────┘ │
    │                                      │
    └──────────────────────────────────────┘
```

### ✨ 架构优势

- 🔒 **安全性**：应用不直接暴露到宿主机，只能通过 Nginx 访问
- 🚀 **性能**：容器间通信使用 Docker 内部网络，无端口映射开销
- 🎯 **灵活性**：统一管理 SSL、日志、访问控制
- 📊 **可扩展**：轻松添加更多 Web 服务到同一网络

---

## 环境准备

### 系统要求

- **操作系统**：Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Windows 10+ (Docker Desktop)
- **内存**：最低 2GB，推荐 4GB
- **存储**：最低 20GB 可用空间
- **网络**：需要能访问 GitHub

### 防火墙配置

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Docker 安装

### Linux 系统

#### 方式 1：一键安装（推荐）

```bash
# 下载并执行官方安装脚本
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（可选，避免每次使用 sudo）
sudo usermod -aG docker $USER

# 重新登录或执行以下命令使组权限生效
newgrp docker

# 验证安装
docker --version
docker ps
```

#### 方式 2：手动安装（Ubuntu/Debian）

```bash
# 更新包索引
sudo apt update

# 安装依赖
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 设置稳定版仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 启动服务
sudo systemctl start docker
sudo systemctl enable docker
```

#### 方式 3：手动安装（CentOS/RHEL）

```bash
# 卸载旧版本
sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine

# 安装依赖
sudo yum install -y yum-utils

# 设置仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io

# 启动服务
sudo systemctl start docker
sudo systemctl enable docker
```

### Windows 系统

1. **下载 Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop/
   - 下载 Windows 版本安装包

2. **安装步骤**
   - 双击安装包，按提示完成安装
   - 重启计算机
   - 启动 Docker Desktop

3. **验证安装**
   ```powershell
   docker --version
   docker ps
   ```

### 安装 Docker Compose

#### Linux 系统

```bash
# 下载最新版本
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

#### Windows 系统

Docker Desktop 已内置 Docker Compose，无需单独安装。

### 验证 Docker 安装

```bash
# 查看 Docker 版本
docker --version

# 查看 Docker Compose 版本
docker-compose --version

# 运行测试容器
docker run hello-world

# 查看 Docker 信息
docker info
```

---

## 部署 Nginx 容器

### 1. 创建共享网络

```bash
# 创建 Docker 共享网络（所有 Web 项目使用）
docker network create docker-shared-net

# 验证网络创建成功
docker network ls | grep docker-shared-net

# 查看网络详细信息
docker network inspect docker-shared-net
```

### 2. 拉取 Nginx 镜像

```bash
# 拉取官方 Nginx 镜像
docker pull nginx:latest

# 验证镜像下载成功
docker images | grep nginx
```

### 3. 创建 Nginx 项目目录

```bash
# 创建目录结构
sudo mkdir -p /opt/project/nginx/{conf,ssl,logs,html}
cd /opt/project/nginx

# 设置权限
sudo chown -R $USER:$USER /opt/project/nginx
```

### 4. 启动临时 Nginx 容器并提取配置文件

```bash
# 启动临时容器（容器端口 80 映射到主机端口 80）
docker run -d --name nginx-temp -p 80:80 nginx:latest

# 等待容器启动
sleep 3

# 验证容器运行
docker ps | grep nginx-temp

# 从容器复制 Nginx 主配置文件
docker cp nginx-temp:/etc/nginx/nginx.conf /opt/project/nginx/conf/nginx.conf

# 从容器复制站点配置目录
docker cp nginx-temp:/etc/nginx/conf.d /opt/project/nginx/conf/

# 从容器复制默认 HTML 文件
docker cp nginx-temp:/usr/share/nginx/html /opt/project/nginx/

# 停止并删除临时容器
docker stop nginx-temp
docker rm nginx-temp

# 验证文件已复制
ls -la /opt/project/nginx/conf/
ls -la /opt/project/nginx/conf/conf.d/
ls -la /opt/project/nginx/html/
```

### 5. 修改 Nginx 配置（可选）

```bash
# 编辑主配置文件（如果需要）
vim /opt/project/nginx/conf/nginx.conf

# 查看默认站点配置
cat /opt/project/nginx/conf/conf.d/default.conf
```

**建议的优化配置**（可选）：

```bash
# 在主配置文件中添加客户端上传大小限制
# 编辑 /opt/project/nginx/conf/nginx.conf
# 在 http 块中添加：
client_max_body_size 100M;

# 启用 Gzip 压缩
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss;
```

### 6. 创建 Nginx Docker Compose 配置

创建 `/opt/project/nginx/docker-compose.yml`：

```bash
cat > /opt/project/nginx/docker-compose.yml <<'EOF'
version: '3.8'

services:
  nginx:
    image: nginx:latest
    container_name: nginx
    restart: unless-stopped
    
    # 映射端口到宿主机
    ports:
      - "80:80"      # HTTP
      - "443:443"    # HTTPS
    
    # 挂载配置和内容
    volumes:
      # Nginx 主配置
      - ./conf/nginx.conf:/etc/nginx/nginx.conf:ro
      # 站点配置目录
      - ./conf/conf.d:/etc/nginx/conf.d:ro
      # SSL 证书目录
      - ./ssl:/etc/nginx/ssl:ro
      # 静态文件目录
      - ./html:/usr/share/nginx/html:ro
      # 日志目录
      - ./logs:/var/log/nginx
    
    # 加入共享网络
    networks:
      - docker-shared-net
    
    # 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    
    # 日志配置
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

# 使用外部共享网络
networks:
  docker-shared-net:
    external: true
EOF
```

### 7. 启动 Nginx 容器

```bash
cd /opt/project/nginx

# 启动 Nginx（使用 docker-compose）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 按 Ctrl+C 退出日志查看

# 查看容器状态
docker-compose ps

# 预期输出：
# NAME    STATUS          PORTS
# nginx   Up (healthy)    0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### 8. 验证 Nginx 部署

```bash
# 测试 HTTP 访问
curl http://localhost

# 预期输出：Nginx 欢迎页面的 HTML 内容

# 使用浏览器访问（如果有桌面环境）
# http://服务器IP

# 确认 Nginx 在共享网络中
docker network inspect docker-shared-net | grep nginx

# 查看容器详细信息
docker inspect nginx | grep IPAddress
```

### 9. 目录结构说明

部署完成后的目录结构：

```
/opt/project/nginx/
├── conf/
│   ├── nginx.conf              # Nginx 主配置文件
│   └── conf.d/
│       └── default.conf        # 默认站点配置
├── ssl/                        # SSL 证书目录（暂时为空）
├── logs/                       # 日志目录
│   ├── access.log
│   └── error.log
├── html/                       # 网站根目录
│   ├── index.html              # 默认首页
│   └── 50x.html                # 错误页面
└── docker-compose.yml          # Docker Compose 配置
```

---

## 部署本项目

### 1. 克隆项目

```bash
# 创建项目目录
sudo mkdir -p /opt/clash-config-manager
sudo chown $USER:$USER /opt/clash-config-manager

# 克隆仓库
cd /opt/clash-config-manager
git clone https://github.com/your-username/clash-config-manager.git .

# 或使用 HTTPS
git clone https://github.com/your-username/clash-config-manager.git .
```

### 2. 配置项目

```bash
# 复制配置文件
cp config/config.ini.example config/config.ini

# 编辑配置文件
vim config/config.ini
# 或
nano config/config.ini
```

**必须修改的配置**：

```ini
[proxy_providers]
# 替换为你的实际订阅链接
YOUR_PROVIDER = https://your-subscription-url
```

### 3. 启动项目

```bash
# 确保在项目目录
cd /opt/clash-config-manager

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看容器状态
docker-compose ps
```

**预期输出**：

```
NAME                    STATUS          PORTS
clash-config-manager    Up (healthy)
```

### 4. 配置 Nginx 代理

创建 `/opt/project/nginx/conf/conf.d/clash-manager.conf`：

```bash
cat > /opt/project/nginx/conf/conf.d/clash-manager.conf <<'EOF'
# Clash Config Manager 代理配置
server {
    listen 80;
    server_name clash.yourdomain.com;  # 替换为你的域名或 IP

    # 访问日志
    access_log /var/log/nginx/clash-manager-access.log;
    error_log /var/log/nginx/clash-manager-error.log;

    # 反向代理到 Clash Config Manager
    location / {
        # 使用容器名访问（Docker 内部 DNS）
        proxy_pass http://clash-config-manager:5000;
        
        # 代理头设置
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Clash 配置文件直接访问
    location /clash_profile.yaml {
        proxy_pass http://clash-config-manager:5000/clash_profile.yaml;
        proxy_set_header Host $host;
    }
    
    # 健康检查端点
    location /status {
        proxy_pass http://clash-config-manager:5000/status;
        proxy_set_header Host $host;
    }
}
EOF
```

### 5. 重新加载 Nginx 配置

```bash
# 测试配置文件语法
docker exec nginx nginx -t

# 重新加载配置
docker exec nginx nginx -s reload

# 或重启 Nginx 容器
docker restart nginx
```

### 6. 配置 HTTPS（推荐）

#### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
sudo apt install certbot -y

# 获取证书（使用 webroot 模式）
sudo certbot certonly --webroot \
  -w /opt/project/nginx/html \
  -d clash.yourdomain.com \
  --email your-email@example.com \
  --agree-tos

# 证书路径
# 证书：/etc/letsencrypt/live/clash.yourdomain.com/fullchain.pem
# 私钥：/etc/letsencrypt/live/clash.yourdomain.com/privkey.pem

# 复制证书到 Nginx SSL 目录
sudo cp /etc/letsencrypt/live/clash.yourdomain.com/fullchain.pem /opt/project/nginx/ssl/
sudo cp /etc/letsencrypt/live/clash.yourdomain.com/privkey.pem /opt/project/nginx/ssl/
sudo chown $USER:$USER /opt/project/nginx/ssl/*
```

#### 更新 Nginx 配置为 HTTPS

```bash
cat > /opt/project/nginx/conf/conf.d/clash-manager.conf <<'EOF'
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name clash.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name clash.yourdomain.com;

    # SSL 证书
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL 优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 访问日志
    access_log /var/log/nginx/clash-manager-access.log;
    error_log /var/log/nginx/clash-manager-error.log;

    # 反向代理配置
    location / {
        proxy_pass http://clash-config-manager:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
    
    location /clash_profile.yaml {
        proxy_pass http://clash-config-manager:5000/clash_profile.yaml;
        proxy_set_header Host $host;
    }
    
    location /status {
        proxy_pass http://clash-config-manager:5000/status;
        proxy_set_header Host $host;
    }
}
EOF

# 重新加载配置
docker exec nginx nginx -t
docker exec nginx nginx -s reload
```

#### 设置证书自动续期

```bash
# 测试自动续期
sudo certbot renew --dry-run

# 添加定时任务（每天检查证书是否需要续期）
sudo crontab -e

# 添加以下行
0 0 * * * certbot renew --quiet --post-hook "cp /etc/letsencrypt/live/clash.yourdomain.com/*.pem /opt/project/nginx/ssl/ && docker exec nginx nginx -s reload"
```

---

## 验证测试

### 1. 容器健康检查

```bash
# 查看所有容器状态
docker ps

# 预期输出：
# nginx                Up (healthy)
# clash-config-manager Up (healthy)
```

### 2. 网络连通性测试

```bash
# 从 Clash Config Manager 容器测试自身
docker exec clash-config-manager curl -f http://localhost:5000/status

# 从 Nginx 容器测试 Clash Config Manager
docker exec nginx curl -f http://clash-config-manager:5000/status

# 预期输出：
# {"status":"running","version":"1.0.0",...}
```

### 3. 外部访问测试

```bash
# HTTP 访问
curl http://clash.yourdomain.com/status

# HTTPS 访问
curl https://clash.yourdomain.com/status

# 下载配置文件
curl https://clash.yourdomain.com/clash_profile.yaml | head -20
```

### 4. Web 界面测试

打开浏览器访问：

- **管理界面**：https://clash.yourdomain.com/
- **状态 API**：https://clash.yourdomain.com/status
- **配置文件**：https://clash.yourdomain.com/clash_profile.yaml

---

## 故障排查

### 问题 1: Docker 服务无法启动

**症状**：`Cannot connect to the Docker daemon`

**解决方案**：

```bash
# 检查 Docker 服务状态
sudo systemctl status docker

# 启动 Docker 服务
sudo systemctl start docker

# 查看详细日志
sudo journalctl -u docker -n 50
```

### 问题 2: 网络不存在

**症状**：`Network docker-shared-net declared as external, but could not be found`

**解决方案**：

```bash
# 创建网络
docker network create docker-shared-net

# 验证
docker network ls | grep docker-shared-net

# 重新启动容器
docker-compose up -d
```

### 问题 3: Nginx 返回 502 Bad Gateway

**可能原因**：
- Clash Config Manager 容器未运行
- 两个容器不在同一网络
- 容器名配置错误

**排查步骤**：

```bash
# 1. 检查容器状态
docker ps -a

# 2. 检查容器是否在同一网络
docker network inspect docker-shared-net | grep -E "(nginx|clash-config-manager)"

# 3. 测试连通性
docker exec nginx ping -c 3 clash-config-manager
docker exec nginx curl http://clash-config-manager:5000/status

# 4. 查看日志
docker logs nginx --tail=50
docker logs clash-config-manager --tail=50
```

**解决方案**：

```bash
# 确保两个容器都在网络中
docker network connect docker-shared-net nginx
docker network connect docker-shared-net clash-config-manager

# 重启容器
docker restart nginx
docker restart clash-config-manager
```

### 问题 4: 端口已被占用

**症状**：`bind: address already in use`

**排查步骤**：

```bash
# Linux 查看端口占用
sudo netstat -tulpn | grep -E ':(80|443|5000)'
sudo lsof -i :80
sudo lsof -i :443

# Windows 查看端口占用
netstat -ano | findstr ":80"
netstat -ano | findstr ":443"
```

**解决方案**：

```bash
# 停止占用端口的进程（替换 PID）
sudo kill -9 <PID>

# 或修改 docker-compose.yml 使用其他端口
ports:
  - "8080:80"   # 使用 8080 代替 80
  - "8443:443"  # 使用 8443 代替 443
```

### 问题 5: 证书过期

**症状**：浏览器显示 SSL 证书错误

**解决方案**：

```bash
# 手动续期证书
sudo certbot renew

# 复制新证书
sudo cp /etc/letsencrypt/live/clash.yourdomain.com/*.pem /opt/project/nginx/ssl/

# 重新加载 Nginx
docker exec nginx nginx -s reload

# 检查证书有效期
openssl x509 -in /opt/project/nginx/ssl/fullchain.pem -noout -dates
```

### 问题 6: 配置文件不存在

**症状**：容器启动失败，日志显示配置文件找不到

**排查步骤**：

```bash
# 检查配置文件
ls -l /opt/clash-config-manager/config/config.ini
ls -l /opt/clash-config-manager/config/rules.yaml

# 查看容器内部
docker exec -it clash-config-manager ls -l /app/config/
```

**解决方案**：

```bash
# 确保配置文件存在
cd /opt/clash-config-manager
cp config/config.ini.example config/config.ini
vim config/config.ini

# 重启容器
docker-compose restart
```

---

## 常用命令

### Docker 基础命令

```bash
# 查看所有容器
docker ps -a

# 查看运行中的容器
docker ps

# 查看容器日志
docker logs <容器名>
docker logs -f <容器名>  # 实时查看
docker logs --tail=100 <容器名>  # 查看最后 100 行

# 进入容器
docker exec -it <容器名> bash
docker exec -it <容器名> sh

# 重启容器
docker restart <容器名>

# 停止容器
docker stop <容器名>

# 删除容器
docker rm <容器名>

# 查看容器详情
docker inspect <容器名>

# 查看容器资源使用
docker stats <容器名>
```

### Docker Compose 命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps

# 重新构建并启动
docker-compose up -d --build

# 只构建不启动
docker-compose build

# 验证配置文件
docker-compose config
```

### 网络管理命令

```bash
# 列出所有网络
docker network ls

# 查看网络详情
docker network inspect docker-shared-net

# 创建网络
docker network create <网络名>

# 删除网络
docker network rm <网络名>

# 将容器连接到网络
docker network connect <网络名> <容器名>

# 断开容器与网络的连接
docker network disconnect <网络名> <容器名>
```

### Nginx 相关命令

```bash
# 测试配置文件
docker exec nginx nginx -t

# 重新加载配置
docker exec nginx nginx -s reload

# 查看 Nginx 版本
docker exec nginx nginx -v

# 查看访问日志
docker exec nginx tail -f /var/log/nginx/access.log

# 查看错误日志
docker exec nginx tail -f /var/log/nginx/error.log

# 或直接查看宿主机日志
tail -f /opt/project/nginx/logs/access.log
tail -f /opt/project/nginx/logs/error.log
```

### 项目管理命令

```bash
# 查看项目状态
cd /opt/clash-config-manager
docker-compose ps

# 更新代码
git pull origin main

# 重新构建并启动
docker-compose up -d --build

# 查看应用日志
docker-compose logs -f clash-config-manager

# 进入容器
docker exec -it clash-config-manager bash

# 手动生成配置
docker exec clash-config-manager python main.py
```

### 日志管理

```bash
# 清理 Docker 日志
sudo truncate -s 0 $(docker inspect --format='{{.LogPath}}' nginx)
sudo truncate -s 0 $(docker inspect --format='{{.LogPath}}' clash-config-manager)

# 清理项目日志
cd /opt/clash-config-manager
truncate -s 0 logs/clash_generator.log
truncate -s 0 logs/access.log
truncate -s 0 logs/error.log

# 清理 Nginx 日志
cd /opt/project/nginx
truncate -s 0 logs/access.log
truncate -s 0 logs/error.log
```

### 备份和恢复

```bash
# 备份配置
cd /opt/clash-config-manager
tar -czf backup-$(date +%Y%m%d).tar.gz config/ output/ logs/

# 恢复配置
tar -xzf backup-20250101.tar.gz

# 备份 Nginx 配置
cd /opt/project/nginx
tar -czf nginx-backup-$(date +%Y%m%d).tar.gz conf/ ssl/

# 导出镜像
docker save nginx:alpine -o nginx-alpine.tar
docker save clash-config-manager -o clash-config-manager.tar

# 导入镜像
docker load -i nginx-alpine.tar
docker load -i clash-config-manager.tar
```

---

## 🎉 部署完成

现在你已经拥有一个完整的部署环境：

- ✅ Docker 和 Docker Compose 已安装
- ✅ Nginx 容器作为反向代理运行
- ✅ Clash Config Manager 容器运行在内部网络
- ✅ 所有服务通过 docker-shared-net 互联
- ✅ HTTPS 证书配置（可选）

### 访问地址

- **Web 管理界面**：https://clash.yourdomain.com/
- **状态 API**：https://clash.yourdomain.com/status
- **Clash 配置**：https://clash.yourdomain.com/clash_profile.yaml

### 下一步

- 📊 配置监控和告警
- 🔄 设置自动备份
- 🔐 配置访问控制和认证
- 📝 添加更多 Web 项目到 docker-shared-net

---

**祝你部署顺利！** 🚀

