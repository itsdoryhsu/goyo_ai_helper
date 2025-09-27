"""
乾淨的模型提供商基類
簡化接口，消除不必要的複雜性
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ..core.models import ModelResponse


class ModelProvider(ABC):
    """模型提供商抽象基類 - 乾淨版本"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        聊天完成 - 統一的回應格式

        Args:
            messages: 對話消息列表
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數

        Returns:
            ModelResponse 對象

        Raises:
            QuotaExceededError: 配額超限
            ProviderUnavailableError: 提供商不可用
        """
        pass

    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        images: List[str],
        model: str,
        **kwargs
    ) -> ModelResponse:
        """
        視覺理解完成 - 默認實現

        大多數提供商可以覆蓋此方法以提供專門的視覺支持
        """
        # 默認行為：將圖片添加到消息中
        enhanced_messages = self._add_images_to_messages(messages, images)
        return await self.chat_completion(enhanced_messages, model, **kwargs)

    def _add_images_to_messages(
        self,
        messages: List[Dict[str, str]],
        images: List[str]
    ) -> List[Dict[str, str]]:
        """
        將圖片添加到消息中 - 提供商特定的實現

        這是一個默認實現，每個提供商應該根據自己的格式覆蓋
        """
        if not images:
            return messages

        # 簡單實現：在最後一條用戶消息中添加圖片引用
        enhanced_messages = messages.copy()
        last_user_msg = None

        for i in range(len(enhanced_messages) - 1, -1, -1):
            if enhanced_messages[i]["role"] == "user":
                last_user_msg = i
                break

        if last_user_msg is not None:
            enhanced_messages[last_user_msg]["content"] += f" [附加了 {len(images)} 張圖片]"

        return enhanced_messages

    async def close(self):
        """清理資源 - 默認實現"""
        pass