#!/bin/bash

# Clash 配置服务器部署脚本 - 独立部署版本（适用于已有网站的服务器）
# 此版本不会创建独立的 Nginx 配置，而是输出配置供你手动添加到现有网站

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置变量（可被 serverconfig.ini 覆盖）
PROJECT_NAME="clash-config-server"
INSTALL_DIR="/opt/clash-config-server"
SERVICE_USER="clash"
SERVICE_GROUP="clash"
SYSTEMD_DIR="/etc/systemd/system"
WEBHOOK_HOST="127.0.0.1"
WEBHOOK_PORT="5000"
WEBHOOK_SERVICE_NAME="clash-webhook"
UPDATER_SERVICE_NAME="clash-config-updater"
TIMER_NAME="clash-config-updater.timer"

# 加载服务器配置文件
load_server_config() {
    if [[ -f "serverconfig.ini" ]]; then
        log_info "正在加载 serverconfig.ini..."
        
        # 使用 Python 读取配置文件
        eval $(python3 << 'EOF'
import configparser
import sys

config = configparser.ConfigParser()
config.read('serverconfig.ini', encoding='utf-8')

# 导出为环境变量
if 'deployment' in config:
    for key, value in config['deployment'].items():
        print(f"export CFG_{key.upper()}='{value}'")

if 'network' in config:
    for key, value in config['network'].items():
        print(f"export CFG_{key.upper()}='{value}'")

if 'systemd' in config:
    for key, value in config['systemd'].items():
        print(f"export CFG_{key.upper()}='{value}'")
EOF
)
        
        # 应用配置
        [[ -n "$CFG_PROJECT_NAME" ]] && PROJECT_NAME="$CFG_PROJECT_NAME"
        [[ -n "$CFG_INSTALL_DIR" ]] && INSTALL_DIR="$CFG_INSTALL_DIR"
        [[ -n "$CFG_SERVICE_USER" ]] && SERVICE_USER="$CFG_SERVICE_USER"
        [[ -n "$CFG_SERVICE_GROUP" ]] && SERVICE_GROUP="$CFG_SERVICE_GROUP"
        [[ -n "$CFG_WEBHOOK_HOST" ]] && WEBHOOK_HOST="$CFG_WEBHOOK_HOST"
        [[ -n "$CFG_WEBHOOK_PORT" ]] && WEBHOOK_PORT="$CFG_WEBHOOK_PORT"
        [[ -n "$CFG_WEBHOOK_SERVICE_NAME" ]] && WEBHOOK_SERVICE_NAME="$CFG_WEBHOOK_SERVICE_NAME"
        [[ -n "$CFG_UPDATER_SERVICE_NAME" ]] && UPDATER_SERVICE_NAME="$CFG_UPDATER_SERVICE_NAME"
        [[ -n "$CFG_TIMER_NAME" ]] && TIMER_NAME="$CFG_TIMER_NAME"
        
        log_info "配置加载完成"
    else
        log_warn "serverconfig.ini 不存在，使用默认配置"
    fi
}

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        exit 1
    fi
}

# 检查系统类型
check_system() {
    if [[ -f /etc/debian_version ]]; then
        OS="debian"
        log_info "检测到 Debian/Ubuntu 系统"
    elif [[ -f /etc/redhat-release ]]; then
        OS="redhat"
        log_info "检测到 RedHat/CentOS 系统"
    else
        log_error "不支持的操作系统"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_step "安装系统依赖..."
    
    if [[ $OS == "debian" ]]; then
        apt update
        apt install -y python3 python3-pip python3-venv git curl systemd
    elif [[ $OS == "redhat" ]]; then
        yum update -y
        yum install -y python3 python3-pip git curl systemd
    fi
    
    log_info "系统依赖安装完成"
}

# 创建用户
create_user() {
    log_step "创建服务用户..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER
        log_info "用户 $SERVICE_USER 创建成功"
    else
        log_info "用户 $SERVICE_USER 已存在"
    fi
}

# 创建目录结构
create_directories() {
    log_step "创建目录结构..."
    
    mkdir -p $INSTALL_DIR/{app,logs,data,static}
    mkdir -p $INSTALL_DIR/data/{profiles,ruleset}
    
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod -R 755 $INSTALL_DIR
    
    log_info "目录结构创建完成"
}

# 部署应用文件
deploy_app() {
    log_step "部署应用文件..."
    
    # 复制整个项目目录结构
    log_info "复制项目文件..."
    cp -r . $INSTALL_DIR/app/
    
    # 创建必要的目录
    mkdir -p $INSTALL_DIR/app/logs
    mkdir -p $INSTALL_DIR/app/output
    mkdir -p $INSTALL_DIR/app/backups
    
    # 确保配置文件存在
    if [[ ! -f "$INSTALL_DIR/app/config.ini" ]]; then
        if [[ -f "$INSTALL_DIR/app/config/config.ini.example" ]]; then
            log_warn "config.ini 不存在，从示例文件创建"
            cp $INSTALL_DIR/app/config/config.ini.example $INSTALL_DIR/app/config.ini
        else
            log_error "配置文件不存在，请先创建 config.ini"
            exit 1
        fi
    fi
    
    # 创建 Python 虚拟环境
    cd $INSTALL_DIR
    python3 -m venv venv
    source venv/bin/activate
    
    # 安装依赖
    if [[ -f "$INSTALL_DIR/app/requirements.txt" ]]; then
        pip install -r $INSTALL_DIR/app/requirements.txt
    else
        pip install pyyaml requests flask gunicorn configparser
    fi
    
    # 设置权限
    chown -R $SERVICE_USER:$SERVICE_GROUP $INSTALL_DIR
    chmod +x $INSTALL_DIR/app/main.py
    chmod +x $INSTALL_DIR/app/src/*.py
    
    log_info "应用文件部署完成"
}

# 创建 systemd 服务
create_systemd_service() {
    log_step "创建 systemd 服务..."
    
    # Webhook 监听服务
    cat > $SYSTEMD_DIR/${WEBHOOK_SERVICE_NAME}.service << EOF
[Unit]
Description=Clash Config Webhook Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/app
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python src/webhook_server.py
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/webhook.log
StandardError=append:$INSTALL_DIR/logs/webhook.log

[Install]
WantedBy=multi-user.target
EOF

    # 定时更新服务
    cat > $SYSTEMD_DIR/${UPDATER_SERVICE_NAME}.service << EOF
[Unit]
Description=Clash Config Updater Service
After=network.target

[Service]
Type=oneshot
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/app
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python src/update_service.py
StandardOutput=append:$INSTALL_DIR/logs/updater.log
StandardError=append:$INSTALL_DIR/logs/updater.log
EOF

    # 定时器
    cat > $SYSTEMD_DIR/${TIMER_NAME} << EOF
[Unit]
Description=Run Clash Config Updater every hour
Requires=${UPDATER_SERVICE_NAME}.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    log_info "systemd 服务创建完成"
}

# 启动服务
start_services() {
    log_step "启动服务..."
    
    # 启用并启动服务
    systemctl enable ${TIMER_NAME}
    systemctl enable ${WEBHOOK_SERVICE_NAME}.service
    
    systemctl start ${TIMER_NAME}
    systemctl start ${WEBHOOK_SERVICE_NAME}.service
    
    # 首次生成配置
    cd $INSTALL_DIR/app
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python generate_clash_config.py
    
    log_info "服务启动完成"
}

# 生成 Nginx 配置示例
generate_nginx_config() {
    log_step "生成 Nginx 配置示例..."
    
    cat > $INSTALL_DIR/nginx-config-example.conf << EOF
# Clash 配置服务器 Nginx 配置示例
# 请将以下配置添加到你现有的 Nginx server 块中

# 配置文件访问
location /clash_profile.yaml {
    alias $INSTALL_DIR/app/clash_profile.yaml;
    add_header Content-Type "text/plain; charset=utf-8";
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # CORS 头（如果需要跨域访问）
    add_header Access-Control-Allow-Origin *;
}

# Webhook 接口
location /clash/webhook {
    proxy_pass http://$WEBHOOK_HOST:$WEBHOOK_PORT/webhook;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}

# 状态页面
location /clash/status {
    proxy_pass http://$WEBHOOK_HOST:$WEBHOOK_PORT/status;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}

# 手动更新接口
location /clash/manual-update {
    proxy_pass http://$WEBHOOK_HOST:$WEBHOOK_PORT/manual-update;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}

# 管理界面（可选）
location /clash/ {
    proxy_pass http://$WEBHOOK_HOST:$WEBHOOK_PORT/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
EOF

    chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/nginx-config-example.conf
    
    log_info "Nginx 配置示例已保存到: $INSTALL_DIR/nginx-config-example.conf"
}

# 显示部署信息
show_info() {
    log_step "部署完成！"
    
    echo -e "${GREEN}==================== 部署信息 ====================${NC}"
    echo -e "安装目录: $INSTALL_DIR"
    echo -e "配置文件: $INSTALL_DIR/app/config.ini"
    echo -e "规则文件: $INSTALL_DIR/app/rules.yaml"
    echo -e "日志目录: $INSTALL_DIR/logs/"
    echo -e ""
    echo -e "${BLUE}下一步操作:${NC}"
    echo -e "1. 编辑配置文件，设置你的代理提供商:"
    echo -e "   nano $INSTALL_DIR/app/config.ini"
    echo -e ""
    echo -e "2. 将以下 Nginx 配置添加到你现有的网站配置中:"
    echo -e "   cat $INSTALL_DIR/nginx-config-example.conf"
    echo -e ""
    echo -e "3. 重新加载 Nginx:"
    echo -e "   nginx -t && systemctl reload nginx"
    echo -e ""
    echo -e "${BLUE}访问地址（根据你的域名调整）:${NC}"
    echo -e "配置文件: http://your-domain.com/clash_profile.yaml"
    echo -e "Webhook:  http://your-domain.com/clash/webhook"
    echo -e "状态页面: http://your-domain.com/clash/status"
    echo -e ""
    echo -e "${BLUE}服务管理:${NC}"
    echo -e "查看状态: systemctl status ${WEBHOOK_SERVICE_NAME}"
    echo -e "查看日志: journalctl -u ${WEBHOOK_SERVICE_NAME} -f"
    echo -e "重启服务: systemctl restart ${WEBHOOK_SERVICE_NAME}"
    echo -e "手动更新: systemctl start ${UPDATER_SERVICE_NAME}"
    echo -e ""
    echo -e "${YELLOW}注意事项:${NC}"
    echo -e "1. 请确保端口 $WEBHOOK_PORT 未被占用"
    echo -e "2. Webhook 服务监听在 $WEBHOOK_HOST:$WEBHOOK_PORT，通过 Nginx 反向代理访问"
    echo -e "3. 配置 GitHub Webhook 地址: http://your-domain.com/clash/webhook"
    echo -e "4. 记得在 config.ini 中设置 webhook_secret"
    echo -e "=================================================="
}

# 主函数
main() {
    log_info "开始部署 Clash 配置服务器（独立部署模式）..."
    
    check_root
    check_system
    load_server_config  # 加载配置文件
    install_dependencies
    create_user
    create_directories
    deploy_app
    create_systemd_service
    start_services
    generate_nginx_config
    show_info
    
    log_info "部署完成！"
}

# 运行主函数
main "$@"
