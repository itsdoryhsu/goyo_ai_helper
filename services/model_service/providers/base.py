"""
基礎模型提供商抽象類
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator


class ModelProvider(ABC):
    """模型提供商抽象基類"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步聊天完成

        Args:
            messages: 對話消息列表
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數

        Returns:
            模型回應結果
        """
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天完成

        Args:
            messages: 對話消息列表
            model: 模型名稱
            **kwargs: 其他參數

        Yields:
            流式回應片段
        """
        pass

    @abstractmethod
    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        images: List[str],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        視覺理解完成

        Args:
            messages: 對話消息列表
            images: 圖片列表 (base64 encoded)
            model: 模型名稱
            **kwargs: 其他參數

        Returns:
            模型回應結果
        """
        pass

    async def health_check(self) -> bool:
        """
        健康檢查

        Returns:
            是否健康
        """
        try:
            test_messages = [{"role": "user", "content": "test"}]
            await self.chat_completion(
                messages=test_messages,
                model="test",
                max_tokens=10
            )
            return True
        except Exception:
            return False