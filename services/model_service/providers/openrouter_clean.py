"""
乾淨的 OpenRouter 提供商實現
消除複雜性，專注核心功能
"""

import logging
import httpx
import json
from typing import Dict, Any, List, Optional

from .base_clean import ModelProvider
from ..core.models import ModelResponse, QuotaExceededError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class CleanOpenRouterProvider(ModelProvider):
    """乾淨的 OpenRouter 提供商實現"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        app_name: str = "Finance Assistant",
        site_url: str = "https://your-app.com",
        timeout: float = 30.0
    ):
        super().__init__("openrouter")
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        # 創建 HTTP 客戶端
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": site_url,
                "X-Title": app_name,
                "Content-Type": "application/json"
            },
            timeout=timeout
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """OpenRouter 聊天完成"""

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # 添加其他參數
        payload.update(kwargs)

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )

            if response.status_code == 429:
                raise QuotaExceededError(f"OpenRouter quota exceeded for model {model}")

            if response.status_code != 200:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                raise ProviderUnavailableError(error_msg)

            data = response.json()

            # 解析回應
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return ModelResponse(
                content=content,
                provider=self.name,
                model=model,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                },
                cost=self._calculate_cost(usage, model)
            )

        except httpx.RequestError as e:
            error_msg = f"OpenRouter network error: {e}"
            logger.error(error_msg)
            raise ProviderUnavailableError(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"OpenRouter response parsing error: {e}"
            logger.error(error_msg)
            raise ProviderUnavailableError(error_msg)

    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        images: List[str],
        model: str,
        **kwargs
    ) -> ModelResponse:
        """OpenRouter 視覺完成"""

        # 轉換消息格式以支持圖片
        enhanced_messages = self._format_vision_messages(messages, images)

        # 使用標準聊天完成接口
        return await self.chat_completion(enhanced_messages, model, **kwargs)

    def _format_vision_messages(
        self,
        messages: List[Dict[str, str]],
        images: List[str]
    ) -> List[Dict[str, Any]]:
        """格式化視覺消息 - OpenRouter 格式"""

        enhanced_messages = []

        for message in messages:
            if message["role"] == "user" and images:
                # 為用戶消息添加圖片
                content = [
                    {"type": "text", "text": message["content"]}
                ]

                for image in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image}"}
                    })

                enhanced_messages.append({
                    "role": "user",
                    "content": content
                })
                images = []  # 只在第一條用戶消息中添加圖片
            else:
                enhanced_messages.append(message)

        return enhanced_messages

    def _calculate_cost(self, usage: Dict[str, int], model: str) -> float:
        """計算成本 - 簡化版本"""
        # 大多數免費模型成本為 0
        if ":free" in model.lower() or "free" in model.lower():
            return 0.0

        # 其他模型的成本計算可以根據需要實現
        return 0.0

    async def close(self):
        """關閉 HTTP 客戶端"""
        await self.client.aclose()