#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vercel Entry Point - 直接使用FastAPI應用
"""

import os
import sys

# 添加當前目錄到Python路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

# 導入LINE Bot應用
from clients.line_bot.line_bot_v5_clean import app

# Vercel會自動檢測這個app變數
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)