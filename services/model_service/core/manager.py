"""
乾淨的模型管理器
消除全局狀態，使用依賴注入，單一職責原則
"""

import logging
import time
from typing import Dict, Optional

from .models import ModelRequest, ModelResponse, ServiceType
from .config import ServiceConfig, ModelConfig
from .fallback import FallbackStrategy, CircuitBreaker

logger = logging.getLogger(__name__)


class ModelManager:
    """
    模型管理器 - 乾淨的設計

    職責：
    1. 管理提供商註冊表
    2. 路由請求到正確的提供商
    3. 協調備援策略
    4. 記錄性能指標
    """

    def __init__(self):
        self.providers = {}  # provider_name -> provider_instance
        self.circuit_breaker = CircuitBreaker()
        self._request_count = 0
        self._total_duration = 0.0

    def register_provider(self, name: str, provider):
        """註冊提供商"""
        self.providers[name] = provider
        logger.info(f"Registered provider: {name}")

    async def complete(
        self,
        service_type: ServiceType,
        messages: list,
        images: Optional[list] = None,
        stream: bool = False,
        **override_params
    ) -> ModelResponse:
        """
        執行模型完成請求

        Args:
            service_type: 服務類型
            messages: 對話消息
            images: 圖片 (用於視覺任務)
            stream: 是否流式回應
            **override_params: 參數覆蓋

        Returns:
            模型回應
        """
        start_time = time.time()

        try:
            # 創建請求對象
            request = ModelRequest(
                messages=messages,
                service_type=service_type.value,
                images=images,
                stream=stream,
                temperature=override_params.get('temperature'),
                max_tokens=override_params.get('max_tokens'),
                timeout=override_params.get('timeout')
            )

            # 獲取配置
            primary_config = ServiceConfig.get_primary_config(service_type)
            fallback_chain = ServiceConfig.get_fallback_chain(service_type)

            # 過濾可用的提供商 (熔斷器檢查)
            available_chain = [
                config for config in fallback_chain
                if self.circuit_breaker.is_available(config.provider.value)
            ]

            if not available_chain:
                logger.warning("All providers are circuit-broken, resetting...")
                available_chain = fallback_chain  # 重置，給一次機會

            # 執行備援策略
            strategy = FallbackStrategy(available_chain)
            response = await strategy.execute(request, self.providers, primary_config)

            # 記錄成功
            self.circuit_breaker.record_success(response.provider)

            # 更新統計
            duration = time.time() - start_time
            response.duration = duration
            self._update_stats(duration)

            logger.info(
                f"Request completed: service={service_type.value}, "
                f"provider={response.provider}, duration={duration:.2f}s, "
                f"fallback={response.fallback_used}"
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            # 記錄失敗到熔斷器
            if hasattr(e, 'provider'):
                self.circuit_breaker.record_failure(e.provider)

            logger.error(f"Request failed: {e}, duration={duration:.2f}s")

            # 返回錯誤回應
            return ModelResponse(
                content=f"模型服務暫時不可用: {str(e)}",
                provider="error",
                model="none",
                error=str(e),
                duration=duration
            )

    async def health_check(self) -> Dict[str, bool]:
        """
        健康檢查所有提供商

        Returns:
            提供商名稱到健康狀態的映射
        """
        health_status = {}

        for name, provider in self.providers.items():
            try:
                # 使用簡單的測試請求
                test_messages = [{"role": "user", "content": "test"}]
                await provider.chat_completion(
                    messages=test_messages,
                    model="test",  # 假設提供商會處理無效模型
                    max_tokens=1
                )
                health_status[name] = True
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                health_status[name] = False

        return health_status

    def get_stats(self) -> Dict[str, float]:
        """獲取性能統計"""
        if self._request_count == 0:
            return {"request_count": 0, "average_duration": 0.0}

        return {
            "request_count": self._request_count,
            "average_duration": self._total_duration / self._request_count
        }

    def _update_stats(self, duration: float):
        """更新統計信息"""
        self._request_count += 1
        self._total_duration += duration

    async def close(self):
        """清理資源"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()

        logger.info("ModelManager closed")


# 便利函數 - 但不使用全局狀態
def create_default_manager():
    """創建默認配置的管理器 - 工廠函數"""
    from .config import ProviderConfig
    from ..providers.openrouter_clean import CleanOpenRouterProvider
    from ..providers.openai_clean import CleanOpenAIProvider
    from ..providers.gemini_clean import CleanGeminiProvider

    manager = ModelManager()

    # 直接註冊所有可用的提供商（避免使用 factory）
    try:
        openrouter_config = ProviderConfig.get_openrouter_config()
        if openrouter_config["api_key"]:
            manager.register_provider("openrouter", CleanOpenRouterProvider(**openrouter_config))
            logger.info("OpenRouter provider initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenRouter provider: {e}")

    try:
        openai_config = ProviderConfig.get_openai_config()
        if openai_config["api_key"]:
            manager.register_provider("openai", CleanOpenAIProvider(**openai_config))
            logger.info("OpenAI provider initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI provider: {e}")

    try:
        gemini_config = ProviderConfig.get_gemini_config()
        if gemini_config["api_key"]:
            # Gemini provider 只接受 api_key，不需要 model_name
            manager.register_provider("gemini", CleanGeminiProvider(api_key=gemini_config["api_key"]))
            logger.info("Gemini provider initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini provider: {e}")

    return manager