#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型配置管理工具
提供彈性的模型設定功能
"""

import os
import sys
import argparse
import json

# 將專案根目錄添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.model_service.config.dynamic_config import dynamic_config
from services.model_service.config.models import ServiceType


def list_profiles():
    """列出所有可用的配置檔案"""
    profiles = dynamic_config.get_available_profiles()
    current = dynamic_config.get_current_profile()

    print("📋 可用的模型配置檔案：")
    print("=" * 50)

    for profile in profiles:
        marker = "✅ (當前)" if profile == current else "   "
        config = dynamic_config.get_profile_config(profile)
        print(f"{marker} {profile}")
        for service, model in config.items():
            print(f"      {service}: {model}")
        print()


def switch_profile(profile_name: str):
    """切換配置檔案"""
    if dynamic_config.switch_profile(profile_name):
        print(f"✅ 已切換到配置檔案: {profile_name}")

        config = dynamic_config.get_profile_config(profile_name)
        print("\n新的模型配置：")
        for service, model in config.items():
            print(f"  {service}: {model}")
    else:
        print(f"❌ 配置檔案 '{profile_name}' 不存在")
        print("\n可用的配置檔案：")
        for profile in dynamic_config.get_available_profiles():
            print(f"  - {profile}")


def set_model(service: str, model: str):
    """設定特定服務的模型"""
    try:
        service_type = ServiceType(service.lower())
        dynamic_config.set_model_for_service(service_type, model)
        print(f"✅ 已設定 {service} 服務模型為: {model}")
    except ValueError:
        print(f"❌ 無效的服務類型: {service}")
        print("可用的服務類型: qa, finance, ocr")


def create_profile(profile_name: str, qa_model: str, finance_model: str, ocr_model: str):
    """創建新的配置檔案"""
    config = {
        "qa": qa_model,
        "finance": finance_model,
        "ocr": ocr_model
    }

    dynamic_config.create_profile(profile_name, config)
    print(f"✅ 已創建新的配置檔案: {profile_name}")
    print("\n配置內容：")
    for service, model in config.items():
        print(f"  {service}: {model}")


def show_current_config():
    """顯示當前配置"""
    current_profile = dynamic_config.get_current_profile()
    config = dynamic_config.get_profile_config()

    print(f"📊 當前配置檔案: {current_profile}")
    print("=" * 50)

    for service_type in [ServiceType.QA, ServiceType.FINANCE, ServiceType.OCR]:
        model = dynamic_config.get_model_for_service(service_type)
        print(f"{service_type.value.upper()}: {model}")


def show_available_models():
    """顯示可用的模型列表"""
    models = {
        "免費模型": [
            "x-ai/grok-4-fast:free",
            "deepseek/deepseek-chat-v3.1:free",
            "deepseek/deepseek-r1-0528:free",
            "google/gemini-2.0-flash-exp:free"
        ],
        "OpenAI 模型": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/gpt-4-turbo"
        ],
        "DeepSeek 模型": [
            "deepseek/deepseek-chat-v3.1",
            "deepseek/deepseek-r1-0528"
        ],
        "Google 模型": [
            "google/gemini-2.0-flash-exp",
            "google/gemini-1.5-pro"
        ]
    }

    print("📚 可用的模型列表：")
    print("=" * 50)

    for category, model_list in models.items():
        print(f"\n{category}:")
        for model in model_list:
            print(f"  - {model}")


def main():
    parser = argparse.ArgumentParser(description="模型配置管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 列出配置檔案
    subparsers.add_parser("list", help="列出所有配置檔案")

    # 切換配置檔案
    switch_parser = subparsers.add_parser("switch", help="切換配置檔案")
    switch_parser.add_argument("profile", help="配置檔案名稱")

    # 設定模型
    set_parser = subparsers.add_parser("set", help="設定特定服務的模型")
    set_parser.add_argument("service", choices=["qa", "finance", "ocr"], help="服務類型")
    set_parser.add_argument("model", help="模型名稱")

    # 創建配置檔案
    create_parser = subparsers.add_parser("create", help="創建新的配置檔案")
    create_parser.add_argument("name", help="配置檔案名稱")
    create_parser.add_argument("qa_model", help="QA 服務模型")
    create_parser.add_argument("finance_model", help="財務分析服務模型")
    create_parser.add_argument("ocr_model", help="OCR 服務模型")

    # 顯示當前配置
    subparsers.add_parser("current", help="顯示當前配置")

    # 顯示可用模型
    subparsers.add_parser("models", help="顯示可用的模型列表")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        list_profiles()
    elif args.command == "switch":
        switch_profile(args.profile)
    elif args.command == "set":
        set_model(args.service, args.model)
    elif args.command == "create":
        create_profile(args.name, args.qa_model, args.finance_model, args.ocr_model)
    elif args.command == "current":
        show_current_config()
    elif args.command == "models":
        show_available_models()


if __name__ == "__main__":
    main()