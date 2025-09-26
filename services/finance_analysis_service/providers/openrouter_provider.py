import logging
from typing import Dict, Any, Optional

from .base import FinanceAnalysisProvider

logger = logging.getLogger(__name__)

# 檢查 OpenRouter 包裝器是否可用
try:
    from services.model_service.langchain_openrouter import create_openrouter_chat
    OPENROUTER_AVAILABLE = True
except ImportError:
    OPENROUTER_AVAILABLE = False
    create_openrouter_chat = None
    logger.warning("OpenRouter 包裝器不可用")


class OpenRouterFinanceProvider(FinanceAnalysisProvider):
    """OpenRouter 財務分析提供商"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

        if not OPENROUTER_AVAILABLE:
            raise ValueError("OpenRouter service is not available. Cannot use 'openrouter' provider.")

    def get_llm(self, temperature: float = 0.01, max_tokens: Optional[int] = None):
        """獲取 OpenRouter LLM 實例"""
        if not OPENROUTER_AVAILABLE:
            raise ValueError("OpenRouter service is not available")

        return create_openrouter_chat(
            model=self.model_name,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            api_key=self.api_key
        )

    def get_provider_info(self) -> Dict[str, Any]:
        """獲取提供商資訊"""
        return {
            "provider": "openrouter",
            "model": self.model_name,
            "api_key_set": bool(self.api_key),
            "available": OPENROUTER_AVAILABLE
        }

    def validate_config(self) -> bool:
        """驗證 OpenRouter 配置"""
        if not OPENROUTER_AVAILABLE:
            logger.error("OpenRouter service is not available")
            return False

        if not self.api_key:
            logger.error("OPENROUTER_API_KEY is not set")
            return False

        if not self.model_name:
            logger.error("OPENROUTER_MODEL is not set")
            return False

        return True