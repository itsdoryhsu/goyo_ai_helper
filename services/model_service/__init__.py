"""
模型服務模組
提供統一的 AI 模型調用接口，支援多種提供商
"""

from .manager import model_manager, qa_completion, finance_completion, ocr_completion
from .config.models import ServiceType

__all__ = [
    'model_manager',
    'qa_completion',
    'finance_completion',
    'ocr_completion',
    'ServiceType'
]