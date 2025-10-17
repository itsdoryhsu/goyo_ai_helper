#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vercel Entry Point - FastAPI應用
Vercel會自動檢測名為'app'的FastAPI實例
"""

import os
import sys

# 添加當前目錄到Python路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

# 導入LINE Bot應用 - 必須命名為app
from clients.line_bot.line_bot_v5_clean import app

# 這裡直接導出app供Vercel使用
# Vercel會自動檢測這個全局變數
app = app

# 本地開發時使用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)