from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..core.models import QADocument, QAResponse

class LLMProvider(ABC):
    """LLM提供商基礎抽象類"""

    @abstractmethod
    async def generate_answer(self, question: str, context: str) -> Dict[str, Any]:
        """生成答案"""
        pass

    async def generate_answer_with_history(self, question: str, context: str, chat_history: list) -> Dict[str, Any]:
        """生成答案 - 包含會話記憶 (默認實現，可被覆蓋)"""
        # 默認行為：忽略歷史記錄，直接調用標準方法
        return await self.generate_answer(question, context)

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """獲取模型信息"""
        pass

class VectorStoreProvider(ABC):
    """向量存儲提供商基礎抽象類"""

    @abstractmethod
    async def search_documents(self, query: str, k: int = 5) -> List[QADocument]:
        """搜索相關文檔"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """檢查向量存儲是否可用"""
        pass