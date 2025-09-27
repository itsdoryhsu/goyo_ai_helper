"""
模型服務核心數據模型
簡潔明確的數據結構，避免過度複雜化
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ServiceType(Enum):
    """服務類型枚舉 - 向後兼容"""
    QA = "qa"
    FINANCE = "finance"
    OCR = "ocr"
    CALENDAR = "calendar"
    INVOICE = "invoice"


@dataclass
class ModelRequest:
    """模型請求數據模型"""
    messages: List[Dict[str, str]]
    service_type: str
    images: Optional[List[str]] = None
    stream: bool = False

    # 可選的參數覆蓋
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None


@dataclass
class ModelResponse:
    """模型回應數據模型"""
    content: str
    provider: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    duration: float = 0.0

    # 錯誤信息 (如果有)
    error: Optional[str] = None
    fallback_used: bool = False


@dataclass
class ProviderStatus:
    """提供商狀態"""
    name: str
    available: bool
    last_error: Optional[str] = None
    response_time: Optional[float] = None


class ModelError(Exception):
    """模型服務基礎異常"""
    pass


class QuotaExceededError(ModelError):
    """配額超限異常"""
    pass


class ProviderUnavailableError(ModelError):
    """提供商不可用異常"""
    pass


class ConfigurationError(ModelError):
    """配置錯誤異常"""
    pass