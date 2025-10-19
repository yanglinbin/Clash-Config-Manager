#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash 配置生成器 - 服务器版本
支持动态生成代理组和自动更新
"""

import os
import sys
import yaml
import configparser
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/clash_generator.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ClashConfigGenerator:
    def __init__(self, config_file="config/config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.rules_config = {}
        self.load_config()

        # 从配置文件获取规则文件路径
        self.rules_file = self.config.get(
            "files", "rules_config", fallback="config/rules.yaml"
        )
        self.load_rules_config()

    def load_config(self):
        """加载配置文件"""
        if not Path(self.config_file).exists():
            logger.error(f"配置文件 {self.config_file} 不存在")
            sys.exit(1)

        self.config.read(self.config_file, encoding="utf-8")
        logger.info(f"已加载配置文件: {self.config_file}")

    def load_rules_config(self):
        """加载规则配置文件"""
        if not Path(self.rules_file).exists():
            logger.error(f"规则配置文件 {self.rules_file} 不存在")
            sys.exit(1)

        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                self.rules_config = yaml.safe_load(f)
            logger.info(f"已加载规则配置文件: {self.rules_file}")
        except yaml.YAMLError as e:
            logger.error(f"规则配置文件格式错误: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"加载规则配置文件失败: {e}")
            sys.exit(1)

    def get_proxy_providers(self) -> Dict[str, str]:
        """获取代理提供者配置"""
        providers = {}
        if "proxy_providers" in self.config:
            for name, url in self.config["proxy_providers"].items():
                providers[name.upper()] = url
        return providers

    def get_regions(self) -> Dict[str, Dict[str, any]]:
        """获取地区配置"""
        regions = {}
        if "regions" in self.config:
            for region, config_str in self.config["regions"].items():
                parts = [k.strip() for k in config_str.split(",")]
                if len(parts) >= 2:
                    # 第一个是 emoji，其余是关键词
                    emoji = parts[0]
                    keywords = parts[1:]
                    regions[region] = {"emoji": emoji, "keywords": keywords}
        return regions

    def get_exclude_keywords(self) -> List[str]:
        """获取要排除的节点关键词"""
        exclude_keywords = []
        if "filter" in self.config:
            keywords_str = self.config.get("filter", "exclude_keywords", fallback="")
            if keywords_str:
                exclude_keywords = [k.strip() for k in keywords_str.split(",")]
        return exclude_keywords

    def generate_proxy_providers_config(
        self, providers: Dict[str, str]
    ) -> Dict[str, Any]:
        """生成 proxy-providers 配置"""
        proxy_providers = {}
        test_url = self.config.get(
            "clash",
            "test_url",
            fallback="http://connectivitycheck.gstatic.com/generate_204",
        )

        for name, url in providers.items():
            proxy_providers[name] = {
                "type": "http",
                "path": f"./profiles/proxies/{name.lower()}_proxies.yaml",
                "url": url,
                "interval": 3600,
                "health-check": {"enable": True, "url": test_url, "interval": 300},
            }

        return proxy_providers

    def generate_auto_groups(
        self, providers: Dict[str, str], regions: Dict[str, Dict[str, any]]
    ) -> List[Dict[str, Any]]:
        """生成自动选择组（跳过可能为空的组）"""
        auto_groups = []
        test_url = self.config.get(
            "clash",
            "test_url",
            fallback="http://connectivitycheck.gstatic.com/generate_204",
        )

        # 获取排除关键词
        exclude_keywords = self.get_exclude_keywords()

        # 是否为所有提供者生成所有地区组
        generate_all_groups = self.config.getboolean(
            "clash", "generate_all_region_groups", fallback=False
        )

        for provider_name in providers.keys():
            # 获取该提供者支持的地区列表
            if not generate_all_groups and self.config.has_section("provider_regions"):
                supported_regions_str = self.config.get(
                    "provider_regions", provider_name, fallback=""
                )
                if supported_regions_str:
                    supported_regions = [
                        r.strip() for r in supported_regions_str.split(",")
                    ]
                    logger.debug(
                        f"提供者 {provider_name} 支持的地区: {supported_regions}"
                    )
                else:
                    supported_regions = list(
                        regions.keys()
                    )  # 如果没有配置，使用所有地区
            else:
                supported_regions = list(regions.keys())  # 生成所有地区组

            for region_name, region_config in regions.items():
                # 检查是否应该为此提供者生成此地区的组
                if region_name not in supported_regions:
                    logger.debug(
                        f"跳过 {provider_name} 的 {region_name} 组（未在支持列表中）"
                    )
                    continue

                emoji = region_config["emoji"]
                keywords = region_config["keywords"]

                # 将所有关键词组合成正则表达式，支持多关键词匹配
                if keywords:
                    # 使用 | 连接所有关键词，创建正则表达式
                    # 例如: "Hong Kong|HK|港" 可以匹配包含任意一个关键词的节点名称
                    filter_regex = "|".join(keywords)

                    # 如果有排除关键词，使用负向前瞻断言排除包含这些关键词的节点
                    # 格式: (?!.*(关键词1|关键词2|...)).*地区关键词
                    if exclude_keywords:
                        exclude_pattern = "|".join(exclude_keywords)
                        # 负向前瞻：排除包含排除关键词的节点
                        filter_regex = f"(?!.*({exclude_pattern})).*({filter_regex})"

                    group_name = f"{emoji}{region_name}自动_{provider_name}"

                    # 创建代理组配置
                    group_config = {
                        "name": group_name,
                        "type": "url-test",
                        "use": [provider_name],
                        "filter": filter_regex,
                        "url": test_url,
                        "tolerance": 100,
                        "interval": 300,
                    }

                    # 注意：Clash 会自动处理空的代理组
                    # 如果 filter 没有匹配到任何节点，该组在 Clash 中会显示为空
                    # 但不会影响配置的正常运行

                    auto_groups.append(group_config)
                    logger.debug(
                        f"创建自动选择组: {group_name} (过滤器: {filter_regex})"
                    )

        logger.info(f"生成了 {len(auto_groups)} 个自动选择组")
        return auto_groups

    def generate_merged_region_groups(
        self, providers: Dict[str, str], regions: Dict[str, Dict[str, any]]
    ) -> List[Dict[str, Any]]:
        """生成合并的地区组（所有提供者合并到一个地区组）"""
        merged_groups = []
        test_url = self.config.get(
            "clash",
            "test_url",
            fallback="http://connectivitycheck.gstatic.com/generate_204",
        )

        # 获取排除关键词
        exclude_keywords = self.get_exclude_keywords()

        # 获取默认类型
        default_type = self.config.get(
            "merged_regions", "default_type", fallback="fallback"
        )

        # 获取需要额外创建 load-balance 组的地区
        load_balance_regions = {}
        if self.config.has_section("load_balance_regions"):
            for region, strategy in self.config["load_balance_regions"].items():
                load_balance_regions[region] = strategy

        for region_name, region_config in regions.items():
            emoji = region_config["emoji"]
            keywords = region_config["keywords"]

            # 检查该地区是否有自定义类型
            group_type = self.config.get(
                "merged_regions", region_name, fallback=default_type
            )

            # 生成过滤正则
            if keywords:
                filter_regex = "|".join(keywords)
                if exclude_keywords:
                    exclude_pattern = "|".join(exclude_keywords)
                    filter_regex = f"(?!.*({exclude_pattern})).*({filter_regex})"

            group_name = f"{emoji}{region_name}"

            # 创建合并的代理组配置
            group_config = {
                "name": group_name,
                "type": group_type,
                "use": list(providers.keys()),  # 使用所有提供者
                "filter": filter_regex,
                "url": test_url,
            }

            # 根据类型添加特定参数
            if group_type == "fallback":
                group_config["timeout"] = 5000
                group_config["interval"] = 600
            elif group_type == "url-test":
                group_config["tolerance"] = 500
                group_config["interval"] = 600
            elif group_type == "load-balance":
                group_config["strategy"] = "consistent-hashing"
                group_config["interval"] = 600

            merged_groups.append(group_config)
            logger.info(f"创建合并地区组: {group_name} (类型: {group_type})")

            # 如果该地区需要额外创建 load-balance 组
            if region_name in load_balance_regions:
                strategy = load_balance_regions[region_name]
                lb_group_name = f"{emoji}{region_name}_负载均衡"

                lb_group_config = {
                    "name": lb_group_name,
                    "type": "load-balance",
                    "use": list(providers.keys()),
                    "filter": filter_regex,
                    "url": test_url,
                    "strategy": strategy,
                    "interval": 600,
                }

                merged_groups.append(lb_group_config)
                logger.info(
                    f"创建负载均衡组: {lb_group_name} (策略: {strategy})"
                )

        logger.info(f"生成了 {len(merged_groups)} 个合并地区组")
        return merged_groups

    def generate_main_proxy_groups(
        self, providers: Dict[str, str], regions: Dict[str, Dict[str, any]]
    ) -> List[Dict[str, Any]]:
        """生成主要代理组"""
        provider_names = list(providers.keys())

        # 检查是否使用合并的地区组
        use_merged_groups = self.config.getboolean(
            "clash", "use_merged_region_groups", fallback=False
        )

        if use_merged_groups:
            # 使用合并的地区组
            auto_group_names = []
            
            # 获取需要额外创建 load-balance 组的地区
            load_balance_regions = set()
            if self.config.has_section("load_balance_regions"):
                load_balance_regions = set(self.config["load_balance_regions"].keys())
            
            for region_name, region_config in regions.items():
                emoji = region_config["emoji"]
                # 添加合并的地区组
                auto_group_names.append(f"{emoji}{region_name}")
                
                # 如果有 load-balance 组，也添加进去
                if region_name in load_balance_regions:
                    auto_group_names.append(f"{emoji}{region_name}_负载均衡")
        else:
            # 使用原有的按提供者分组方式
            auto_group_names = []
            generate_all_groups = self.config.getboolean(
                "clash", "generate_all_region_groups", fallback=False
            )

            for provider_name in provider_names:
                # 获取该提供者支持的地区列表
                if not generate_all_groups and self.config.has_section("provider_regions"):
                    supported_regions_str = self.config.get(
                        "provider_regions", provider_name, fallback=""
                    )
                    if supported_regions_str:
                        supported_regions = [
                            r.strip() for r in supported_regions_str.split(",")
                        ]
                    else:
                        supported_regions = list(regions.keys())
                else:
                    supported_regions = list(regions.keys())

                for region_name, region_config in regions.items():
                    if region_name in supported_regions:
                        emoji = region_config["emoji"]
                        auto_group_names.append(f"{emoji}{region_name}自动_{provider_name}")

        # 从配置文件获取代理组配置
        proxy_groups_config = self.rules_config.get("proxy_groups", {})
        main_groups = []

        # 处理主要代理组
        main_groups_config = proxy_groups_config.get("main_groups", [])
        for group_config in main_groups_config:
            group = {
                "name": group_config["name"],
                "type": group_config["type"],
                "use": provider_names,
                "proxies": ["DIRECT"] + auto_group_names,
            }
            main_groups.append(group)

        # 处理特殊代理组（不使用代理提供商）
        special_groups_config = proxy_groups_config.get("special_groups", [])
        for group_config in special_groups_config:
            group = {
                "name": group_config["name"],
                "type": group_config["type"],
                "proxies": group_config["proxies"],
            }
            main_groups.append(group)

        return main_groups

    def get_rule_providers(self) -> Dict[str, Any]:
        """获取规则集配置"""
        return self.rules_config.get("rule-providers", {})

    def get_custom_rules(self) -> List[str]:
        """获取自定义规则"""
        rules = []

        # 获取自定义规则配置
        custom_rules = self.rules_config.get("custom_rules", [])

        # 如果是列表，直接添加
        if isinstance(custom_rules, list):
            rules.extend(custom_rules)
        # 如果是字典（旧格式），按类别添加规则
        elif isinstance(custom_rules, dict):
            for category, rule_list in custom_rules.items():
                if isinstance(rule_list, list):
                    rules.extend(rule_list)

        # 添加规则集引用规则
        ruleset_rules = self.rules_config.get("ruleset_rules", [])
        rules.extend(ruleset_rules)

        return rules

    def _generate_all_proxy_groups(
        self, providers: Dict[str, str], regions: Dict[str, Dict[str, any]]
    ) -> List[Dict[str, Any]]:
        """根据配置生成所有代理组"""
        # 检查是否使用合并的地区组
        use_merged_groups = self.config.getboolean(
            "clash", "use_merged_region_groups", fallback=False
        )

        if use_merged_groups:
            # 使用合并的地区组
            return (
                self.generate_main_proxy_groups(providers, regions)
                + self.generate_merged_region_groups(providers, regions)
            )
        else:
            # 使用原有的按提供者分组方式
            return (
                self.generate_main_proxy_groups(providers, regions)
                + self.generate_auto_groups(providers, regions)
            )

    def generate_config(self) -> Dict[str, Any]:
        """生成完整的 Clash 配置"""
        providers = self.get_proxy_providers()
        regions = self.get_regions()

        if not providers:
            logger.error("没有配置代理提供者")
            return {}

        logger.info(f"找到 {len(providers)} 个代理提供者: {list(providers.keys())}")
        logger.info(f"找到 {len(regions)} 个地区配置: {list(regions.keys())}")

        # 生成配置
        config = {
            "port": self.config.getint("clash", "port", fallback=7890),
            "socks-port": self.config.getint("clash", "socks_port", fallback=7891),
            "allow-lan": self.config.getboolean("clash", "allow_lan", fallback=True),
            "mode": self.config.get("clash", "mode", fallback="Rule"),
            "log-level": self.config.get("clash", "log_level", fallback="info"),
            "external-controller": self.config.get(
                "clash", "external_controller", fallback=":9090"
            ),
            "proxy-providers": self.generate_proxy_providers_config(providers),
            "proxy-groups": self._generate_all_proxy_groups(providers, regions),
            "rule-providers": self.get_rule_providers(),
            "rules": self.get_custom_rules(),
        }

        return config

    def save_config(
        self, config: Dict[str, Any], output_file: str = "output/clash_profile.yaml"
    ):
        """保存配置到文件"""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            file_size = Path(output_file).stat().st_size
            logger.info(f"✅ 配置文件已生成: {output_file}")
            logger.info(f"📊 文件大小: {file_size} 字节")
            logger.info(f"📊 代理组数量: {len(config.get('proxy-groups', []))}")
            logger.info(f"📊 规则数量: {len(config.get('rules', []))}")

            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def run(self):
        """运行生成器"""
        logger.info("🚀 开始生成 Clash 配置")
        logger.info("=" * 50)

        config = self.generate_config()
        if not config:
            logger.error("❌ 配置生成失败")
            return False

        if self.save_config(config):
            logger.info("🎉 配置生成完成!")
            return True
        else:
            logger.error("❌ 配置保存失败")
            return False


def main():
    """主函数"""
    generator = ClashConfigGenerator()
    success = generator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
