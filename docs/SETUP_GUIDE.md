# 🚀 Clash 配置服务器快速开始指南

本指南将帮助你从零开始设置 Clash 配置服务器。

## 📋 前提条件

- 一台 Linux 服务器（Ubuntu/Debian/CentOS）
- 有效的代理订阅链接
- （可选）一个域名
- 基本的 Linux 命令知识

## 🎯 第一步：准备工作

### 1. 克隆或下载项目

```bash
# 方法 1: 使用 Git 克隆
git clone https://github.com/你的用户名/clash_profile.git
cd clash_profile

# 方法 2: 直接下载 ZIP 并解压
# 下载后解压到 clash_profile 目录
```

### 2. 创建配置文件

```bash
# 复制示例配置文件
cp config.ini.example config.ini

# 编辑配置文件
nano config.ini
```

### 3. 填写配置信息

在 `config.ini` 中填入你的信息：

```ini
[proxy_providers]
# 将示例替换为你的实际订阅链接
XXAI = http://your-actual-subscription-url-1
NAIYUN = https://your-actual-subscription-url-2
KITTY = https://your-actual-subscription-url-3

# 可以添加更多提供商
# MY_PROVIDER = https://your-subscription-url

[server]
# 修改 webhook 密钥（重要！）
webhook_secret = 生成一个强密码
```

**生成强密码的方法**：
```bash
# 使用 openssl 生成随机密钥
openssl rand -base64 32
```

## 🔧 第二步：本地测试

在部署到服务器之前，建议先在本地测试：

### 1. 安装 Python 依赖

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 测试配置生成

```bash
# 运行配置生成器
python main.py
```

如果成功，你会看到：
```
✅ 配置文件已生成: clash_profile.yaml
📊 文件大小: XXXXX 字节
```

### 3. 检查生成的配置

```bash
# 查看生成的配置文件
head -50 clash_profile.yaml

# 检查代理组
grep "name:" clash_profile.yaml | head -20
```

## 🌐 第三步：部署到服务器

### 场景 A：全新服务器（没有运行网站）

```bash
# 上传项目到服务器
scp -r clash_profile root@your-server-ip:/root/

# SSH 登录服务器
ssh root@your-server-ip

# 进入项目目录
cd /root/clash_profile

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 场景 B：已有网站的服务器（推荐）

```bash
# 上传项目到服务器
scp -r clash_profile root@your-server-ip:/root/

# SSH 登录服务器
ssh root@your-server-ip

# 进入项目目录
cd /root/clash_profile

# 运行独立部署脚本
chmod +x deploy_standalone.sh
./deploy_standalone.sh
```

**然后按照 [DEPLOY_EXISTING_SITE.md](DEPLOY_EXISTING_SITE.md) 的指引配置 Nginx。**

## 📱 第四步：配置 Clash 客户端

### 1. 获取订阅链接

根据你的部署方式，订阅链接为：

- **全新服务器**: `http://your-server-ip/clash_profile.yaml`
- **已有网站（子路径）**: `http://your-domain.com/clash_profile.yaml`
- **已有网站（子域名）**: `http://clash.your-domain.com/clash_profile.yaml`

### 2. 在 Clash 客户端中添加订阅

#### Clash for Windows
1. 打开 Clash for Windows
2. 点击 `Profiles`
3. 在地址栏输入订阅链接
4. 点击 `Download`
5. 双击配置文件以激活

#### ClashX (macOS)
1. 点击菜单栏图标
2. `配置` > `托管配置` > `管理`
3. 点击 `添加`
4. 输入名称和订阅链接
5. 点击 `确定`

#### Clash for Android
1. 点击 `配置`
2. 点击 `+` 按钮
3. 选择 `URL`
4. 输入名称和订阅链接
5. 保存并选择配置

## 🔄 第五步：配置自动更新

### 1. 设置 GitHub Webhook

1. 在 GitHub 仓库中，进入 `Settings` > `Webhooks`
2. 点击 `Add webhook`
3. 填写信息：
   - **Payload URL**: 
     - 全新服务器: `http://your-server-ip/webhook`
     - 已有网站: `http://your-domain.com/clash/webhook`
   - **Content type**: `application/json`
   - **Secret**: 与 `config.ini` 中的 `webhook_secret` 相同
   - **Events**: 选择 `Just the push event`
4. 点击 `Add webhook`

### 2. 测试自动更新

```bash
# 修改配置文件
nano config.ini

# 提交并推送到 GitHub
git add config.ini.example rules.yaml
git commit -m "更新配置"
git push

# 观察服务器日志
tail -f /opt/clash-config-server/logs/webhook.log
```

## ✅ 第六步：验证部署

### 1. 检查服务状态

```bash
# 检查 Webhook 服务
systemctl status clash-webhook

# 检查定时更新
systemctl status clash-config-updater.timer

# 查看日志
tail -f /opt/clash-config-server/logs/webhook.log
```

### 2. 测试配置文件访问

```bash
# 测试配置文件是否可访问
curl http://your-domain.com/clash_profile.yaml

# 或使用浏览器访问
# http://your-domain.com/clash_profile.yaml
```

### 3. 测试手动更新

```bash
# 方法 1: 使用 systemd
systemctl start clash-config-updater

# 方法 2: 使用 API
curl -X POST http://your-domain.com/clash/manual-update
```

## 🔒 第七步：安全加固（可选但推荐）

### 1. 配置 SSL/HTTPS

```bash
# 安装 certbot
apt install certbot python3-certbot-nginx

# 获取证书
certbot --nginx -d your-domain.com

# 或（子域名方案）
certbot --nginx -d clash.your-domain.com
```

### 2. 配置防火墙

```bash
# 安装 ufw
apt install ufw

# 允许必要端口
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS

# 启用防火墙
ufw enable
```

### 3. 限制访问频率（在 Nginx 中）

```nginx
# 在 http 块中添加
limit_req_zone $binary_remote_addr zone=clash_limit:10m rate=10r/m;

# 在 location 块中添加
location /clash_profile.yaml {
    limit_req zone=clash_limit burst=5;
    # 其他配置...
}
```

## 📊 第八步：日常维护

### 查看日志

```bash
# Webhook 服务日志
tail -f /opt/clash-config-server/logs/webhook.log

# 配置生成日志
tail -f /opt/clash-config-server/logs/generator.log

# 更新服务日志
journalctl -u clash-config-updater -f
```

### 手动更新配置

```bash
# 进入应用目录
cd /opt/clash-config-server/app

# 编辑配置
nano config.ini

# 手动重新生成
sudo -u clash /opt/clash-config-server/venv/bin/python main.py

# 重启服务
systemctl restart clash-webhook
```

### 备份配置

```bash
# 备份配置文件
cp /opt/clash-config-server/app/config.ini ~/config.ini.backup

# 备份数据目录
tar -czf clash-backup-$(date +%Y%m%d).tar.gz /opt/clash-config-server/
```

## ❓ 常见问题

### Q1: 配置文件生成失败？

**A**: 检查以下几点：
1. 确认 `config.ini` 中的订阅链接有效
2. 检查网络连接
3. 查看日志：`tail -f /opt/clash-config-server/logs/generator.log`

### Q2: Webhook 不工作？

**A**: 检查：
1. Webhook 服务是否运行：`systemctl status clash-webhook`
2. Nginx 配置是否正确：`nginx -t`
3. GitHub Webhook 密钥是否匹配
4. 查看日志：`tail -f /opt/clash-config-server/logs/webhook.log`

### Q3: 节点无法连接？

**A**: 这通常与服务器配置无关，检查：
1. Clash 客户端是否正确选择了配置
2. 代理节点是否有效
3. 防火墙是否阻止了代理端口

### Q4: 如何添加新的代理提供商？

**A**: 编辑 `config.ini`：
```ini
[proxy_providers]
# 添加新的提供商
NEW_PROVIDER = https://your-new-subscription-url
```
然后重新生成配置。

### Q5: 如何修改地区分组？

**A**: 编辑 `config.ini` 的 `[regions]` 部分：
```ini
[regions]
# 添加新地区
韩国 = 🇰🇷,Korea,KR,韩,Seoul
```

### Q6: 如何更新规则集？

**A**: 编辑 `rules.yaml`，修改后推送到 GitHub，Webhook 会自动更新。

## 🎓 进阶配置

### 自定义规则

编辑 `rules.yaml` 中的 `custom_rules` 部分：

```yaml
custom_rules:
  my_custom_rules:
    - "DOMAIN-SUFFIX,example.com,🚀海外代理"
    - "IP-CIDR,192.168.1.0/24,DIRECT"
```

### 调整更新频率

编辑 `config.ini`：

```ini
[server]
update_interval = 7200  # 2小时更新一次（秒）
```

然后重启定时器：
```bash
systemctl restart clash-config-updater.timer
```

### 添加更多代理组

编辑 `rules.yaml` 的 `proxy_groups.main_groups`：

```yaml
proxy_groups:
  main_groups:
    - name: "🎵音乐平台"
      type: select
      description: "音乐流媒体专用"
```

## 📚 相关文档

- [README.md](README.md) - 项目概述
- [CONFIGURATION.md](CONFIGURATION.md) - 详细配置说明
- [DEPLOY_EXISTING_SITE.md](DEPLOY_EXISTING_SITE.md) - 已有网站部署指南

## 🆘 获取帮助

如果遇到问题：
1. 查看日志文件
2. 阅读相关文档
3. 在 GitHub 提交 Issue
4. 参考常见问题部分

---

**祝你使用愉快！** 🎉
