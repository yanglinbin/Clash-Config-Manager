# 🔧 服务器路径修复指南

## 问题描述
```
[WARN] serverconfig.ini 不存在，使用默认配置
```

**原因**: 部署脚本在查找 `serverconfig.ini` 时使用的是项目根目录，但文件已移动到 `config/` 目录。

## 🚀 快速修复方案

### **方案 1: 重新部署（推荐）**

```bash
# 1. 停止现有服务
sudo systemctl stop clash-webhook
sudo systemctl stop clash-config-updater.timer

# 2. 备份配置文件
sudo cp /opt/clash-config-server/app/config.ini /tmp/config.ini.backup

# 3. 更新项目代码
cd /opt/clash_profile
git pull origin main

# 4. 重新运行部署脚本
sudo ./scripts/deploy_standalone.sh

# 5. 恢复配置文件
sudo cp /tmp/config.ini.backup /opt/clash-config-server/app/config.ini
sudo chown clash:clash /opt/clash-config-server/app/config.ini
```

### **方案 2: 手动修复现有部署**

```bash
# 1. 更新部署目录中的代码文件
cd /opt/clash_profile
git pull origin main

# 2. 复制更新后的文件到部署目录
sudo cp src/webhook_server.py /opt/clash-config-server/app/src/
sudo cp scripts/deploy_standalone.sh /opt/clash-config-server/app/scripts/

# 3. 设置权限
sudo chown clash:clash /opt/clash-config-server/app/src/webhook_server.py
sudo chmod +x /opt/clash-config-server/app/scripts/deploy_standalone.sh

# 4. 重启服务
sudo systemctl restart clash-webhook
sudo systemctl restart clash-config-updater.timer
```

### **方案 3: 创建符号链接（临时方案）**

```bash
# 在部署目录的根目录创建符号链接
cd /opt/clash-config-server/app
sudo ln -s config/serverconfig.ini serverconfig.ini
sudo chown -h clash:clash serverconfig.ini

# 重启服务
sudo systemctl restart clash-webhook
```

## ✅ 验证修复结果

```bash
# 1. 检查服务状态
sudo systemctl status clash-webhook
sudo systemctl status clash-config-updater.timer

# 2. 查看日志，确认不再有警告
sudo journalctl -u clash-webhook -f --since "1 minute ago"

# 3. 测试配置生成
cd /opt/clash-config-server/app
sudo -u clash ../venv/bin/python main.py

# 4. 检查 Webhook 服务
curl http://127.0.0.1:5000/status
```

## 📋 预期结果

修复成功后应该看到：
- ✅ 服务启动时不再有 `serverconfig.ini 不存在` 的警告
- ✅ 如果 `config/serverconfig.ini` 存在，会显示 `正在加载 config/serverconfig.ini...`
- ✅ 服务使用 `config/serverconfig.ini` 中的配置参数
- ✅ Webhook 服务正常运行

## 🎯 推荐操作

**建议使用方案 1（重新部署）**，因为：
- ✅ 确保获得所有最新修复
- ✅ 避免手动操作错误
- ✅ 保证配置一致性
- ✅ 自动处理所有路径问题

**修复完成后，你的部署就会正确读取 `config/serverconfig.ini` 配置了！** 🚀
