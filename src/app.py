#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash Config Manager Web 应用
提供配置状态查询和手动更新接口
"""

import os
import sys
import subprocess
import logging
import configparser
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from pathlib import Path

# 获取项目根目录（app.py 在 src/ 下，需要向上一级）
PROJECT_ROOT = Path(__file__).parent.parent

# 确保日志目录存在
(PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# 配置 Flask 应用
# 设置模板和静态文件目录
template_dir = Path(__file__).parent / "frontend" / "html"
static_dir = Path(__file__).parent / "frontend"

app = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir),
    static_url_path="/static",
)


class ConfigManager:
    def __init__(self, config_file="config/config.ini"):
        self.config_file = PROJECT_ROOT / config_file
        self.config = configparser.ConfigParser()
        self.load_config()
        self.last_update = None

    def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            self.config.read(self.config_file, encoding="utf-8")
            logger.info(f"已加载配置文件: {self.config_file}")
        else:
            logger.warning(f"配置文件 {self.config_file} 不存在")

    def regenerate_config(self):
        """重新生成配置文件"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "src" / "generate_clash_config.py"),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
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


config_manager = ConfigManager()


@app.route("/status")
def status():
    """状态查询接口（JSON格式）"""
    status_info = {
        "server": "Clash Config Manager",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "last_update": (
            config_manager.last_update.isoformat()
            if config_manager.last_update
            else None
        ),
        "config_file": str(config_manager.config_file),
    }

    # 检查配置文件是否存在
    config_file_path = PROJECT_ROOT / "output" / "clash_profile.yaml"
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
    """手动触发配置更新"""
    try:
        logger.info("收到手动更新请求")

        if config_manager.regenerate_config():
            config_manager.last_update = datetime.now()
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


@app.route("/clash_profile.yaml")
def get_clash_config():
    """获取生成的Clash配置文件"""
    config_path = PROJECT_ROOT / "output" / "clash_profile.yaml"
    if config_path.exists():
        from flask import send_file

        return send_file(
            str(config_path),
            mimetype="text/yaml",
            as_attachment=False,
            download_name="clash_profile.yaml",
        )
    else:
        return jsonify({"error": "配置文件不存在"}), 404


@app.route("/")
def index():
    """主页 - Web 管理界面"""
    return render_template(
        "index.html",
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        last_update=(
            config_manager.last_update.strftime("%Y-%m-%d %H:%M:%S")
            if config_manager.last_update
            else "从未更新"
        ),
        config_exists=(
            "✅ 存在"
            if (PROJECT_ROOT / "output" / "clash_profile.yaml").exists()
            else "❌ 不存在"
        ),
    )


def main():
    """主函数"""
    # 端口配置优先级：环境变量 > 默认值
    port = int(os.environ.get("APP_PORT", 8080))
    host = "0.0.0.0"  # Docker容器内需要监听所有接口

    port_source = "环境变量" if "APP_PORT" in os.environ else "默认值"
    logger.info(f"启动 Web 服务器: {host}:{port} (端口来源: {port_source})")
    logger.info(f"模板目录: {template_dir}")
    logger.info(f"静态文件目录: {static_dir}")

    # 启动服务器
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
