#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Render.com 專用啟動腳本
整合所有服務到單一進程，遵循 Linus 簡化原則
"""

import os
import sys
import asyncio
import threading
import uvicorn
from concurrent.futures import ThreadPoolExecutor

# 添加當前目錄到Python路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

# 導入服務
from clients.line_bot.line_bot_v5_clean import app as linebot_app

def start_oauth_service():
    """啟動 OAuth 服務在不同端口"""
    try:
        from services.google_auth_service.oauth_server import app as oauth_app
        oauth_port = int(os.environ.get("OAUTH_PORT", 8080))
        uvicorn.run(oauth_app, host="0.0.0.0", port=oauth_port)
    except Exception as e:
        print(f"OAuth 服務啟動失敗: {e}")

def start_main_service():
    """啟動主要的 LINE Bot 服務"""
    main_port = int(os.environ.get("PORT", 10000))
    print(f"🚀 啟動 Goyo LINE Bot 於端口 {main_port}")
    print(f"🔐 OAuth 服務將在端口 8080 啟動")

    # 在背景啟動 OAuth 服務
    oauth_thread = threading.Thread(target=start_oauth_service, daemon=True)
    oauth_thread.start()

    # 啟動主服務
    uvicorn.run(linebot_app, host="0.0.0.0", port=main_port)

if __name__ == "__main__":
    print("="*60)
    print("🤖 Goyo AI Helper - Render.com 部署版本")
    print("📋 Linus 式設計：所有服務整合在單一進程中")
    print("="*60)

    start_main_service()