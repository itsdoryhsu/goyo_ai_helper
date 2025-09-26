class FinanceServiceError(Exception):
    """財務服務基礎異常"""
    pass

class DataLoadError(FinanceServiceError):
    """數據加載失敗 - 通常是spreadsheet讀取問題"""
    pass

class CalculationError(FinanceServiceError):
    """財務計算錯誤 - 通常是數據格式或邏輯問題"""
    pass

class AIError(FinanceServiceError):
    """AI分析失敗 - 通常是LLM調用問題"""
    pass

class ConfigError(FinanceServiceError):
    """配置錯誤 - 缺少必要的環境變數或設置"""
    pass