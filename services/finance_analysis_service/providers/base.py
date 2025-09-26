from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class FinanceAnalysisProvider(ABC):
    """財務分析提供商抽象基類"""

    @abstractmethod
    def get_llm(self, temperature: float = 0.01, max_tokens: Optional[int] = None):
        """
        獲取 LLM 實例

        Args:
            temperature: 溫度參數
            max_tokens: 最大 token 數

        Returns:
            LangChain 兼容的 LLM 實例
        """
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """
        獲取提供商資訊

        Returns:
            提供商資訊字典
        """
        pass

    def validate_config(self) -> bool:
        """
        驗證配置是否正確

        Returns:
            配置是否有效
        """
        return True