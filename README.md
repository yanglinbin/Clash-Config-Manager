# Clash 配置管理器

自动化的 Clash 代理配置管理系统，支持多订阅源合并、自动更新、节点筛选和规则管理。

## ✨ 功能特性

- 🔄 **多订阅源合并** - 支持同时管理多个代理订阅源
- 🌍 **智能节点分组** - 按地区自动分组（香港、台湾、日本、美国、新加坡等）
- 🎯 **节点关键词过滤** - 自动过滤广告节点和无效节点
- ⚙️ **自定义规则配置** - 灵活配置代理规则和分流规则
- 🐳 **Docker 部署** - 容器化部署，简单可靠
- 🌐 **Web 管理界面** - 提供状态查询和手动更新功能

---

## 🚀 快速开始

### 前置要求

- Docker 和 Docker Compose 已安装
- 已创建 `docker-shared-net` 网络
- Nginx 容器已部署并配置

> 📘 **首次部署**？请查看完整部署指南：[DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md)

### 1. 创建网络（首次部署）

```bash
# 创建 Docker 共享网络
docker network create docker-shared-net
```

### 2. 准备配置

```bash
# 复制配置示例
cp config/config.ini.example config/config.ini

# 编辑配置，填入你的订阅链接
vim config/config.ini
```

### 3. 启动服务

```bash
# 使用 Docker Compose 启动
docker compose up -d

# 查看服务状态
docker compose ps
```

### 4. 配置 Nginx 代理

在 Nginx 配置中添加反向代理规则，将域名指向 `http://clash-config-manager:5000`

详细配置请参考：[DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md)

### 5. 访问服务

- **管理界面**: https://clash.yourdomain.com/
- **服务状态**: https://clash.yourdomain.com/status
- **Clash 配置**: https://clash.yourdomain.com/clash_profile.yaml

---

## 📁 项目结构

```
clash-config-manager/
├── config/                 # 配置文件
│   ├── config.ini          # 主配置（运行必需，需自行创建）
│   ├── config.ini.example  # 配置示例（仅供参考）
│   ├── rules.yaml          # 规则配置（运行必需）
│   └── rules.schema.json   # JSON Schema（仅供验证）
├── src/                    # 源代码
│   ├── generate_clash_config.py  # 配置生成器
│   ├── app.py                     # Web 应用
│   └── frontend/                  # 前端资源
│       ├── html/                  # HTML 模板
│       ├── css/                   # 样式表
│       └── js/                    # JavaScript 脚本
├── output/                 # 生成的配置（自动创建）
├── logs/                   # 日志文件（自动创建）
├── backups/                # 备份目录（可选）
├── Dockerfile              # Docker 镜像定义
├── docker-compose.yml      # Docker 编排配置
├── requirements.txt        # Python 依赖
└── main.py                 # 主入口（手动生成配置）
```

---

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

---

## 📊 Web 管理界面

访问 `http://your-server/` 可查看：

- 📊 服务状态信息
- 📁 配置文件状态
- 🔄 手动触发更新
- 🔌 API 接口文档

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 管理界面 |
| `/status` | GET | 服务状态（JSON） |
| `/manual-update` | POST | 手动触发更新 |

---

## 🔧 常用命令

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 手动生成配置
docker compose exec clash-config-manager python main.py
```

---

## 🔒 安全提示

⚠️ **重要**：不要将以下文件提交到 Git：

- `config/config.ini` - 包含订阅链接
- `output/clash_profile.yaml` - 包含节点信息

这些文件已在 `.gitignore` 中配置。

---

## 📖 文档

- **[config/config.ini.example](config/config.ini.example)** - 配置示例
- **[config/rules.yaml](config/rules.yaml)** - 规则配置

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License
