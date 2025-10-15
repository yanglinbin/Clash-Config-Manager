#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Webhook 监听服务
监听 GitHub 仓库更新，自动触发配置文件重新生成
"""

import os
import sys
import json
import hmac
import hashlib
import subprocess
import logging
import configparser
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/webhook.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class WebhookServer:
    def __init__(self, config_file="config/config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
        self.webhook_secret = self.config.get("server", "webhook_secret", fallback="")
        self.repo_url = None
        self.last_update = None

    def load_config(self):
        """加载配置文件"""
        if Path(self.config_file).exists():
            self.config.read(self.config_file, encoding="utf-8")
            logger.info(f"已加载配置文件: {self.config_file}")
        else:
            logger.warning(f"配置文件 {self.config_file} 不存在")

    def verify_signature(self, payload_body, signature_header):
        """验证 GitHub Webhook 签名"""
        if not self.webhook_secret:
            logger.warning("未配置 webhook_secret，跳过签名验证")
            return True

        if not signature_header:
            logger.error("缺少签名头")
            return False

        try:
            hash_object = hmac.new(
                self.webhook_secret.encode("utf-8"),
                msg=payload_body,
                digestmod=hashlib.sha256,
            )
            expected_signature = "sha256=" + hash_object.hexdigest()

            if not hmac.compare_digest(expected_signature, signature_header):
                logger.error("签名验证失败")
                return False

            return True
        except Exception as e:
            logger.error(f"签名验证异常: {e}")
            return False

    def pull_latest_code(self):
        """拉取最新代码"""
        try:
            # 检查是否为 Git 仓库
            if not Path(".git").exists():
                logger.warning("当前目录不是 Git 仓库")
                return False

            # 拉取最新代码
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("代码更新成功")
                logger.info(f"Git 输出: {result.stdout}")
                return True
            else:
                logger.error(f"代码更新失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Git 拉取超时")
            return False
        except Exception as e:
            logger.error(f"拉取代码异常: {e}")
            return False

    def regenerate_config(self):
        """重新生成配置文件"""
        try:
            result = subprocess.run(
                [sys.executable, "src/generate_clash_config.py"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info("配置文件重新生成成功")
                logger.info(f"生成器输出: {result.stdout}")
                return True
            else:
                logger.error(f"配置文件生成失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("配置生成超时")
            return False
        except Exception as e:
            logger.error(f"生成配置异常: {e}")
            return False

    def handle_push_event(self, payload):
        """处理 push 事件"""
        try:
            repo_name = payload.get("repository", {}).get("full_name", "unknown")
            ref = payload.get("ref", "")
            commits = payload.get("commits", [])

            logger.info(f"收到 push 事件: {repo_name}, ref: {ref}")
            logger.info(f"提交数量: {len(commits)}")

            # 只处理主分支的推送
            if ref not in ["refs/heads/main", "refs/heads/master"]:
                logger.info(f"忽略非主分支推送: {ref}")
                return False

            # 检查是否有相关文件变更
            relevant_files = [
                "config.ini",
                "src/generate_clash_config.py",
                "src/webhook_server.py",
            ]
            has_relevant_changes = False

            for commit in commits:
                modified_files = commit.get("modified", []) + commit.get("added", [])
                for file in modified_files:
                    if any(relevant_file in file for relevant_file in relevant_files):
                        has_relevant_changes = True
                        logger.info(f"检测到相关文件变更: {file}")
                        break

            if not has_relevant_changes:
                logger.info("没有检测到相关文件变更，跳过更新")
                return False

            # 更新代码和配置
            if self.pull_latest_code():
                # 重新加载配置
                self.load_config()

                # 重新生成配置文件
                if self.regenerate_config():
                    self.last_update = datetime.now()
                    logger.info("Webhook 处理完成")
                    return True

            return False

        except Exception as e:
            logger.error(f"处理 push 事件异常: {e}")
            return False


webhook_server = WebhookServer()


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """处理 GitHub Webhook"""
    try:
        # 获取请求数据
        payload_body = request.get_data()
        signature_header = request.headers.get("X-Hub-Signature-256")
        event_type = request.headers.get("X-GitHub-Event")

        logger.info(f"收到 Webhook 请求: {event_type}")

        # 验证签名
        if not webhook_server.verify_signature(payload_body, signature_header):
            return jsonify({"error": "Invalid signature"}), 403

        # 解析 JSON 数据
        try:
            payload = json.loads(payload_body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return jsonify({"error": "Invalid JSON"}), 400

        # 处理不同类型的事件
        if event_type == "push":
            success = webhook_server.handle_push_event(payload)
            if success:
                return jsonify(
                    {
                        "status": "success",
                        "message": "Config updated successfully",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                return jsonify(
                    {
                        "status": "skipped",
                        "message": "No relevant changes detected",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        elif event_type == "ping":
            logger.info("收到 ping 事件")
            return jsonify(
                {
                    "status": "success",
                    "message": "Webhook server is running",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            logger.info(f"忽略事件类型: {event_type}")
            return jsonify(
                {
                    "status": "ignored",
                    "message": f"Event type {event_type} not handled",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.error(f"Webhook 处理异常: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/status")
def status():
    """状态页面"""
    status_info = {
        "server": "Clash Config Webhook Server",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "last_update": (
            webhook_server.last_update.isoformat()
            if webhook_server.last_update
            else None
        ),
        "config_file": webhook_server.config_file,
        "webhook_secret_configured": bool(webhook_server.webhook_secret),
    }

    # 检查配置文件是否存在
    config_file_path = Path("/opt/clash-config-server/app/output/clash_profile.yaml")
    config_exists = config_file_path.exists()
    if config_exists:
        config_stat = config_file_path.stat()
        status_info["config_file_exists"] = True
        status_info["config_file_size"] = config_stat.st_size
        status_info["config_file_modified"] = datetime.fromtimestamp(
            config_stat.st_mtime
        ).isoformat()
    else:
        status_info["config_file_exists"] = False

    return jsonify(status_info)


@app.route("/manual-update", methods=["POST"])
def manual_update():
    """手动触发更新"""
    try:
        logger.info("收到手动更新请求")

        if webhook_server.regenerate_config():
            webhook_server.last_update = datetime.now()
            return jsonify(
                {
                    "status": "success",
                    "message": "Config updated successfully",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Config update failed",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"手动更新异常: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/")
def index():
    """首页"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clash Config Webhook Server</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 20px; background: #f0f0f0; border-radius: 5px; margin: 20px 0; }
            .success { background: #d4edda; color: #155724; }
            .info { background: #d1ecf1; color: #0c5460; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Clash Config Webhook Server</h1>
            
            <div class="status info">
                <h3>服务状态</h3>
                <p>✅ 服务正在运行</p>
                <p>📅 当前时间: {{ current_time }}</p>
                {% if last_update %}
                <p>🔄 最后更新: {{ last_update }}</p>
                {% endif %}
            </div>
            
            <div class="status">
                <h3>配置信息</h3>
                <p>📁 配置文件: {{ config_exists }}</p>
                <p>🔐 Webhook 密钥: {{ webhook_configured }}</p>
            </div>
            
            <div class="status">
                <h3>API 接口</h3>
                <ul>
                    <li><strong>GET /status</strong> - 获取服务状态</li>
                    <li><strong>POST /webhook</strong> - GitHub Webhook 接口</li>
                    <li><strong>POST /manual-update</strong> - 手动触发更新</li>
                    <li><strong>GET /clash_profile.yaml</strong> - 获取配置文件</li>
                </ul>
            </div>
            
            <div class="status">
                <h3>手动操作</h3>
                <button onclick="manualUpdate()">🔄 手动更新配置</button>
                <button onclick="checkStatus()">📊 检查状态</button>
            </div>
            
            <div id="result" class="status" style="display:none;"></div>
        </div>
        
        <script>
            function manualUpdate() {
                fetch('/manual-update', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        const result = document.getElementById('result');
                        result.style.display = 'block';
                        result.className = 'status ' + (data.status === 'success' ? 'success' : 'error');
                        result.innerHTML = '<h3>更新结果</h3><p>' + data.message + '</p>';
                    })
                    .catch(error => {
                        const result = document.getElementById('result');
                        result.style.display = 'block';
                        result.className = 'status error';
                        result.innerHTML = '<h3>更新失败</h3><p>' + error + '</p>';
                    });
            }
            
            function checkStatus() {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        const result = document.getElementById('result');
                        result.style.display = 'block';
                        result.className = 'status info';
                        result.innerHTML = '<h3>状态信息</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    });
            }
        </script>
    </body>
    </html>
    """

    return render_template_string(
        html_template,
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        last_update=(
            webhook_server.last_update.strftime("%Y-%m-%d %H:%M:%S")
            if webhook_server.last_update
            else "从未更新"
        ),
        config_exists=(
            "✅ 存在"
            if Path("/opt/clash-config-server/app/output/clash_profile.yaml").exists()
            else "❌ 不存在"
        ),
        webhook_configured=(
            "✅ 已配置" if webhook_server.webhook_secret else "❌ 未配置"
        ),
    )


def main():
    """主函数"""
    # 从服务器配置文件读取设置
    server_config = configparser.ConfigParser()
    if Path("config/serverconfig.ini").exists():
        server_config.read("config/serverconfig.ini", encoding="utf-8")
        host = server_config.get("network", "webhook_host", fallback="127.0.0.1")
        port = server_config.getint("network", "webhook_port", fallback=5000)
    else:
        # 兼容旧配置
        logger.warning("config/serverconfig.ini 不存在，使用默认配置")
        host = "127.0.0.1"
        port = 5000

    logger.info(f"启动 Webhook 服务器: {host}:{port}")

    # 启动服务器
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
