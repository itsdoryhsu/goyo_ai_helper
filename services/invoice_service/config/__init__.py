# Invoice Service Configuration Module
# 直接導入settings模組內容，避免循環導入問題
import os
import sys

# 確保能找到settings模組
current_dir = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(current_dir, 'settings.py')

if os.path.exists(settings_path):
    # 相對導入 (正常情況)
    try:
        from .settings import *
    except ImportError:
        # 如果相對導入失敗，嘗試直接執行settings檔案
        import importlib.util
        spec = importlib.util.spec_from_file_location("settings", settings_path)
        settings_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings_module)

        # 將settings模組的所有變數導入當前命名空間
        for attr_name in dir(settings_module):
            if not attr_name.startswith('_'):
                globals()[attr_name] = getattr(settings_module, attr_name)
else:
    raise ImportError(f"Cannot find settings.py at {settings_path}")