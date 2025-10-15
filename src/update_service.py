#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash 配置定时更新服务
定期检查并更新配置文件
"""

import os
import sys
import time
import logging
import configparser
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from generate_clash_config import ClashConfigGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/update_service.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class UpdateService:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
        self.last_update = None
        self.update_interval = self.config.getint(
            "server", "update_interval", fallback=3600
        )

    def load_config(self):
        """加载配置文件"""
        if Path(self.config_file).exists():
            self.config.read(self.config_file, encoding="utf-8")
            logger.info(f"已加载配置文件: {self.config_file}")
        else:
            logger.error(f"配置文件 {self.config_file} 不存在")
            sys.exit(1)

    def check_config_file_age(self) -> bool:
        """检查配置文件是否需要更新"""
        config_file = Path("output/clash_profile.yaml")

        if not config_file.exists():
            logger.info("配置文件不存在，需要生成")
            return True

        # 获取文件修改时间
        file_mtime = datetime.fromtimestamp(config_file.stat().st_mtime)
        current_time = datetime.now()

        # 检查是否超过更新间隔
        if current_time - file_mtime > timedelta(seconds=self.update_interval):
            logger.info(f"配置文件已过期 (超过 {self.update_interval} 秒)，需要更新")
            return True
        else:
            logger.info("配置文件仍在有效期内")
            return False

    def pull_latest_code(self) -> bool:
        """拉取最新代码"""
        try:
            if not Path(".git").exists():
                logger.info("当前目录不是 Git 仓库，跳过代码更新")
                return True

            logger.info("检查代码更新...")

            # 获取远程更新
            result = subprocess.run(
                ["git", "fetch", "origin"], capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Git fetch 失败: {result.stderr}")
                return False

            # 检查是否有更新
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..origin/main"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                commits_behind = int(result.stdout.strip())
                if commits_behind > 0:
                    logger.info(f"发现 {commits_behind} 个新提交，开始更新代码")

                    # 拉取更新
                    result = subprocess.run(
                        ["git", "pull", "origin", "main"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode == 0:
                        logger.info("代码更新成功")
                        return True
                    else:
                        logger.error(f"代码更新失败: {result.stderr}")
                        return False
                else:
                    logger.info("代码已是最新版本")
                    return True
            else:
                logger.warning("无法检查代码更新状态")
                return True

        except subprocess.TimeoutExpired:
            logger.error("Git 操作超时")
            return False
        except Exception as e:
            logger.error(f"检查代码更新异常: {e}")
            return False

    def update_config(self) -> bool:
        """更新配置文件"""
        try:
            logger.info("开始更新配置文件...")

            # 重新加载配置（可能有更新）
            self.load_config()

            # 生成新配置
            generator = ClashConfigGenerator(self.config_file)
            success = generator.run()

            if success:
                self.last_update = datetime.now()
                logger.info("配置文件更新成功")
                return True
            else:
                logger.error("配置文件更新失败")
                return False

        except Exception as e:
            logger.error(f"更新配置文件异常: {e}")
            return False

    def backup_config(self) -> bool:
        """备份当前配置文件"""
        try:
            config_file = Path("output/clash_profile.yaml")
            if config_file.exists():
                backup_dir = Path("backups")
                backup_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"clash_profile_{timestamp}.yaml"

                config_file.rename(backup_file)
                logger.info(f"配置文件已备份到: {backup_file}")

                # 清理旧备份（保留最近10个）
                self.cleanup_old_backups(backup_dir)
                return True
            else:
                logger.info("没有配置文件需要备份")
                return True

        except Exception as e:
            logger.error(f"备份配置文件异常: {e}")
            return False

    def cleanup_old_backups(self, backup_dir: Path, keep_count: int = 10):
        """清理旧备份文件"""
        try:
            backup_files = list(backup_dir.glob("clash_profile_*.yaml"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            if len(backup_files) > keep_count:
                for old_backup in backup_files[keep_count:]:
                    old_backup.unlink()
                    logger.info(f"已删除旧备份: {old_backup}")

        except Exception as e:
            logger.error(f"清理备份文件异常: {e}")

    def check_config_validity(self) -> bool:
        """检查配置文件有效性"""
        try:
            config_file = Path("output/clash_profile.yaml")
            if not config_file.exists():
                logger.error("配置文件不存在")
                return False

            # 检查文件大小
            file_size = config_file.stat().st_size
            if file_size < 1000:  # 小于1KB可能有问题
                logger.warning(f"配置文件过小: {file_size} 字节")
                return False

            # 简单检查YAML格式
            import yaml

            with open(config_file, "r", encoding="utf-8") as f:
                try:
                    yaml.safe_load(f)
                    logger.info("配置文件格式验证通过")
                    return True
                except yaml.YAMLError as e:
                    logger.error(f"配置文件格式错误: {e}")
                    return False

        except Exception as e:
            logger.error(f"检查配置文件有效性异常: {e}")
            return False

    def run_once(self) -> bool:
        """执行一次更新检查"""
        logger.info("=" * 50)
        logger.info("开始执行定时更新检查")

        try:
            # 检查是否需要更新
            need_update = self.check_config_file_age()

            if not need_update:
                logger.info("配置文件无需更新")
                return True

            # 拉取最新代码
            if not self.pull_latest_code():
                logger.error("代码更新失败，跳过配置更新")
                return False

            # 备份当前配置
            if not self.backup_config():
                logger.warning("配置备份失败，但继续更新")

            # 更新配置
            if self.update_config():
                # 验证新配置
                if self.check_config_validity():
                    logger.info("✅ 配置更新完成且验证通过")
                    return True
                else:
                    logger.error("❌ 新配置验证失败")
                    return False
            else:
                logger.error("❌ 配置更新失败")
                return False

        except Exception as e:
            logger.error(f"定时更新异常: {e}")
            return False
        finally:
            logger.info("定时更新检查结束")
            logger.info("=" * 50)

    def run_daemon(self):
        """以守护进程模式运行"""
        logger.info(f"启动定时更新服务，更新间隔: {self.update_interval} 秒")

        while True:
            try:
                self.run_once()
                logger.info(f"等待 {self.update_interval} 秒后进行下次检查...")
                time.sleep(self.update_interval)

            except KeyboardInterrupt:
                logger.info("收到中断信号，停止服务")
                break
            except Exception as e:
                logger.error(f"守护进程异常: {e}")
                logger.info("等待 60 秒后重试...")
                time.sleep(60)

    def get_status(self) -> dict:
        """获取服务状态"""
        config_file = Path("output/clash_profile.yaml")

        status = {
            "service": "Clash Config Update Service",
            "status": "running",
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_interval": self.update_interval,
            "config_file_exists": config_file.exists(),
            "config_file_size": (
                config_file.stat().st_size if config_file.exists() else 0
            ),
            "config_file_modified": (
                datetime.fromtimestamp(config_file.stat().st_mtime).isoformat()
                if config_file.exists()
                else None
            ),
            "next_check": (
                datetime.now() + timedelta(seconds=self.update_interval)
            ).isoformat(),
        }

        return status


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Clash 配置定时更新服务")
    parser.add_argument("--daemon", action="store_true", help="以守护进程模式运行")
    parser.add_argument("--once", action="store_true", help="只执行一次更新检查")
    parser.add_argument("--status", action="store_true", help="显示服务状态")
    parser.add_argument("--config", default="config.ini", help="配置文件路径")

    args = parser.parse_args()

    service = UpdateService(args.config)

    if args.status:
        # 显示状态
        status = service.get_status()
        print("服务状态:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    elif args.once:
        # 执行一次更新
        success = service.run_once()
        sys.exit(0 if success else 1)
    elif args.daemon:
        # 守护进程模式
        service.run_daemon()
    else:
        # 默认执行一次更新
        success = service.run_once()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
