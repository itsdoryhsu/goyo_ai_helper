"""
Google Gemini 直接 API 提供者
"""

import os
import logging
import json
from typing import Dict, Any, List, AsyncGenerator
import httpx

from .base import ModelProvider
from ..exceptions import ModelError, QuotaExceededError

logger = logging.getLogger(__name__)


class GeminiProvider(ModelProvider):
    """Google Gemini 直接 API 提供者"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found in environment variables")

    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """將 OpenAI 格式的消息轉換為 Gemini 格式"""
        gemini_contents = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            # Gemini 只支援 user 和 model 角色
            if role == "system":
                # 將 system 消息合併到第一個 user 消息中
                if gemini_contents and gemini_contents[0]["role"] == "user":
                    gemini_contents[0]["parts"][0]["text"] = f"{content}\n\n{gemini_contents[0]['parts'][0]['text']}"
                else:
                    gemini_contents.insert(0, {
                        "role": "user",
                        "parts": [{"text": content}]
                    })
            elif role == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })

        return {"contents": gemini_contents}

    def _convert_gemini_response_to_openai_format(self, gemini_response: Dict[str, Any]) -> Dict[str, Any]:
        """將 Gemini 回應轉換為 OpenAI 格式"""
        if "candidates" not in gemini_response or not gemini_response["candidates"]:
            return {
                "choices": [],
                "usage": {}
            }

        candidate = gemini_response["candidates"][0]
        content = ""

        if "content" in candidate and "parts" in candidate["content"]:
            content = candidate["content"]["parts"][0].get("text", "")

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": gemini_response.get("usageMetadata", {})
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """使用 Gemini API 進行聊天完成"""

        if not self.api_key:
            raise ModelError("Google API key not configured")

        # 轉換為 Gemini 格式
        gemini_payload = self._convert_messages_to_gemini_format(messages)

        # 添加生成配置
        gemini_payload["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            **kwargs
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                    json=gemini_payload,
                    timeout=30.0
                )

                if response.status_code == 429:
                    raise QuotaExceededError(f"Gemini quota exceeded for model {model}")
                elif response.status_code != 200:
                    raise ModelError(f"Gemini API error {response.status_code}: {response.text}")

                gemini_response = response.json()
                return self._convert_gemini_response_to_openai_format(gemini_response)

        except httpx.TimeoutException:
            raise ModelError(f"Gemini API timeout for model {model}")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise ModelError(f"Gemini API error: {str(e)}")

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """使用 Gemini API 進行流式聊天完成"""

        if not self.api_key:
            raise ModelError("Google API key not configured")

        # 轉換為 Gemini 格式
        gemini_payload = self._convert_messages_to_gemini_format(messages)

        # 添加生成配置並啟用流式
        gemini_payload["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            **kwargs
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/models/{model}:streamGenerateContent?key={self.api_key}",
                    json=gemini_payload,
                    timeout=30.0
                ) as response:
                    if response.status_code == 429:
                        raise QuotaExceededError(f"Gemini quota exceeded for model {model}")
                    elif response.status_code != 200:
                        raise ModelError(f"Gemini API error {response.status_code}: {response.text}")

                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                if "candidates" in chunk and chunk["candidates"]:
                                    candidate = chunk["candidates"][0]
                                    if "content" in candidate and "parts" in candidate["content"]:
                                        for part in candidate["content"]["parts"]:
                                            if "text" in part:
                                                yield part["text"]
                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            raise ModelError(f"Gemini API timeout for model {model}")
        except Exception as e:
            logger.error(f"Gemini stream error: {e}")
            raise ModelError(f"Gemini stream error: {str(e)}")

    async def vision_completion(
        self,
        messages: List[Dict],
        images: List[str],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Dict[str, Any]:
        """使用 Gemini API 進行視覺完成"""

        if not self.api_key:
            raise ModelError("Google API key not configured")

        # 構建包含圖片的 Gemini 格式請求
        gemini_contents = []

        # 處理文字消息
        for message in messages:
            if message["role"] == "user":
                parts = [{"text": message["content"]}]

                # 如果這是最後一個用戶消息，添加圖片
                if message == messages[-1] and images:
                    for image_data in images:
                        parts.append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_data
                            }
                        })

                gemini_contents.append({
                    "role": "user",
                    "parts": parts
                })

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                **kwargs
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 429:
                    raise QuotaExceededError(f"Gemini quota exceeded for model {model}")
                elif response.status_code != 200:
                    raise ModelError(f"Gemini API error {response.status_code}: {response.text}")

                gemini_response = response.json()
                return self._convert_gemini_response_to_openai_format(gemini_response)

        except httpx.TimeoutException:
            raise ModelError(f"Gemini API timeout for model {model}")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise ModelError(f"Gemini API error: {str(e)}")

    async def health_check(self) -> bool:
        """檢查 Gemini API 健康狀態"""
        try:
            if not self.api_key:
                return False

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models?key={self.api_key}",
                    timeout=10.0
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False