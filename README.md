# Clash 配置管理器

自动化的 Clash 代理配置管理系统，支持多订阅源合并、自动更新、节点筛选和规则管理。

## 功能特性

- 🔄 **多订阅源合并** - 支持同时管理多个代理订阅源
- 🌍 **智能节点分组** - 按地区自动分组（香港、台湾、日本、美国、新加坡等）
- 🎯 **节点关键词过滤** - 自动过滤广告节点和无效节点
- ⚙️ **自定义规则配置** - 灵活配置代理规则和分流规则
- 🐳 **Docker 部署** - 容器化部署，简单可靠
- 🌐 **Web 管理界面** - 提供状态查询和手动更新功能
- 🚀 **CI/CD 自动化** - GitHub Actions 自动构建和部署

---

## 快速开始

### 本地开发（Windows）

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/clash-config-manager.git
cd clash-config-manager

# 2. 配置订阅
cp config/config.ini.example config/config.ini
# 编辑 config.ini 填入你的订阅链接

# 3. 本地测试
docker-compose up --build

# 4. 访问
http://localhost:8080/
```

### 生产部署（Ubuntu）

详细部署步骤请查看：[DEPLOY.md](DEPLOY.md)

---

## 项目结构

```
clash-config-manager/
├── .github/workflows/          # GitHub Actions CI/CD
│   ├── build-and-push.yml     # 构建镜像并推送到 ghcr.io
│   └── sync-config.yml        # 同步配置文件到服务器
├── config/                     # 配置文件
│   ├── config.ini.example     # 配置示例
│   ├── rules.yaml             # 规则配置
│   └── rules.schema.json      # 规则模式
├── src/                        # 源代码
│   ├── app.py                 # Flask Web 应用
│   ├── generate_clash_config.py
│   └── frontend/              # 前端资源
├── server-deploy/              # 服务器部署文件
│   ├── hooks.json             # Webhook 配置
│   ├── update-from-github.sh  # 自动更新脚本
│   └── webhook.service        # systemd 服务
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # 镜像构建
└── README.md                   # 本文件
```

---

## API 端点

- `GET /` - Web 管理界面
- `GET /status` - 服务状态（JSON）
- `POST /update` - 手动触发更新
- `GET /clash_profile.yaml` - 下载生成的配置文件

---

## 配置说明

### config.ini

```ini
[subscription]
urls = 
    https://your-subscription-url-1
    https://your-subscription-url-2

[proxy_group_defaults]
🚀节点选择 = 🇭🇰香港
🇭🇰香港 = DIRECT
🇨🇳台湾 = DIRECT
🇯🇵日本 = DIRECT
🇺🇸美国 = DIRECT
🇸🇬新加坡 = DIRECT
```

详细配置说明请参考 `config/config.ini.example`。

---

## 自动化部署

### 代码更新

```bash
git tag v1.0.0
git push --tags
# GitHub Actions 自动构建并部署到服务器
```

### 配置更新

```bash
vim config/rules.yaml
git commit -am "chore: 更新规则"
git push
# GitHub Actions 自动同步到服务器并重启
```

---

## 开发

### 技术栈

- **后端**: Python 3.9 + Flask + Gunicorn
- **容器**: Docker + Docker Compose
- **CI/CD**: GitHub Actions + GitHub Container Registry
- **自动化**: Webhook + SSH

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
python src/app.py

# 或使用 Docker
docker-compose up --build
```

---

## License

MIT License

---

## 相关文档

- [部署指南](DEPLOY.md) - 详细的服务器部署步骤
