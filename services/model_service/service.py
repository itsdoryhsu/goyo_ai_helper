"""
模型服務的統一接口
替代舊的全局管理器，提供乾淨的依賴注入接口
"""

import logging
from typing import List, Dict, Any, Optional

from .core.manager import ModelManager, create_default_manager
from .core.config import ServiceType
from .core.models import ModelResponse

logger = logging.getLogger(__name__)


class ModelService:
    """
    模型服務統一接口

    這個類封裝了模型管理器，提供簡潔的 API
    每個需要模型服務的組件應該依賴注入這個服務
    """

    def __init__(self, manager: Optional[ModelManager] = None):
        """
        初始化模型服務

        Args:
            manager: 可選的自定義管理器，如果不提供則使用默認管理器
        """
        self.manager = manager or create_default_manager()

    async def qa_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ModelResponse:
        """QA 服務專用的模型調用"""
        return await self.manager.complete(
            service_type=ServiceType.QA,
            messages=messages,
            **kwargs
        )

    async def finance_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ModelResponse:
        """財務分析服務專用的模型調用"""
        return await self.manager.complete(
            service_type=ServiceType.FINANCE,
            messages=messages,
            **kwargs
        )

    async def ocr_completion(
        self,
        messages: List[Dict[str, str]],
        images: Optional[List[str]] = None,
        **kwargs
    ) -> ModelResponse:
        """OCR 服務專用的模型調用"""
        return await self.manager.complete(
            service_type=ServiceType.OCR,
            messages=messages,
            images=images,
            **kwargs
        )

    async def health_check(self) -> Dict[str, bool]:
        """健康檢查所有提供商"""
        return await self.manager.health_check()

    def get_stats(self) -> Dict[str, Any]:
        """獲取服務統計信息"""
        return self.manager.get_stats()

    async def close(self):
        """關閉服務，清理資源"""
        await self.manager.close()


# 創建默認服務實例的工廠函數
def create_model_service() -> ModelService:
    """
    創建模型服務實例

    每個需要模型服務的組件都應該調用這個函數
    而不是依賴全局變量
    """
    return ModelService()


# 向後兼容的便利函數
async def qa_completion(messages: List[Dict], **kwargs) -> ModelResponse:
    """
    QA 服務便利函數

    注意：這是為了向後兼容，新代碼應該使用 ModelService
    """
    service = create_model_service()
    try:
        return await service.qa_completion(messages, **kwargs)
    finally:
        await service.close()


async def finance_completion(messages: List[Dict], **kwargs) -> ModelResponse:
    """
    財務分析服務便利函數

    注意：這是為了向後兼容，新代碼應該使用 ModelService
    """
    service = create_model_service()
    try:
        return await service.finance_completion(messages, **kwargs)
    finally:
        await service.close()


async def ocr_completion(
    messages: List[Dict],
    images: Optional[List[str]] = None,
    **kwargs
) -> ModelResponse:
    """
    OCR 服務便利函數

    注意：這是為了向後兼容，新代碼應該使用 ModelService
    """
    service = create_model_service()
    try:
        return await service.ocr_completion(messages, images, **kwargs)
    finally:
        await service.close()