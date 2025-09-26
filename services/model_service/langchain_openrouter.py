"""
LangChain 兼容的 OpenRouter 包裝器
用於財務分析服務中替換 ChatOpenAI
"""

import os
import asyncio
import logging
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, AIMessageChunk
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult, LLMResult, ChatGenerationChunk
from pydantic import Field

try:
    from .providers.openrouter import OpenRouterProvider
    from .exceptions import QuotaExceededError
except ImportError:
    # 直接從絕對路徑導入，避免相對導入問題
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from providers.openrouter import OpenRouterProvider
    from exceptions import QuotaExceededError

logger = logging.getLogger(__name__)


class OpenRouterChatModel(BaseChatModel):
    """LangChain 兼容的 OpenRouter 聊天模型"""

    # 模型配置
    model_name: str = Field(default="meta-llama/llama-4-maverick:free")
    temperature: float = Field(default=0.01)
    max_tokens: Optional[int] = Field(default=None)

    # OpenRouter 配置
    api_key: str = Field(default="")
    base_url: str = Field(default="https://openrouter.ai/api/v1")
    app_name: str = Field(default="Finance Helper")
    site_url: str = Field(default="https://your-app.com")

    # 內部提供商
    _provider: Optional[OpenRouterProvider] = None

    def __init__(self, **data: Any):
        super().__init__(**data)

        # 如果沒有提供 API key，從環境變數獲取
        if not self.api_key:
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not self.api_key:
                raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")

        # 初始化 OpenRouter 提供商
        self._provider = OpenRouterProvider(
            api_key=self.api_key,
            base_url=self.base_url,
            app_name=self.app_name,
            site_url=self.site_url
        )

    @property
    def _llm_type(self) -> str:
        return "openrouter-chat"

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """轉換 LangChain 消息格式為 OpenRouter API 格式"""
        converted = []
        for message in messages:
            if isinstance(message, HumanMessage):
                converted.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                converted.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                converted.append({"role": "system", "content": message.content})
            else:
                # 其他類型的消息作為用戶消息處理
                converted.append({"role": "user", "content": str(message.content)})

        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成響應"""
        # 使用 asyncio 運行異步方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self._agenerate(messages, stop, None, **kwargs)
            )
        finally:
            loop.close()

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """異步生成響應"""
        if not self._provider:
            raise ValueError("OpenRouter provider not initialized")

        try:
            # 轉換消息格式
            api_messages = self._convert_messages(messages)

            # 準備請求參數
            request_params = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }

            # 如果有 stop 序列，添加到請求參數
            if stop:
                request_params["stop"] = stop

            # 調用 OpenRouter API
            response = await self._provider.chat_completion(
                messages=api_messages,
                model=self.model_name,
                **request_params
            )

            # 解析響應
            if "choices" not in response or not response["choices"]:
                raise ValueError("Invalid response from OpenRouter API")

            choice = response["choices"][0]
            content = choice["message"]["content"]

            # 創建 ChatGeneration
            generation = ChatGeneration(
                message=AIMessage(content=content),
                generation_info={
                    "finish_reason": choice.get("finish_reason"),
                    "model": response.get("model"),
                    "usage": response.get("usage", {}),
                }
            )

            return ChatResult(generations=[generation])

        except QuotaExceededError as e:
            logger.error(f"OpenRouter quota exceeded: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in OpenRouter chat completion: {e}")
            raise

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """同步流式生成 (不實現，使用批量生成)"""
        result = self._generate(messages, stop, run_manager, **kwargs)
        yield result.generations[0]

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGeneration]:
        """異步流式生成"""
        if not self._provider:
            raise ValueError("OpenRouter provider not initialized")

        try:
            api_messages = self._convert_messages(messages)

            request_params = {
                "temperature": kwargs.get("temperature", self.temperature),
            }

            if stop:
                request_params["stop"] = stop

            content_parts = []
            async for chunk in self._provider.stream_completion(
                messages=api_messages,
                model=self.model_name,
                **request_params
            ):
                content_parts.append(chunk)
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content=chunk),
                    generation_info={"partial": True}
                )

            # 最終完整消息
            full_content = "".join(content_parts)
            yield ChatGenerationChunk(
                message=AIMessageChunk(content=full_content),
                generation_info={"partial": False}
            )

        except Exception as e:
            logger.error(f"Error in OpenRouter streaming: {e}")
            raise

    async def aclose(self):
        """關閉資源"""
        if self._provider:
            await self._provider.close()

    def __del__(self):
        """析構函數"""
        if self._provider:
            asyncio.create_task(self._provider.close())


# 便利的工廠函數
def create_openrouter_chat(
    model: str = "meta-llama/llama-4-maverick:free",
    temperature: float = 0.01,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> OpenRouterChatModel:
    """創建 OpenRouter 聊天模型實例"""

    config = {
        "model_name": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }

    if api_key:
        config["api_key"] = api_key

    return OpenRouterChatModel(**config)


# 預設模型配置
RECOMMENDED_MODELS = {
    "financial_analysis": "meta-llama/llama-4-maverick:free",
    "reasoning": "deepseek/deepseek-r1:free",
    "structured_output": "mistralai/mistral-small-3.1:free",
}


def get_financial_analysis_model(**kwargs) -> OpenRouterChatModel:
    """獲取用於財務分析的推薦模型"""
    return create_openrouter_chat(
        model=RECOMMENDED_MODELS["financial_analysis"],
        **kwargs
    )