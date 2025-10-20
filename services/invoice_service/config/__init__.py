# Invoice Service Configuration Module
# 使用多種方式嘗試導入settings，確保在不同環境下都能工作

# 方法1: 標準相對導入
try:
    from .settings import *
except ImportError:
    # 方法2: 嘗試不同的路徑查找方式
    import os
    import sys
    import importlib.util

    # 多種路徑嘗試
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'settings.py'),  # 標準路徑
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.py'),  # 絕對路徑
        os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.py'),  # 實際路徑
    ]

    # 如果在sys.path中找到相關目錄，也加入嘗試
    for path in sys.path:
        if 'invoice_service' in path:
            possible_paths.append(os.path.join(path, 'config', 'settings.py'))

    settings_loaded = False
    for settings_path in possible_paths:
        if os.path.exists(settings_path):
            try:
                spec = importlib.util.spec_from_file_location("settings", settings_path)
                settings_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(settings_module)

                # 將settings模組的所有變數導入當前命名空間
                for attr_name in dir(settings_module):
                    if not attr_name.startswith('_'):
                        globals()[attr_name] = getattr(settings_module, attr_name)

                settings_loaded = True
                break
            except Exception:
                continue

    if not settings_loaded:
        # 方法3: 嘗試絕對導入作為最後手段
        try:
            from services.invoice_service.config.settings import *
        except ImportError:
            raise ImportError(f"Cannot load settings.py from any of: {possible_paths}")