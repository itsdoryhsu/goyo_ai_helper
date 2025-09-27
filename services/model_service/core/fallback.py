"""
統一的備援策略實現
消除重複的備援邏輯，使用乾淨的策略模式
"""

import logging
import asyncio
from typing import List, Optional

from .models import ModelRequest, ModelResponse, QuotaExceededError, ProviderUnavailableError
from .config import ModelConfig

logger = logging.getLogger(__name__)


class FallbackStrategy:
    """備援策略 - 統一處理所有提供商的備援邏輯"""

    def __init__(self, fallback_chain: List[ModelConfig]):
        """
        初始化備援策略

        Args:
            fallback_chain: 按優先級排序的配置鏈
        """
        self.fallback_chain = fallback_chain

    async def execute(
        self,
        request: ModelRequest,
        provider_registry: dict,
        primary_config: ModelConfig
    ) -> ModelResponse:
        """
        執行備援策略

        Args:
            request: 模型請求
            provider_registry: 提供商註冊表
            primary_config: 主要配置

        Returns:
            模型回應

        Raises:
            ProviderUnavailableError: 所有提供商都不可用
        """
        last_error = None
        attempted_providers = []

        # 首先嘗試主要配置
        configs_to_try = [primary_config] + self.fallback_chain

        for config in configs_to_try:
            provider = provider_registry.get(config.provider.value)
            if not provider:
                logger.warning(f"Provider {config.provider.value} not available in registry")
                continue

            if config.provider.value in attempted_providers:
                continue  # 避免重複嘗試同一個提供商

            try:
                logger.info(f"Trying provider: {config.provider.value} with model: {config.model}")

                # 執行請求
                response = await self._execute_request(provider, request, config)

                # 標記是否使用了備援
                response.fallback_used = (config != primary_config)

                logger.info(f"Successfully got response from {config.provider.value}")
                return response

            except QuotaExceededError as e:
                logger.warning(f"Quota exceeded for {config.provider.value}: {e}")
                attempted_providers.append(config.provider.value)
                last_error = e
                continue

            except Exception as e:
                logger.error(f"Provider {config.provider.value} failed: {e}")
                attempted_providers.append(config.provider.value)
                last_error = e
                continue

        # 所有提供商都失敗了
        error_msg = f"All providers exhausted. Last error: {last_error}"
        logger.error(error_msg)
        raise ProviderUnavailableError(error_msg)

    async def _execute_request(
        self,
        provider,
        request: ModelRequest,
        config: ModelConfig
    ) -> ModelResponse:
        """
        執行單個提供商請求

        Args:
            provider: 提供商實例
            request: 請求對象
            config: 配置對象

        Returns:
            模型回應
        """
        # 準備參數，允許請求覆蓋配置
        params = {
            "model": config.model,
            "temperature": request.temperature or config.temperature,
            "max_tokens": request.max_tokens or config.max_tokens,
        }

        # 根據請求類型選擇方法
        if request.images:
            # 視覺任務
            return await provider.vision_completion(
                messages=request.messages,
                images=request.images,
                **params
            )
        elif request.stream:
            # 流式回應 (暫不實現)
            raise NotImplementedError("Streaming not yet implemented")
        else:
            # 標準聊天完成
            return await provider.chat_completion(
                messages=request.messages,
                **params
            )


class CircuitBreaker:
    """簡單的熔斷器 - 避免持續嘗試失敗的提供商"""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_counts = {}
        self.last_failure_times = {}

    def is_available(self, provider_name: str) -> bool:
        """檢查提供商是否可用"""
        import time

        current_time = time.time()

        # 檢查是否需要重置
        if provider_name in self.last_failure_times:
            if current_time - self.last_failure_times[provider_name] > self.reset_timeout:
                self.failure_counts.pop(provider_name, None)
                self.last_failure_times.pop(provider_name, None)

        # 檢查失敗計數
        failure_count = self.failure_counts.get(provider_name, 0)
        return failure_count < self.failure_threshold

    def record_failure(self, provider_name: str):
        """記錄失敗"""
        import time

        self.failure_counts[provider_name] = self.failure_counts.get(provider_name, 0) + 1
        self.last_failure_times[provider_name] = time.time()

        logger.warning(
            f"Provider {provider_name} failure count: {self.failure_counts[provider_name]}"
        )

    def record_success(self, provider_name: str):
        """記錄成功 - 重置失敗計數"""
        self.failure_counts.pop(provider_name, None)
        self.last_failure_times.pop(provider_name, None)