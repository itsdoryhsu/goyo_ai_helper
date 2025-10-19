#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goyo AI Helper - 主應用入口
LINE Bot 財務稅法顧問系統
遵循 Linus 設計哲學：簡單、可靠、無特殊情況
"""

import os
import sys

# 添加當前目錄到Python路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

# 導入LINE Bot應用
from clients.line_bot.line_bot_v5_clean import app

# 本地開發和雲端部署使用
if __name__ == "__main__":
    import uvicorn
    # 支援多種部署平台的端口配置
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 啟動 Goyo AI Helper 於端口 {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)