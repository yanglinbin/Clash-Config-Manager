# Clash 配置管理器

自动化的 Clash 代理配置管理系统，支持多订阅源合并、自动更新、节点筛选和规则管理。

## ✨ 功能特性

- 🔄 **多订阅源合并** - 支持同时管理多个代理订阅源
- 🌍 **智能节点分组** - 按地区自动分组（香港、台湾、日本、美国、新加坡等）
- 🎯 **节点关键词过滤** - 自动过滤广告节点和无效节点
- ⚙️ **自定义规则配置** - 灵活配置代理规则和分流规则
- 🔄 **定时自动更新** - 支持定时更新订阅源
- 🐳 **Docker 部署** - 容器化部署，简单可靠
- 🚀 **GitHub Actions 自动部署** - 代码推送自动部署到服务器

## 🚀 快速开始

### 1. 准备配置

```bash
# 复制配置示例
cp config/config.ini.example config/config.ini

# 编辑配置，填入你的订阅链接
nano config/config.ini
```

### 2. 启动服务

```bash
# 使用 Docker Compose 启动
docker compose up -d

# 查看服务状态
docker compose ps
```

### 3. 访问配置

应用监听在 `127.0.0.1:8080`，需要通过 Nginx 反向代理访问：

- **Clash 配置**: http://your-server/clash_profile.yaml
- **服务状态**: http://your-server/status

## 📁 项目结构

```
clash-config-manager/
├── .github/workflows/      # GitHub Actions 工作流
│   └── deploy.yml         # 自动部署配置
├── config/                 # 配置文件
│   ├── config.ini          # 主配置（需自行创建）
│   ├── config.ini.example  # 配置示例
│   ├── rules.yaml          # 规则配置
│   └── rules.schema.json   # 规则Schema
├── src/                    # 源代码
│   ├── generate_clash_config.py  # 配置生成器
│   ├── app.py                     # Web 应用
│   └── frontend/                  # 前端资源
│       ├── html/                  # HTML 模板
│       ├── css/                   # 样式表
│       └── js/                    # JavaScript 脚本
├── output/                 # 生成的配置（自动创建）
├── logs/                   # 日志文件（自动创建）
├── Dockerfile              # Docker镜像定义
├── docker-compose.yml      # Docker编排配置
├── main.py                 # 主入口（手动生成配置）
└── DEPLOY.md               # 部署文档
```

## ⚙️ 配置说明

### config.ini 主要配置

```ini
[proxy_providers]
# 订阅源配置
YOUR_PROVIDER = https://your-subscription-url

[regions]
# 地区分组配置
香港 = 🇭🇰,Hong Kong,HK,香港
台湾 = 🇹🇼,Taiwan,TW,台湾
日本 = 🇯🇵,Japan,JP,日本
美国 = 🇺🇸,United States,US,美国
新加坡 = 🇸🇬,Singapore,SG,新加坡

[filter]
# 节点过滤规则
exclude_keywords = 网址,剩余,流量,过期

[server]
# 更新间隔（秒）
update_interval = 3600
```

详细配置请参考 `config/config.ini.example`

## 🐳 Docker 说明

### docker-compose.yml

定义应用容器配置：
- 容器名: `clash-config-manager`
- 端口: `127.0.0.1:8080`（只监听本地，需通过Nginx访问）
- 自动重启: 是
- 健康检查: 是

### 部署架构

```
客户端请求
   ↓
Nginx容器 (80/443) ← 手动部署
   ↓ 反向代理
应用容器 (8080)    ← docker-compose部署
   ↓
返回响应
```

**说明**：
- 应用容器由本项目管理（docker-compose）
- Nginx容器需要手动部署和配置
- 两个容器独立运行，通过网络通信

## 🔧 常用命令

```bash
# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 查看容器状态
docker compose ps

# 手动生成配置
docker compose exec clash-config-manager python main.py
```

## 📝 部署说明

详细的Linux服务器部署步骤（包括Docker安装、数据目录配置、Nginx部署）请查看：

**[DEPLOY.md](DEPLOY.md)** - 完整部署指南

## 🔒 安全提示

⚠️ **重要**：不要将以下文件提交到 Git：
- `config/config.ini` - 包含订阅链接
- `output/clash_profile.yaml` - 包含节点信息
- `.env` - 环境变量

这些文件已在 `.gitignore` 中配置。

## 📄 License

MIT
