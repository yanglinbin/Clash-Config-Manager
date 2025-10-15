# 🚀 部署步骤更新说明

## 📋 新项目结构下的部署变更

由于项目结构已优化，部署步骤需要相应调整：

### 🔄 **主要变更**

#### **1. 配置文件路径变更**
```bash
# 旧方式
cp config.ini.example config.ini

# 新方式 ✅
cp config/config.ini.example config.ini
```

#### **2. 主入口脚本变更**
```bash
# 旧方式
python generate_clash_config.py

# 新方式 ✅
python main.py
```

#### **3. 部署脚本路径变更**
```bash
# 旧方式
chmod +x deploy_standalone.sh
sudo ./deploy_standalone.sh

# 新方式 ✅
chmod +x scripts/deploy_standalone.sh
sudo ./scripts/deploy_standalone.sh
```

### 📁 **新的服务器目录结构**

```
/opt/clash-config-server/
├── app/                       # 项目根目录
│   ├── src/                   # 源代码目录
│   │   ├── generate_clash_config.py
│   │   ├── webhook_server.py
│   │   └── update_service.py
│   ├── config/                # 配置模板目录
│   │   ├── config.ini.example
│   │   ├── rules.yaml
│   │   ├── rules.schema.json
│   │   └── serverconfig.ini
│   ├── docs/                  # 文档目录
│   ├── scripts/               # 脚本目录
│   │   └── deploy_standalone.sh
│   ├── logs/                  # 应用日志目录
│   │   ├── clash_generator.log
│   │   ├── webhook.log
│   │   └── update_service.log
│   ├── output/                # 输出目录
│   │   └── clash_profile.yaml
│   ├── backups/               # 备份目录
│   ├── main.py                # 主入口脚本
│   ├── config.ini             # 用户配置文件
│   └── requirements.txt       # Python 依赖
├── venv/                      # Python 虚拟环境
└── logs/                      # 系统日志目录
```

### ✅ **更新后的完整部署流程**

#### **步骤 1: 本地准备**
```bash
# 1. 克隆项目
git clone <your-repo-url>
cd clash_profile

# 2. 创建配置文件
cp config/config.ini.example config.ini

# 3. 编辑配置文件
nano config.ini

# 4. 本地测试
pip install -r requirements.txt
python main.py
```

#### **步骤 2: 服务器部署**
```bash
# 1. 上传项目到服务器
scp -r . user@server:/tmp/clash_profile/

# 2. 登录服务器
ssh user@server

# 3. 进入项目目录
cd /tmp/clash_profile

# 4. 运行部署脚本
chmod +x scripts/deploy_standalone.sh
sudo ./scripts/deploy_standalone.sh
```

#### **步骤 3: 验证部署**
```bash
# 检查服务状态
sudo systemctl status clash-webhook
sudo systemctl status clash-config-updater.timer

# 检查日志
sudo tail -f /opt/clash-config-server/app/logs/clash_generator.log
sudo tail -f /opt/clash-config-server/app/logs/webhook.log

# 测试配置生成
cd /opt/clash-config-server/app
sudo -u clash ../venv/bin/python main.py
```

### 🔧 **部署脚本改进**

部署脚本已更新以支持新的目录结构：

1. **✅ 自动创建必要目录**: `logs/`, `output/`, `backups/`
2. **✅ 复制完整项目结构**: 包括所有子目录
3. **✅ 智能配置处理**: 自动从示例文件创建配置
4. **✅ 依赖管理**: 使用 `requirements.txt` 安装依赖
5. **✅ 权限设置**: 正确设置所有文件权限

### 🚨 **重要注意事项**

1. **配置文件位置**: `config.ini` 仍保持在项目根目录，便于访问
2. **日志文件**: 应用日志在 `app/logs/`，系统日志在 `logs/`
3. **输出文件**: 生成的配置在 `app/output/clash_profile.yaml`
4. **备份文件**: 自动备份在 `app/backups/` 目录

### 🎯 **兼容性说明**

- ✅ **向后兼容**: 旧的配置文件格式仍然支持
- ✅ **平滑升级**: 现有部署可以直接升级
- ✅ **文档同步**: 所有文档已更新至新结构

### 📞 **如需帮助**

如果在部署过程中遇到问题，请检查：

1. 项目结构是否完整
2. 配置文件路径是否正确
3. 权限设置是否正确
4. 日志文件中的错误信息

**部署脚本已完全适配新的项目结构，可以直接使用！** 🎉
