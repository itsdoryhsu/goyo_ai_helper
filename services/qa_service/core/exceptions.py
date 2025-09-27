"""QA Service 自定義異常"""

class QAServiceError(Exception):
    """QA服務基礎異常"""
    pass

class VectorStoreError(QAServiceError):
    """向量存儲相關異常"""
    pass

class LLMError(QAServiceError):
    """LLM相關異常"""
    pass

class SessionError(QAServiceError):
    """會話管理相關異常"""
    pass

class ConfigError(QAServiceError):
    """配置相關異常"""
    pass