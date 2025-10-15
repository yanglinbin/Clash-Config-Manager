# Clash 配置服务器

自动化的 Clash 代理配置管理系统，支持多订阅源、自动更新、节点筛选和 GitHub 集成。

## 快速开始

### 1. 配置准备

```bash
# 克隆项目
git clone <your-repo-url>
cd clash_profile

# 创建配置文件
cp config/config.ini.example config.ini

# 编辑配置，填入订阅链接
nano config.ini
```

### 2. 本地测试

```bash
pip install -r requirements.txt
python main.py
```

### 3. 服务器部署

```bash
# 上传到服务器
scp -r clash_profile root@your-server:/root/

# SSH 登录
ssh root@your-server
cd /root/clash_profile

# 运行部署脚本
chmod +x deploy_standalone.sh
./deploy_standalone.sh
```

### 4. 配置 Nginx

将生成的 Nginx 配置添加到你的网站配置中：

```bash
cat /opt/clash-config-server/nginx-config-example.conf
```

### 5. 使用配置

订阅链接：`http://your-domain.com/clash_profile.yaml`

## 核心功能

- ✅ 多订阅源管理
- ✅ 地区节点自动分组
- ✅ 节点关键词过滤
- ✅ 定时自动更新
- ✅ GitHub Webhook 集成
- ✅ 自定义规则配置

## 配置文件

- `config.ini` - 订阅源、地区、过滤规则
- `rules.yaml` - 代理组、规则集配置
- `serverconfig.ini` - 服务器部署参数

## 文档

- [完整部署文档](DEPLOY.md) - 超详细部署指南
- [配置说明](config.ini.example) - 配置文件示例

## 服务管理

```bash
# 查看服务状态
systemctl status clash-webhook

# 手动更新配置
systemctl start clash-config-updater

# 查看日志
journalctl -u clash-webhook -f
```

## 安全提示

⚠️ **不要**将 `config.ini` 提交到 Git！它包含敏感的订阅链接。

## License

MIT

