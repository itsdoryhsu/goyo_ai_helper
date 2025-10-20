#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goyo AI Helper - 主應用入口
LINE Bot 財務稅法顧問系統
遵循 Linus 設計哲學：簡單、可靠、無特殊情況
"""

import os
import sys
import shutil
import glob

# 強制清除Python快取 - 解決部署環境快取問題
def clear_deployment_cache():
    """清除部署環境的Python快取，確保模組正確載入"""
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 清除 __pycache__ 目錄
    for pycache_dir in glob.glob(os.path.join(current_dir, "**", "__pycache__"), recursive=True):
        try:
            shutil.rmtree(pycache_dir)
            print(f"清除快取目錄: {pycache_dir}")
        except Exception as e:
            print(f"清除快取失敗 {pycache_dir}: {e}")

    # 清除 .pyc 檔案
    for pyc_file in glob.glob(os.path.join(current_dir, "**", "*.pyc"), recursive=True):
        try:
            os.remove(pyc_file)
            print(f"清除快取檔案: {pyc_file}")
        except Exception as e:
            print(f"清除快取檔案失敗 {pyc_file}: {e}")

# 部署環境強制清除快取
if os.environ.get("RENDER"):
    print("🧹 偵測到Render部署環境，強制清除Python快取...")
    clear_deployment_cache()

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
    # 支援多種部署平台的端口配置 (Render 會自動設定 PORT)
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 啟動 Goyo AI Helper 於端口 {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)