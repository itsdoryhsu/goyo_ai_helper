"""
模型服務異常定義
"""


class ModelError(Exception):
    """模型服務基礎錯誤"""
    pass


class QuotaExceededError(ModelError):
    """模型配額超限錯誤"""
    pass


class ProviderError(ModelError):
    """提供商錯誤"""
    pass


class ConfigurationError(ModelError):
    """配置錯誤"""
    pass