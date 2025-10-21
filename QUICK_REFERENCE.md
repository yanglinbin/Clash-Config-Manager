# 快速参考

> 📋 常用命令和配置速查表

---

## 🚀 日常操作

### 启动/停止服务

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps
```

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 最近 100 行
docker-compose logs --tail=100

# 只看应用日志
docker-compose logs -f clash-config-manager
```

### 更新配置

```bash
# 修改配置文件
vim config/config.ini
vim config/rules.yaml

# 重启应用配置
docker-compose restart
```

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose up -d --build
```

---

## 🔧 Nginx 管理

```bash
# 测试配置
docker exec nginx nginx -t

# 重新加载配置
docker exec nginx nginx -s reload

# 重启 Nginx
docker restart nginx

# 查看日志
docker logs nginx --tail=50
```

---

## 🌐 网络管理

```bash
# 查看网络
docker network ls

# 查看网络详情
docker network inspect docker-shared-net

# 测试连通性
docker exec nginx curl http://clash-config-manager:5000/status
```

---

## 📊 监控和诊断

```bash
# 查看容器状态
docker ps

# 查看资源使用
docker stats clash-config-manager

# 进入容器
docker exec -it clash-config-manager bash

# 容器内测试
curl http://localhost:5000/status
```

---

## 🔐 HTTPS 证书续期

```bash
# 续期证书
sudo certbot renew

# 复制证书
sudo cp /etc/letsencrypt/live/your-domain.com/*.pem /opt/project/nginx/ssl/

# 重新加载 Nginx
docker exec nginx nginx -s reload
```

---

## 📁 重要路径

| 项目 | 路径 |
|------|------|
| 项目目录 | `/opt/clash-config-manager` |
| Nginx 目录 | `/opt/project/nginx` |
| 配置文件 | `/opt/clash-config-manager/config/config.ini` |
| 规则文件 | `/opt/clash-config-manager/config/rules.yaml` |
| 输出文件 | `/opt/clash-config-manager/output/clash_profile.yaml` |
| 项目日志 | `/opt/clash-config-manager/logs/` |
| Nginx 日志 | `/opt/project/nginx/logs/` |

---

## 🌍 访问地址

| 服务 | URL |
|------|-----|
| Web 界面 | https://clash.yourdomain.com/ |
| 状态 API | https://clash.yourdomain.com/status |
| 配置文件 | https://clash.yourdomain.com/clash_profile.yaml |
| 容器内部 | http://clash-config-manager:5000 |

---

## 🆘 常见问题

### Nginx 502 错误

```bash
# 检查容器运行
docker ps

# 测试连通性
docker exec nginx ping clash-config-manager
docker exec nginx curl http://clash-config-manager:5000/status

# 查看日志
docker logs clash-config-manager --tail=50
```

### 配置文件不生效

```bash
# 重启容器应用新配置
docker-compose restart

# 查看配置是否正确挂载
docker exec clash-config-manager ls -l /app/config/
docker exec clash-config-manager cat /app/config/config.ini
```

### 端口被占用

```bash
# 查看端口占用（Linux）
sudo lsof -i :80
sudo lsof -i :443

# 查看端口占用（Windows）
netstat -ano | findstr ":80"
```

---

## 📖 详细文档

- 📘 [完整部署指南](./DEPLOY_GUIDE.md) - Docker、Nginx 安装和配置
- 📝 [项目说明](./README.md) - 项目介绍和功能特性

