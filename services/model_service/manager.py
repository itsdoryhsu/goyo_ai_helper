"""
模型服務管理器
統一管理所有服務的模型調用
"""

import logging
from typing import Dict, Any, List, Optional

from .config.models import ServiceType
from .config.settings import get_openrouter_config, get_service_config, get_backup_models
from .providers.openrouter import OpenRouterProvider, QuotaExceededError
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider
from .exceptions import ModelError

logger = logging.getLogger(__name__)


class ServiceModelManager:
    """服務專用模型管理器"""

    def __init__(self):
        self.openrouter_provider = None
        self.openai_provider = None
        self.gemini_provider = None
        self.backup_models = get_backup_models()
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化所有提供商"""
        # 初始化 OpenRouter 提供商
        try:
            config = get_openrouter_config()
            if config["api_key"]:
                self.openrouter_provider = OpenRouterProvider(
                    api_key=config["api_key"],
                    base_url=config["base_url"],
                    app_name=config["app_name"],
                    site_url=config["site_url"]
                )
                logger.info("OpenRouter provider initialized successfully")
            else:
                logger.warning("OPENROUTER_API_KEY not set")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter provider: {e}")

        # 初始化 OpenAI 提供商
        try:
            self.openai_provider = OpenAIProvider()
            logger.info("OpenAI provider initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")

        # 初始化 Gemini 提供商
        try:
            self.gemini_provider = GeminiProvider()
            logger.info("Gemini provider initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")

    def get_service_config(self, service_type: ServiceType) -> Dict[str, Any]:
        """獲取特定服務的模型配置"""
        return get_service_config(service_type.value)

    async def chat_completion(
        self,
        service_type: ServiceType,
        messages: List[Dict[str, str]],
        **override_params
    ) -> Dict[str, Any]:
        """為特定服務執行聊天完成"""
        if not self.openrouter_provider:
            raise RuntimeError("OpenRouter provider not initialized")

        config = self.get_service_config(service_type)
        config.update(override_params)  # 允許臨時覆蓋參數

        try:
            logger.info(f"Using {config['model']} for {service_type.value} service")
            return await self.openrouter_provider.chat_completion(
                messages=messages,
                **config
            )
        except QuotaExceededError as e:
            logger.warning(f"Quota exceeded for {config['model']}, trying backup")
            return await self._try_backup_model(service_type, messages, **config)

    async def vision_completion(
        self,
        service_type: ServiceType,
        messages: List[Dict[str, str]],
        images: List[str],
        **override_params
    ) -> Dict[str, Any]:
        """為特定服務執行視覺理解（OCR 專用）"""
        if not self.openrouter_provider:
            raise RuntimeError("OpenRouter provider not initialized")

        config = self.get_service_config(service_type)
        config.update(override_params)

        try:
            logger.info(f"Using {config['model']} for {service_type.value} vision task")
            return await self.openrouter_provider.vision_completion(
                messages=messages,
                images=images,
                **config
            )
        except QuotaExceededError as e:
            logger.warning(f"Quota exceeded for {config['model']}, trying backup")
            # 嘗試直接 API 的視覺模型備選
            if self.gemini_provider:
                try:
                    logger.info("Trying Gemini backup for vision task")
                    backup_config = config.copy()
                    backup_config["model"] = "gemini-1.5-pro"
                    return await self.gemini_provider.vision_completion(
                        messages=messages,
                        images=images,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"Gemini vision backup failed: {e}")

            if self.openai_provider:
                try:
                    logger.info("Trying OpenAI backup for vision task")
                    backup_config = config.copy()
                    backup_config["model"] = "gpt-4o"
                    return await self.openai_provider.vision_completion(
                        messages=messages,
                        images=images,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"OpenAI vision backup failed: {e}")

            # 最後嘗試 OpenRouter 付費模型
            backup_config = config.copy()
            backup_config["model"] = self.backup_models["vision"]
            return await self.openrouter_provider.vision_completion(
                messages=messages,
                images=images,
                **backup_config
            )

    async def _try_backup_model(
        self,
        service_type: ServiceType,
        messages: List[Dict[str, str]],
        **config
    ) -> Dict[str, Any]:
        """嘗試使用備選模型（直接 API 調用）"""
        # 優先嘗試直接 API 調用的備選模型
        if service_type == ServiceType.QA:
            # QA 服務：嘗試 OpenAI GPT-4
            if self.openai_provider:
                try:
                    logger.info("Trying OpenAI backup for QA service")
                    backup_config = config.copy()
                    backup_config["model"] = "gpt-4"
                    return await self.openai_provider.chat_completion(
                        messages=messages,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"OpenAI backup failed: {e}")

            # 再嘗試 Gemini
            if self.gemini_provider:
                try:
                    logger.info("Trying Gemini backup for QA service")
                    backup_config = config.copy()
                    backup_config["model"] = "gemini-1.5-pro"
                    return await self.gemini_provider.chat_completion(
                        messages=messages,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"Gemini backup failed: {e}")

        elif service_type == ServiceType.FINANCE:
            # 財務分析：嘗試 OpenAI GPT-4
            if self.openai_provider:
                try:
                    logger.info("Trying OpenAI backup for Finance service")
                    backup_config = config.copy()
                    backup_config["model"] = "gpt-4"
                    return await self.openai_provider.chat_completion(
                        messages=messages,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"OpenAI backup failed: {e}")

        elif service_type == ServiceType.OCR:
            # OCR 服務：嘗試 Gemini Vision
            if self.gemini_provider:
                try:
                    logger.info("Trying Gemini backup for OCR service")
                    backup_config = config.copy()
                    backup_config["model"] = "gemini-1.5-pro"
                    return await self.gemini_provider.chat_completion(
                        messages=messages,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"Gemini backup failed: {e}")

            # 再嘗試 OpenAI GPT-4 Vision
            if self.openai_provider:
                try:
                    logger.info("Trying OpenAI Vision backup for OCR service")
                    backup_config = config.copy()
                    backup_config["model"] = "gpt-4o"
                    return await self.openai_provider.chat_completion(
                        messages=messages,
                        **backup_config
                    )
                except Exception as e:
                    logger.warning(f"OpenAI Vision backup failed: {e}")

        # 最後嘗試 OpenRouter 的其他免費模型
        if self.openrouter_provider:
            backup_models = []
            if service_type == ServiceType.QA:
                backup_models = ["google/gemini-2.0-flash-exp:free"]
            elif service_type == ServiceType.FINANCE:
                backup_models = ["x-ai/grok-4-fast:free"]
            elif service_type == ServiceType.OCR:
                backup_models = ["google/gemini-2.0-flash-exp:free"]

            for backup_model in backup_models:
                try:
                    backup_config = config.copy()
                    backup_config["model"] = backup_model
                    logger.info(f"Trying OpenRouter backup: {backup_model}")
                    return await self.openrouter_provider.chat_completion(
                        messages=messages,
                        **backup_config
                    )
                except QuotaExceededError:
                    logger.warning(f"OpenRouter backup {backup_model} also exhausted")
                    continue
                except Exception as e:
                    logger.error(f"OpenRouter backup {backup_model} failed: {e}")
                    continue

        raise RuntimeError(f"All backup models exhausted for {service_type.value} service")

    async def health_check(self) -> bool:
        """健康檢查"""
        if not self.openrouter_provider:
            return False
        return await self.openrouter_provider.health_check()

    async def close(self):
        """關閉資源"""
        if self.openrouter_provider:
            await self.openrouter_provider.close()
        # OpenAI 和 Gemini 提供商使用 httpx，會自動關閉


# 全域服務模型管理器實例
model_manager = ServiceModelManager()


# 便利函數
async def qa_completion(messages: List[Dict], **kwargs) -> Dict[str, Any]:
    """QA 服務專用的模型調用"""
    return await model_manager.chat_completion(ServiceType.QA, messages, **kwargs)


async def finance_completion(messages: List[Dict], **kwargs) -> Dict[str, Any]:
    """財務分析服務專用的模型調用"""
    return await model_manager.chat_completion(ServiceType.FINANCE, messages, **kwargs)


async def ocr_completion(messages: List[Dict], images: List[str] = None, **kwargs) -> Dict[str, Any]:
    """OCR 服務專用的模型調用"""
    if images:
        return await model_manager.vision_completion(ServiceType.OCR, messages, images, **kwargs)
    else:
        return await model_manager.chat_completion(ServiceType.OCR, messages, **kwargs)