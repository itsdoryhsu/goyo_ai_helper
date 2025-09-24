"""
OpenAI 直接 API 提供者
"""

import os
import logging
import json
from typing import Dict, Any, List, AsyncGenerator
import httpx

from .base import ModelProvider
from ..exceptions import ModelError, QuotaExceededError

logger = logging.getLogger(__name__)


class OpenAIProvider(ModelProvider):
    """OpenAI 直接 API 提供者"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """使用 OpenAI API 進行聊天完成"""

        if not self.api_key:
            raise ModelError("OpenAI API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 429:
                    raise QuotaExceededError(f"OpenAI quota exceeded for model {model}")
                elif response.status_code != 200:
                    raise ModelError(f"OpenAI API error {response.status_code}: {response.text}")

                return response.json()

        except httpx.TimeoutException:
            raise ModelError(f"OpenAI API timeout for model {model}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise ModelError(f"OpenAI API error: {str(e)}")

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """使用 OpenAI API 進行流式聊天完成"""

        if not self.api_key:
            raise ModelError("OpenAI API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                ) as response:
                    if response.status_code == 429:
                        raise QuotaExceededError(f"OpenAI quota exceeded for model {model}")
                    elif response.status_code != 200:
                        raise ModelError(f"OpenAI API error {response.status_code}")

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

        except httpx.TimeoutException:
            raise ModelError(f"OpenAI API timeout for model {model}")
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            raise ModelError(f"OpenAI stream error: {str(e)}")

    async def vision_completion(
        self,
        messages: List[Dict],
        images: List[str],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Dict[str, Any]:
        """使用 OpenAI API 進行視覺完成"""

        # 將圖片添加到最後一個用戶消息中
        if images and messages:
            last_message = messages[-1]
            if last_message["role"] == "user":
                content = [{"type": "text", "text": last_message["content"]}]

                for image_data in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    })

                last_message["content"] = content

        return await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    async def health_check(self) -> bool:
        """檢查 OpenAI API 健康狀態"""
        try:
            if not self.api_key:
                return False

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=10.0
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False