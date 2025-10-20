#!/usr/bin/env python3
"""
清理 Python 緩存腳本
用於解決部署環境中的模組導入緩存問題
"""

import os
import shutil
import sys

def clear_python_cache():
    """清理所有 Python 緩存"""
    cache_dirs = []
    pyc_files = []

    # 遍歷目錄找到所有緩存
    for root, dirs, files in os.walk('.'):
        # 跳過虛擬環境
        if '.venv' in root or 'venv' in root:
            continue

        # 收集 __pycache__ 目錄
        if '__pycache__' in dirs:
            cache_dirs.append(os.path.join(root, '__pycache__'))

        # 收集 .pyc 文件
        for file in files:
            if file.endswith('.pyc'):
                pyc_files.append(os.path.join(root, file))

    # 刪除緩存目錄
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"✅ 已刪除緩存目錄: {cache_dir}")
        except Exception as e:
            print(f"❌ 無法刪除 {cache_dir}: {e}")

    # 刪除 .pyc 文件
    for pyc_file in pyc_files:
        try:
            os.remove(pyc_file)
            print(f"✅ 已刪除緩存文件: {pyc_file}")
        except Exception as e:
            print(f"❌ 無法刪除 {pyc_file}: {e}")

    print(f"\n🎉 緩存清理完成！")
    print(f"📊 刪除了 {len(cache_dirs)} 個緩存目錄")
    print(f"📊 刪除了 {len(pyc_files)} 個 .pyc 文件")

if __name__ == "__main__":
    print("🧹 開始清理 Python 緩存...")
    clear_python_cache()