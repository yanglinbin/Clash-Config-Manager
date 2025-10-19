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
from typing import Dict, List, Any, Optional

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
        # 创建 ConfigParser 并保留键名的大小写
        self.config = configparser.RawConfigParser()
        self.config.optionxform = str  # 保留键名原始大小写
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

            # 创建合并的代理组配置（使用所有提供者，通过 filter 筛选节点）
            group_config = {
                "name": group_name,
                "type": group_type,
                "filter": filter_regex,
                "url": test_url,
                "use": list(providers.keys()),  # 使用所有代理提供者
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

        logger.info(f"生成了 {len(merged_groups)} 个合并地区组")
        return merged_groups

    def generate_custom_groups(
        self, providers: Dict[str, str], regions: Dict[str, Dict[str, any]]
    ) -> List[Dict[str, Any]]:
        """生成自定义节点组"""
        custom_groups = []

        if not self.config.has_section("custom_groups"):
            return custom_groups

        test_url = self.config.get(
            "clash",
            "test_url",
            fallback="http://connectivitycheck.gstatic.com/generate_204",
        )

        # 获取排除关键词
        exclude_keywords = self.get_exclude_keywords()

        # 遍历所有自定义组配置
        for group_name, config_str in self.config["custom_groups"].items():
            try:
                # 解析配置: emoji, 类型, 提供者列表, 地区列表, 目标代理组列表
                parts = [p.strip() for p in config_str.split(",")]
                if len(parts) < 4:
                    logger.warning(f"自定义组 {group_name} 配置不完整，跳过")
                    continue

                emoji = parts[0]
                group_type = parts[1]
                providers_str = parts[2]
                regions_str = parts[3]
                target_groups_str = parts[4] if len(parts) > 4 else ""

                # 解析提供者列表
                has_specific_providers = bool(providers_str)
                if providers_str:
                    selected_providers = [p.strip() for p in providers_str.split("|")]
                    # 过滤掉不存在的提供者
                    selected_providers = [
                        p for p in selected_providers if p in providers
                    ]
                    if not selected_providers:
                        logger.warning(f"自定义组 {group_name} 没有有效的提供者，跳过")
                        continue
                else:
                    selected_providers = []

                # 解析目标代理组列表
                if target_groups_str:
                    target_groups = [g.strip() for g in target_groups_str.split("|")]
                else:
                    target_groups = []  # 空表示添加到所有主代理组

                # 解析地区列表并生成过滤正则
                if regions_str:
                    selected_regions = [r.strip() for r in regions_str.split("|")]
                    # 收集所有选中地区的关键词
                    all_keywords = []
                    for region_name in selected_regions:
                        if region_name in regions:
                            all_keywords.extend(regions[region_name]["keywords"])

                    if not all_keywords:
                        logger.warning(
                            f"自定义组 {group_name} 没有有效的地区关键词，跳过"
                        )
                        continue

                    # 生成过滤正则
                    filter_regex = "|".join(all_keywords)
                    if exclude_keywords:
                        exclude_pattern = "|".join(exclude_keywords)
                        filter_regex = f"(?!.*({exclude_pattern})).*({filter_regex})"
                else:
                    logger.warning(f"自定义组 {group_name} 没有指定地区，跳过")
                    continue

                # 创建自定义组配置
                full_group_name = f"{emoji}{group_name}"
                group_config = {
                    "name": full_group_name,
                    "type": group_type,
                    "filter": filter_regex,
                    "url": test_url,
                }

                # 添加 use 参数：如果指定了提供者则使用指定的，否则使用所有提供者
                if has_specific_providers:
                    group_config["use"] = selected_providers
                else:
                    group_config["use"] = list(providers.keys())

                # 保存目标代理组信息（用于后续添加到主代理组）
                group_config["_target_groups"] = target_groups

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

                custom_groups.append(group_config)
                provider_info = (
                    f"提供者: {','.join(selected_providers)}"
                    if has_specific_providers
                    else "提供者: 所有"
                )
                target_info = (
                    f"目标组: {','.join(target_groups)}"
                    if target_groups
                    else "目标组: 所有"
                )
                logger.info(
                    f"创建自定义节点组: {full_group_name} "
                    f"(类型: {group_type}, {provider_info}, "
                    f"地区: {regions_str}, {target_info})"
                )

            except Exception as e:
                logger.error(f"解析自定义组 {group_name} 配置失败: {e}")
                continue

        if custom_groups:
            logger.info(f"生成了 {len(custom_groups)} 个自定义节点组")

        return custom_groups

    def generate_manual_select_group(
        self, providers: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """生成手动选择组"""
        if not self.config.has_section("manual_select"):
            return None

        enabled = self.config.getboolean("manual_select", "enabled", fallback=False)
        if not enabled:
            return None

        name = self.config.get("manual_select", "name", fallback="手动选择")
        emoji = self.config.get("manual_select", "emoji", fallback="✋")

        full_group_name = f"{emoji}{name}"

        # 手动选择组使用所有代理提供者，不使用 filter，包含所有节点
        group_config = {
            "name": full_group_name,
            "type": "select",
            "use": list(providers.keys()),  # 使用所有代理提供者
        }

        logger.info(f"创建手动选择组: {full_group_name}")
        return group_config

    def generate_main_proxy_groups(
        self,
        providers: Dict[str, str],
        regions: Dict[str, Dict[str, any]],
        custom_groups: List[Dict[str, Any]] = None,
        manual_select_group: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """生成主要代理组"""
        if custom_groups is None:
            custom_groups = []

        # 检查是否使用合并的地区组
        use_merged_groups = self.config.getboolean(
            "clash", "use_merged_region_groups", fallback=False
        )

        # 收集所有地区组名称
        region_group_names = []
        if use_merged_groups:
            for region_name, region_config in regions.items():
                emoji = region_config["emoji"]
                region_group_names.append(f"{emoji}{region_name}")
        else:
            # 使用原有的按提供者分组方式
            generate_all_groups = self.config.getboolean(
                "clash", "generate_all_region_groups", fallback=False
            )

            for provider_name in providers.keys():
                if not generate_all_groups and self.config.has_section(
                    "provider_regions"
                ):
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
                        region_group_names.append(
                            f"{emoji}{region_name}自动_{provider_name}"
                        )

        # 获取代理组默认配置
        proxy_defaults = {}
        if self.config.has_section("proxy_group_defaults"):
            for group_name, default_node in self.config["proxy_group_defaults"].items():
                if default_node:
                    proxy_defaults[group_name] = default_node
                    logger.info(f"读取默认节点配置: {group_name} -> {default_node}")

        # 从配置文件获取代理组配置
        proxy_groups_config = self.rules_config.get("proxy_groups", {})
        main_groups = []

        # 处理主要代理组
        main_groups_config = proxy_groups_config.get("main_groups", [])
        for group_config in main_groups_config:
            group_name = group_config["name"]

            # 构建 proxies 列表：默认节点（如果有） + DIRECT + 地区组 + 自定义组 + 手动选择组
            proxies = []
            default_node = proxy_defaults.get(group_name, None)

            # 添加默认节点（如果配置了）
            if default_node:
                proxies.append(default_node)

            # 添加 DIRECT
            proxies.append("DIRECT")

            # 添加地区组（排除已作为默认节点的）
            for region_name in region_group_names:
                if region_name != default_node:
                    proxies.append(region_name)

            # 添加自定义组（根据目标组过滤，排除已作为默认节点的）
            for custom_group in custom_groups:
                custom_group_name = custom_group["name"]
                target_groups = custom_group.get("_target_groups", [])

                # 如果目标组为空（表示添加到所有主代理组）或包含当前组
                if (
                    not target_groups or group_name in target_groups
                ) and custom_group_name != default_node:
                    proxies.append(custom_group_name)

            # 添加手动选择组（如果启用，排除已作为默认节点的）
            if manual_select_group and manual_select_group["name"] != default_node:
                proxies.append(manual_select_group["name"])

            group = {
                "name": group_name,
                "type": group_config["type"],
                "proxies": proxies,
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

        # 先生成自定义组和手动选择组
        custom_groups = self.generate_custom_groups(providers, regions)
        manual_select_group = self.generate_manual_select_group(providers)

        # 生成主代理组时传入自定义组和手动选择组，以便添加到选项列表
        main_groups = self.generate_main_proxy_groups(
            providers, regions, custom_groups, manual_select_group
        )

        # 生成所有代理组
        all_groups = main_groups

        # 添加地区组
        if use_merged_groups:
            all_groups += self.generate_merged_region_groups(providers, regions)
        else:
            all_groups += self.generate_auto_groups(providers, regions)

        # 添加自定义组
        for custom_group in custom_groups:
            # 移除内部使用的 _target_groups 字段
            group_copy = {
                k: v for k, v in custom_group.items() if not k.startswith("_")
            }
            all_groups.append(group_copy)

        # 添加手动选择组
        if manual_select_group:
            all_groups.append(manual_select_group)

        return all_groups

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
