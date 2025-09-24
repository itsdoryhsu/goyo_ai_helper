"""
OpenRouter 模型提供商
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from .base import ModelProvider
from ..exceptions import QuotaExceededError

logger = logging.getLogger(__name__)




class OpenRouterProvider(ModelProvider):
    """OpenRouter 提供商實現"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        app_name: str = "財務助手",
        site_url: str = "https://your-app.com",
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.app_name = app_name
        self.site_url = site_url
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
    ) -> Dict[str, Any]:
        """實現聊天完成"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            logger.debug(f"OpenRouter request: {model} with {len(messages)} messages")

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )

            if response.status_code == 429:
                raise QuotaExceededError(f"Quota exceeded for model {model}")

            response.raise_for_status()
            result = response.json()

            logger.debug(f"OpenRouter response: {result.get('usage', {})}")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise QuotaExceededError(f"Quota exceeded for model {model}")
            logger.error(f"OpenRouter HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """實現流式聊天完成"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                **kwargs
            }

            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                if response.status_code == 429:
                    raise QuotaExceededError(f"Quota exceeded for model {model}")

                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise QuotaExceededError(f"Quota exceeded for model {model}")
            logger.error(f"OpenRouter stream error: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter stream error: {e}")
            raise

    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        images: List[str],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """實現視覺理解完成"""
        try:
            # 轉換消息格式以支援圖片
            vision_messages = []
            for msg in messages:
                if msg["role"] == "user" and images:
                    # 為用戶消息添加圖片
                    content = [{"type": "text", "text": msg["content"]}]
                    for image in images:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image}"}
                        })
                    vision_messages.append({
                        "role": "user",
                        "content": content
                    })
                else:
                    vision_messages.append(msg)

            return await self.chat_completion(
                messages=vision_messages,
                model=model,
                **kwargs
            )

        except Exception as e:
            logger.error(f"OpenRouter vision error: {e}")
            raise

    async def health_check(self) -> bool:
        """健康檢查"""
        try:
            test_messages = [{"role": "user", "content": "ping"}]
            result = await self.chat_completion(
                messages=test_messages,
                model="x-ai/grok-4-fast:free",
                max_tokens=1
            )
            return "choices" in result
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {e}")
            return False

    async def close(self):
        """關閉 HTTP 客戶端"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()