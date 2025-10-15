# Clash 配置服务器部署完全指南

本文档提供完整的、从零开始的 Clash 配置服务器部署指南。适用于已有网站的服务器环境。

## 目录

1. [系统要求](#系统要求)
2. [架构说明](#架构说明)
3. [前置准备](#前置准备)
4. [配置文件详解](#配置文件详解)
5. [本地测试](#本地测试)
6. [服务器部署](#服务器部署)
7. [Nginx 配置](#nginx-配置)
8. [GitHub Webhook 设置](#github-webhook-设置)
9. [验证与测试](#验证与测试)
10. [日常维护](#日常维护)
11. [故障排除](#故障排除)
12. [高级配置](#高级配置)

---

## 系统要求

### 服务器配置

- **操作系统**: Ubuntu 20.04+ / Debian 10+ / CentOS 7+
- **内存**: 最低 512MB，推荐 1GB+
- **磁盘**: 最低 1GB 可用空间
- **网络**: 公网 IP 或域名

### 软件依赖

自动安装（由部署脚本处理）：
- Python 3.7+
- Git
- Nginx
- Systemd

### 必备信息

1. ✅ 有效的 Clash 订阅链接（至少一个）
2. ✅ 服务器 SSH 访问权限
3. ✅ 域名（可选，建议配置）
4. ✅ GitHub 账号（用于代码托管和 Webhook）

---

## 架构说明

### 系统组件

```
┌─────────────────────────────────────────────────────────────┐
│                      Clash 配置服务器                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐  │
│  │   Nginx      │───▶│  Webhook     │   │   定时器     │  │
│  │ (反向代理)   │    │   服务       │   │  (每小时)    │  │
│  └──────────────┘    └──────────────┘   └──────────────┘  │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │        配置生成器 (main.py -> src/generate_clash_config.py)        │  │
│  └─────────────────────────────────────────────────────┘  │
│                            │                                │
│         ┌──────────────────┼──────────────────┐           │
│         ▼                  ▼                  ▼            │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐        │
│  │config.ini│      │rules.yaml│      │订阅源APIs│        │
│  └──────────┘      └──────────┘      └──────────┘        │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘           │
│                            ▼                                │
│                  ┌──────────────────┐                      │
│                  │clash_profile.yaml│                      │
│                  └──────────────────┘                      │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  Clash 客户端   │
                    └─────────────────┘
```

### 工作流程

1. **配置生成**: 
   - 读取 `config.ini`（订阅源、地区、过滤规则）
   - 读取 `rules.yaml`（代理组、规则集）
   - 从订阅源获取节点信息
   - 生成 `clash_profile.yaml`

2. **自动更新**:
   - **定时更新**: Systemd Timer 每小时触发一次
   - **Webhook 更新**: GitHub 代码推送时自动触发

3. **配置分发**:
   - Nginx 提供静态文件服务
   - Clash 客户端通过 HTTP 订阅

---

## 前置准备

### 步骤 1: 准备订阅链接

收集你的 Clash 订阅链接，例如：

```
https://example1.com/subscribe?token=xxxxx
https://example2.com/api/v1/client/subscribe?token=yyyyy
```

### 步骤 2: 生成 Webhook 密钥

```bash
# 在本地或服务器生成强密码
openssl rand -base64 32
```

保存生成的密钥，稍后用于配置。

### 步骤 3: 克隆或下载项目

```bash
# 方法 1: Git 克隆
git clone <your-github-repo-url> clash_profile
cd clash_profile

# 方法 2: 下载 ZIP
# 下载后解压到 clash_profile 目录
```

---

## 配置文件详解

### config.ini - 核心配置

这是**最重要**的配置文件，包含订阅源和业务逻辑配置。

#### 完整示例

```ini
[proxy_providers]
# 代理提供者配置
# 格式: 名称 = 订阅URL
PROVIDER1 = https://your-subscription-url-1
PROVIDER2 = https://your-subscription-url-2

[regions]
# 地区分组配置
# 格式: 地区名称 = emoji,关键词1,关键词2,...
香港 = 🇭🇰,Hong Kong,HK,港,HongKong
台湾 = 🇹🇼,Taiwan,TW,台,Taipei
日本 = 🇯🇵,Japan,JP,日,Tokyo
美国 = 🇺🇸,United States,US,美,America,USA
新加坡 = 🇸🇬,Singapore,SG,新,狮城

[filter]
# 节点过滤规则 - 排除包含以下关键词的节点
exclude_keywords = 网址,剩余,流量,重置,套餐,如遇,永久,官方,群组,欢迎,官网,频道,个人

[server]
# 更新间隔（秒）
update_interval = 3600

# GitHub Webhook 密钥
webhook_secret = <your-generated-secret>

[files]
# 规则配置文件路径
rules_config = rules.yaml

[clash]
# Clash 基础配置
port = 7890
socks_port = 7891
allow_lan = true
mode = Rule
log_level = info
external_controller = :9090
test_url = http://connectivitycheck.gstatic.com/generate_204
```

#### 配置说明

**[proxy_providers]** - 订阅源管理

```ini
XXAI = https://example.com/subscribe?token=abc123
```

- 名称（XXAI）会用于生成自动选择组，如 "🇭🇰香港自动_XXAI"
- 可以添加任意数量的订阅源
- 支持 HTTP/HTTPS 订阅链接

**[regions]** - 地区分组

```ini
香港 = 🇭🇰,Hong Kong,HK,港,HongKong
```

- 第一项是 emoji 图标
- 后续项是匹配关键词（只要节点名包含任一关键词即匹配）
- 会为每个订阅源的每个地区生成一个自动选择组

**[filter]** - 节点过滤

```ini
exclude_keywords = 网址,剩余,流量
```

- 包含这些关键词的节点会被排除
- 用于过滤订阅信息节点和广告节点
- 使用正则表达式负向前瞻实现

**[server]** - 服务器参数

- `update_interval`: 自动更新间隔（秒），默认 3600（1小时）
- `webhook_secret`: GitHub Webhook 的验证密钥

### serverconfig.ini - 部署配置

这个文件控制服务器基础设施参数，**通常不需要修改**。

#### 关键配置项

```ini
[deployment]
# 安装路径 - 默认 /opt/clash-config-server
install_dir = /opt/clash-config-server

# 服务用户 - 默认 clash
service_user = clash

[network]
# Webhook 服务监听地址 - 默认 127.0.0.1（仅本机）
webhook_host = 127.0.0.1

# Webhook 服务端口 - 默认 5000
webhook_port = 5000

[nginx]
# API 路径前缀 - 默认 /clash
api_prefix = /clash
```

#### 何时需要修改

1. **端口冲突**: 如果 5000 端口已被占用
2. **自定义路径**: 想要使用不同的安装目录
3. **URL 路径**: 想要自定义 API 访问路径

### rules.yaml - 规则配置

定义代理组、规则集和自定义规则，**一般不需要修改**。

结构：
```yaml
rule_providers:      # 规则集来源
proxy_groups:        # 代理组定义
  main_groups:       # 主要代理组
  special_groups:    # 特殊组（如广告拦截）
custom_rules:        # 自定义规则
ruleset_rules:       # 规则集引用
```

---

## 本地测试

在部署到服务器之前，**强烈建议**先在本地测试配置生成。

### 步骤 1: 安装依赖

```bash
cd clash_profile
pip install -r requirements.txt
```

### 步骤 2: 创建配置文件

```bash
cp config/config.ini.example config.ini
nano config.ini  # 或使用其他编辑器
```

填入你的实际订阅链接。

### 步骤 3: 测试生成

```bash
python main.py
```

### 预期输出

```
2024-01-01 12:00:00 - INFO - 🚀 开始生成 Clash 配置
2024-01-01 12:00:00 - INFO - ==================================================
2024-01-01 12:00:00 - INFO - 已加载配置文件: config.ini
2024-01-01 12:00:00 - INFO - 已加载规则配置文件: rules.yaml
2024-01-01 12:00:00 - INFO - 找到 2 个代理提供者: ['XXAI', 'NAIYUN']
2024-01-01 12:00:00 - INFO - 找到 5 个地区配置: ['香港', '台湾', '日本', '美国', '新加坡']
2024-01-01 12:00:00 - INFO - ✅ 配置文件已生成: clash_profile.yaml
2024-01-01 12:00:00 - INFO - 📊 文件大小: 45678 字节
2024-01-01 12:00:00 - INFO - 📊 代理组数量: 25
2024-01-01 12:00:00 - INFO - 📊 规则数量: 150
2024-01-01 12:00:00 - INFO - 🎉 配置生成完成!
```

### 步骤 4: 验证生成的配置

```bash
# 查看文件大小（应该大于 10KB）
ls -lh clash_profile.yaml

# 查看代理组
grep "^  - name:" clash_profile.yaml | head -20

# 检查是否有你的订阅源
grep "proxy-providers:" -A 10 clash_profile.yaml
```

---

## 服务器部署

### 步骤 1: 上传项目到服务器

```bash
# 从本地上传
scp -r clash_profile root@your-server-ip:/root/

# 或者直接在服务器上克隆
ssh root@your-server-ip
cd /root
git clone <your-repo-url> clash_profile
cd clash_profile
```

### 步骤 2: 准备配置文件

```bash
# 在服务器上创建配置
cp config/config.ini.example config.ini
nano config.ini

# 填入你的订阅链接和 webhook_secret
```

### 步骤 3: 检查 serverconfig.ini（可选）

```bash
cat serverconfig.ini

# 如果需要修改端口或路径，现在编辑
nano serverconfig.ini
```

### 步骤 4: 运行部署脚本

```bash
# 添加执行权限
chmod +x scripts/deploy_standalone.sh

# 运行部署（需要 root 权限）
./scripts/deploy_standalone.sh
```

### 部署过程

脚本会自动执行以下操作：

1. ✅ 检测系统类型（Ubuntu/Debian/CentOS）
2. ✅ 加载 serverconfig.ini 配置
3. ✅ 安装系统依赖（Python, Git, Systemd）
4. ✅ 创建服务用户 `clash`
5. ✅ 创建目录结构 `/opt/clash-config-server/`
6. ✅ 部署应用文件
7. ✅ 创建 Python 虚拟环境
8. ✅ 安装 Python 依赖
9. ✅ 创建 Systemd 服务
   - `clash-webhook.service` - Webhook 监听服务
   - `clash-config-updater.service` - 配置更新服务
   - `clash-config-updater.timer` - 定时触发器
10. ✅ 启动服务
11. ✅ 生成初始配置
12. ✅ 生成 Nginx 配置示例

### 预期输出

```
[INFO] 开始部署 Clash 配置服务器（独立部署模式）...
[INFO] 检测到 Ubuntu 系统
[INFO] 正在加载 serverconfig.ini...
[INFO] 配置加载完成
[STEP] 安装系统依赖...
[INFO] 系统依赖安装完成
[STEP] 创建服务用户...
[INFO] 用户 clash 创建成功
[STEP] 创建目录结构...
[INFO] 目录结构创建完成
[STEP] 部署应用文件...
[INFO] 应用文件部署完成
[STEP] 创建 systemd 服务...
[INFO] systemd 服务创建完成
[STEP] 启动服务...
[INFO] 服务启动完成
[STEP] 生成 Nginx 配置示例...
[INFO] Nginx 配置示例已保存到: /opt/clash-config-server/nginx-config-example.conf
[STEP] 部署完成！
==================== 部署信息 ====================
安装目录: /opt/clash-config-server
配置文件: /opt/clash-config-server/app/config.ini
规则文件: /opt/clash-config-server/app/config/rules.yaml
日志目录: /opt/clash-config-server/logs/

下一步操作:
1. 编辑配置文件，设置你的代理提供商:
   nano /opt/clash-config-server/app/config.ini

2. 将以下 Nginx 配置添加到你现有的网站配置中:
   cat /opt/clash-config-server/nginx-config-example.conf

3. 重新加载 Nginx:
   nginx -t && systemctl reload nginx

访问地址（根据你的域名调整）:
配置文件: http://your-domain.com/clash_profile.yaml
Webhook:  http://your-domain.com/clash/webhook
状态页面: http://your-domain.com/clash/status

服务管理:
查看状态: systemctl status clash-webhook
查看日志: journalctl -u clash-webhook -f
重启服务: systemctl restart clash-webhook
手动更新: systemctl start clash-config-updater

注意事项:
1. 请确保端口 5000 未被占用
2. Webhook 服务监听在 127.0.0.1:5000，通过 Nginx 反向代理访问
3. 配置 GitHub Webhook 地址: http://your-domain.com/clash/webhook
4. 记得在 config.ini 中设置 webhook_secret
==================================================
```

---

## Nginx 配置

部署脚本会生成 Nginx 配置示例，你需要手动集成到现有网站配置中。

### 步骤 1: 查看生成的配置

```bash
cat /opt/clash-config-server/nginx-config-example.conf
```

### 步骤 2: 选择集成方式

#### 方式 A: 子路径方式（推荐）

适用于：在现有域名下添加 Clash 配置服务。

**优点**: 不需要额外域名，配置简单
**缺点**: 路径较长

**示例**: `https://yourdomain.com/clash_profile.yaml`

##### 操作步骤

1. 编辑你的主站 Nginx 配置：

```bash
nano /etc/nginx/sites-available/your-site.conf
```

2. 在 `server` 块中添加以下内容：

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # 你现有的网站配置
    location / {
        # 你的网站配置
    }
    
    # ====== Clash 配置服务器 ======
    
    # 配置文件访问
    location /clash_profile.yaml {
        alias /opt/clash-config-server/app/output/clash_profile.yaml;
        add_header Content-Type "text/plain; charset=utf-8";
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        add_header Access-Control-Allow-Origin *;
    }
    
    # Webhook 接口
    location /clash/webhook {
        proxy_pass http://127.0.0.1:5000/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 状态页面
    location /clash/status {
        proxy_pass http://127.0.0.1:5000/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 手动更新接口
    location /clash/manual-update {
        proxy_pass http://127.0.0.1:5000/manual-update;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 管理界面
    location /clash/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 方式 B: 子域名方式

适用于：有多个子域名，想要独立域名访问。

**优点**: URL 简洁美观
**缺点**: 需要配置子域名 DNS

**示例**: `https://clash.yourdomain.com/clash_profile.yaml`

##### 操作步骤

1. 配置 DNS 解析：

```
类型: A
主机记录: clash
记录值: 你的服务器IP
```

2. 创建新的 Nginx 配置：

```bash
nano /etc/nginx/sites-available/clash.conf
```

3. 添加以下内容：

```nginx
server {
    listen 80;
    server_name clash.yourdomain.com;
    
    root /opt/clash-config-server/static;
    
    # 配置文件访问
    location /clash_profile.yaml {
        alias /opt/clash-config-server/app/output/clash_profile.yaml;
        add_header Content-Type "text/plain; charset=utf-8";
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        add_header Access-Control-Allow-Origin *;
    }
    
    # API 接口
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. 启用配置：

```bash
ln -s /etc/nginx/sites-available/clash.conf /etc/nginx/sites-enabled/
```

### 步骤 3: 测试并重载 Nginx

```bash
# 测试配置语法
nginx -t

# 如果测试通过，重载配置
systemctl reload nginx
```

### 步骤 4: 配置 SSL（推荐）

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx

# 获取 SSL 证书
# 子路径方式
certbot --nginx -d yourdomain.com

# 子域名方式
certbot --nginx -d clash.yourdomain.com
```

---

## GitHub Webhook 设置

配置 GitHub Webhook 实现代码推送自动更新。

### 步骤 1: 在 GitHub 仓库中配置

1. 打开你的 GitHub 仓库
2. 进入 `Settings` > `Webhooks`
3. 点击 `Add webhook`

### 步骤 2: 填写 Webhook 信息

- **Payload URL**: 
  - 子路径方式: `http://yourdomain.com/clash/webhook`
  - 子域名方式: `http://clash.yourdomain.com/webhook`
  - 如果已配置 SSL: 使用 `https://`

- **Content type**: 选择 `application/json`

- **Secret**: 填入你在 `config.ini` 中设置的 `webhook_secret`

- **Which events would you like to trigger this webhook?**
  - 选择 `Just the push event`

- **Active**: 勾选

### 步骤 3: 保存并测试

1. 点击 `Add webhook`
2. GitHub 会自动发送一个 ping 事件
3. 查看 `Recent Deliveries`，应该看到绿色勾号

### 步骤 4: 测试自动更新

```bash
# 修改配置文件
nano config.ini

# 提交并推送
git add config.ini.example rules.yaml
git commit -m "更新配置"
git push

# 查看服务器日志
journalctl -u clash-webhook -f
```

预期日志输出：

```
收到 Webhook 请求: push
收到 push 事件: your-username/clash_profile, ref: refs/heads/main
提交数量: 1
检测到相关文件变更: config.ini
代码更新成功
配置文件重新生成成功
Webhook 处理完成
```

---

## 验证与测试

### 1. 检查服务状态

```bash
# 检查 Webhook 服务
systemctl status clash-webhook
# 应该显示: active (running)

# 检查定时器
systemctl status clash-config-updater.timer
# 应该显示: active (waiting)

# 查看定时器下次触发时间
systemctl list-timers | grep clash
```

### 2. 检查配置文件

```bash
# 检查文件是否存在
ls -lh /opt/clash-config-server/app/clash_profile.yaml

# 查看文件内容
head -50 /opt/clash-config-server/app/clash_profile.yaml
```

### 3. 测试 Web 访问

```bash
# 测试配置文件访问
curl -I http://yourdomain.com/clash_profile.yaml

# 预期输出: HTTP/1.1 200 OK

# 测试状态页面
curl http://yourdomain.com/clash/status

# 预期输出: JSON 格式的状态信息
```

### 4. 在 Clash 客户端中测试

#### Clash for Windows

1. 打开 Clash for Windows
2. 进入 `Profiles`
3. 在地址栏输入: `http://yourdomain.com/clash_profile.yaml`
4. 点击 `Download`
5. 双击配置文件激活
6. 检查是否能看到所有代理节点和代理组

#### ClashX (macOS)

1. 点击菜单栏图标
2. `配置` > `托管配置` > `管理`
3. 点击 `添加`
4. 名称: `My Clash Config`
5. URL: `http://yourdomain.com/clash_profile.yaml`
6. 保存并选择配置

### 5. 测试手动更新

```bash
# 方法 1: 使用 systemctl
systemctl start clash-config-updater

# 方法 2: 使用 API
curl -X POST http://yourdomain.com/clash/manual-update

# 查看更新日志
tail -f /opt/clash-config-server/logs/updater.log
```

---

## 日常维护

### 查看日志

```bash
# Webhook 服务日志
journalctl -u clash-webhook -f

# 或查看文件日志
tail -f /opt/clash-config-server/logs/webhook.log

# 更新服务日志
tail -f /opt/clash-config-server/logs/updater.log

# 配置生成日志
tail -f /opt/clash-config-server/app/clash_generator.log
```

### 修改配置

```bash
# 进入应用目录
cd /opt/clash-config-server/app

# 编辑配置文件
sudo nano config.ini

# 手动重新生成配置
sudo -u clash /opt/clash-config-server/venv/bin/python main.py

# 重启服务（如果修改了服务器配置）
systemctl restart clash-webhook
```

### 备份配置

```bash
# 备份配置文件
cp /opt/clash-config-server/app/config.ini ~/config.ini.backup.$(date +%Y%m%d)

# 备份整个应用目录
tar -czf ~/clash-backup-$(date +%Y%m%d).tar.gz /opt/clash-config-server/

# 查看自动备份
ls -lh /opt/clash-config-server/backups/
```

### 更新代码

```bash
cd /opt/clash-config-server/app

# 拉取最新代码
git pull origin main

# 重启服务
systemctl restart clash-webhook

# 手动更新配置
systemctl start clash-config-updater
```

### 清理日志

```bash
# 清理旧日志
find /opt/clash-config-server/logs/ -name "*.log" -mtime +30 -delete

# 清理旧备份（保留最近10个）
cd /opt/clash-config-server/backups
ls -t clash_profile_*.yaml | tail -n +11 | xargs -r rm
```

---

## 故障排除

### 问题 1: 配置文件生成失败

**症状**: 
```
❌ 配置生成失败
```

**排查步骤**:

```bash
# 1. 检查配置文件是否存在
ls -l /opt/clash-config-server/app/config.ini

# 2. 检查配置文件语法
cat /opt/clash-config-server/app/config.ini

# 3. 手动运行生成器查看错误
cd /opt/clash-config-server/app
sudo -u clash /opt/clash-config-server/venv/bin/python main.py

# 4. 检查订阅链接是否有效
curl -I "你的订阅URL"
```

**解决方案**:
- 确认 `config.ini` 格式正确
- 确认订阅链接可访问
- 检查网络连接

### 问题 2: Webhook 不工作

**症状**:
- GitHub 显示 Webhook 失败
- 推送代码后配置未更新

**排查步骤**:

```bash
# 1. 检查服务状态
systemctl status clash-webhook

# 2. 查看日志
journalctl -u clash-webhook -n 50

# 3. 测试 Webhook 接口
curl -X POST http://127.0.0.1:5000/webhook

# 4. 检查 Nginx 配置
nginx -t
curl -I http://yourdomain.com/clash/webhook

# 5. 检查防火墙
ufw status
```

**解决方案**:
- 确认服务正在运行
- 检查 Nginx 反向代理配置
- 验证 webhook_secret 是否匹配
- 检查防火墙规则

### 问题 3: 端口冲突

**症状**:
```
Address already in use: 127.0.0.1:5000
```

**解决方案**:

```bash
# 1. 查找占用端口的进程
lsof -i:5000

# 2. 修改 serverconfig.ini
nano serverconfig.ini
# 修改 webhook_port = 5001

# 3. 重新部署或手动修改 systemd 服务
nano /etc/systemd/system/clash-webhook.service
# 确保使用新端口

# 4. 更新 Nginx 配置
nano /etc/nginx/sites-available/your-site.conf
# proxy_pass http://127.0.0.1:5001

# 5. 重新加载
systemctl daemon-reload
systemctl restart clash-webhook
nginx -t && systemctl reload nginx
```

### 问题 4: Clash 客户端无法订阅

**症状**:
- 客户端显示 "下载失败"
- 配置为空

**排查步骤**:

```bash
# 1. 测试配置文件是否可访问
curl http://yourdomain.com/clash_profile.yaml

# 2. 检查文件大小
ls -lh /opt/clash-config-server/app/clash_profile.yaml

# 3. 检查文件权限
ls -la /opt/clash-config-server/app/clash_profile.yaml
# 应该是 clash:clash 所有

# 4. 检查 Nginx 日志
tail -f /var/log/nginx/error.log
```

**解决方案**:
- 确认文件存在且大小正常（>1KB）
- 检查文件权限
- 验证 Nginx 配置正确
- 确认域名 DNS 解析正确

### 问题 5: 节点过滤不生效

**症状**:
- 仍然看到包含 "网址"、"流量" 等关键词的节点

**排查步骤**:

```bash
# 1. 检查配置
grep exclude_keywords /opt/clash-config-server/app/config.ini

# 2. 查看生成的配置
grep -A 5 "filter:" /opt/clash-config-server/app/clash_profile.yaml

# 3. 检查日志
tail -f /opt/clash-config-server/app/clash_generator.log
```

**解决方案**:
- 确认 `exclude_keywords` 配置正确
- 重新生成配置
- 检查节点名称是否包含关键词

### 问题 6: SSL 证书问题

**症状**:
- HTTPS 访问失败
- 证书过期

**解决方案**:

```bash
# 检查证书状态
certbot certificates

# 手动续期
certbot renew

# 自动续期
certbot renew --dry-run

# 配置自动续期
systemctl enable certbot.timer
systemctl start certbot.timer
```

---

## 高级配置

### 自定义更新间隔

```bash
# 编辑定时器
systemctl edit clash-config-updater.timer

# 添加以下内容
[Timer]
OnCalendar=
OnCalendar=*:0/30  # 每30分钟一次

# 重载配置
systemctl daemon-reload
systemctl restart clash-config-updater.timer
```

### 添加访问控制

在 Nginx 中限制配置文件访问：

```nginx
location /clash_profile.yaml {
    alias /opt/clash-config-server/app/clash_profile.yaml;
    
    # IP 白名单
    allow 1.2.3.4;
    allow 192.168.1.0/24;
    deny all;
    
    # 或使用 HTTP Basic Auth
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

### 配置日志轮转

```bash
# 创建 logrotate 配置
cat > /etc/logrotate.d/clash-config << EOF
/opt/clash-config-server/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 clash clash
}
EOF
```

### 监控和告警

使用 systemd 发送告警邮件：

```bash
# 编辑服务
systemctl edit clash-webhook.service

# 添加
[Service]
OnFailure=status-email@%n.service

# 配置邮件通知
apt install mailutils
```

### 多环境部署

```bash
# 创建测试环境配置
cp config.ini config.test.ini

# 使用不同配置运行
python main.py --config config.test.ini
```

---

## 附录

### 完整文件结构

```
/opt/clash-config-server/
├── app/
│   ├── config.ini              # 核心配置（不要提交到 Git）
│   ├── src/                    # 源代码目录
│   │   ├── generate_clash_config.py
│   │   ├── webhook_server.py
│   │   └── update_service.py
│   ├── config/                # 配置文件目录
│   │   ├── serverconfig.ini
│   │   └── rules.yaml
│   ├── main.py                # 主入口脚本
│   ├── clash_profile.yaml      # 生成的配置（不要提交到 Git）
│   ├── clash_generator.log
│   ├── webhook.log
│   └── update_service.log
├── venv/                       # Python 虚拟环境
├── logs/                       # 日志目录
│   ├── webhook.log
│   └── updater.log
├── data/                       # 数据目录
│   ├── profiles/
│   └── ruleset/
├── backups/                    # 备份目录
│   └── clash_profile_*.yaml
├── static/                     # 静态文件
└── nginx-config-example.conf   # Nginx 配置示例
```

### 常用命令速查

```bash
# 服务管理
systemctl start clash-webhook
systemctl stop clash-webhook
systemctl restart clash-webhook
systemctl status clash-webhook

# 日志查看
journalctl -u clash-webhook -f
journalctl -u clash-config-updater -f
tail -f /opt/clash-config-server/logs/webhook.log

# 手动更新
systemctl start clash-config-updater
curl -X POST http://localhost:5000/manual-update

# 配置测试
nginx -t
python main.py

# 备份
tar -czf ~/clash-backup.tar.gz /opt/clash-config-server/
```

### 性能优化建议

1. **使用 CDN**: 将配置文件放到 CDN，减轻服务器压力
2. **启用缓存**: Nginx 添加适当的缓存头
3. **压缩传输**: 启用 gzip 压缩
4. **限流**: 使用 Nginx limit_req 限制请求频率

### 安全最佳实践

1. ✅ 使用 HTTPS
2. ✅ 设置强 webhook_secret
3. ✅ 限制配置文件访问（IP 白名单或 Auth）
4. ✅ 定期更新系统和依赖
5. ✅ 使用防火墙限制端口访问
6. ✅ 定期备份配置
7. ✅ 监控服务状态
8. ✅ 不要将 config.ini 提交到公开仓库

---

## 总结

恭喜！你已经成功部署了 Clash 配置服务器。现在你可以：

- ✅ 通过 URL 订阅 Clash 配置
- ✅ 自动更新订阅源
- ✅ GitHub 推送自动触发配置更新
- ✅ 灵活配置节点过滤和分组
- ✅ 集中管理多个订阅源

如遇问题，请参考[故障排除](#故障排除)章节或查看日志文件。

**祝你使用愉快！** 🎉

