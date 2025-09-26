import logging
from typing import Dict, Any, Optional

from .base import FinanceAnalysisProvider

logger = logging.getLogger(__name__)

# 檢查 OpenAI 是否可用
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    ChatOpenAI = None
    logger.warning("langchain_openai 不可用")


class OpenAIFinanceProvider(FinanceAnalysisProvider):
    """OpenAI 財務分析提供商"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI service is not available. Cannot use 'openai' provider.")

    def get_llm(self, temperature: float = 0.01, max_tokens: Optional[int] = None):
        """獲取 OpenAI LLM 實例"""
        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI service is not available")

        return ChatOpenAI(
            model=self.model_name,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            api_key=self.api_key
        )

    def get_provider_info(self) -> Dict[str, Any]:
        """獲取提供商資訊"""
        return {
            "provider": "openai",
            "model": self.model_name,
            "api_key_set": bool(self.api_key),
            "available": OPENAI_AVAILABLE
        }

    def validate_config(self) -> bool:
        """驗證 OpenAI 配置"""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI service is not available")
            return False

        if not self.api_key:
            logger.error("OPENAI_API_KEY is not set")
            return False

        if not self.model_name:
            logger.error("OPENAI_MODEL is not set")
            return False

        return True