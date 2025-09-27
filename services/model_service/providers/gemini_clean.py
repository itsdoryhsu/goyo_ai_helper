"""
乾淨的 Gemini 提供商實現
"""

import logging
import httpx
import json
from typing import Dict, Any, List, Optional

from .base_clean import ModelProvider
from ..core.models import ModelResponse, QuotaExceededError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class CleanGeminiProvider(ModelProvider):
    """乾淨的 Gemini 提供商實現"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 30.0
    ):
        super().__init__("gemini")
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        # 創建 HTTP 客戶端
        self.client = httpx.AsyncClient(
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
        """Gemini 聊天完成"""

        # 轉換消息格式為 Gemini 格式
        gemini_messages = self._convert_to_gemini_format(messages)

        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        # 清理模型名稱
        clean_model = model.replace("models/", "")

        try:
            url = f"{self.base_url}/models/{clean_model}:generateContent"
            response = await self.client.post(
                url,
                json=payload,
                params={"key": self.api_key}
            )

            if response.status_code == 429:
                raise QuotaExceededError(f"Gemini quota exceeded for model {model}")

            if response.status_code != 200:
                error_msg = f"Gemini API error: {response.status_code} - {response.text}"
                raise ProviderUnavailableError(error_msg)

            data = response.json()

            # 解析回應
            if "candidates" not in data or not data["candidates"]:
                raise ProviderUnavailableError("No candidates in Gemini response")

            candidate = data["candidates"][0]

            # 處理不同的回應格式
            content = self._extract_content_from_candidate(candidate)
            usage_metadata = data.get("usageMetadata", {})

            return ModelResponse(
                content=content,
                provider=self.name,
                model=model,
                usage={
                    "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                    "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    "total_tokens": usage_metadata.get("totalTokenCount", 0)
                },
                cost=0.0  # Gemini 通常免費
            )

        except httpx.RequestError as e:
            error_msg = f"Gemini network error: {e}"
            logger.error(error_msg)
            raise ProviderUnavailableError(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"Gemini response parsing error: {e}"
            logger.error(error_msg)
            raise ProviderUnavailableError(error_msg)

    def _convert_to_gemini_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """轉換消息格式為 Gemini 格式"""
        gemini_messages = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            # Gemini 角色映射
            if role == "system":
                # Gemini 沒有系統角色，將其轉為用戶消息
                gemini_role = "user"
                content = f"Instructions: {content}"
            elif role == "assistant":
                gemini_role = "model"
            else:
                gemini_role = "user"

            gemini_messages.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

        return gemini_messages

    def _extract_content_from_candidate(self, candidate: Dict[str, Any]) -> str:
        """從 Gemini 候選回應中提取內容，處理不同的 API 回應格式"""

        # 檢查是否有 content 欄位
        if "content" not in candidate:
            # 檢查 finishReason 以了解為什麼沒有內容
            finish_reason = candidate.get("finishReason", "UNKNOWN")
            if finish_reason == "MAX_TOKENS":
                return "回應被截斷（達到最大token限制）"
            elif finish_reason == "SAFETY":
                return "回應被安全過濾器阻止"
            else:
                raise ProviderUnavailableError(f"No content in Gemini candidate, finish reason: {finish_reason}")

        content_obj = candidate["content"]

        # 標準格式：content.parts[0].text
        if "parts" in content_obj and content_obj["parts"]:
            parts = content_obj["parts"]
            if isinstance(parts, list) and len(parts) > 0:
                first_part = parts[0]
                if "text" in first_part:
                    return first_part["text"]

        # 替代格式：直接在 content 中查找文字
        if "text" in content_obj:
            return content_obj["text"]

        # 如果是空的 content（只有 role），檢查 finishReason
        if content_obj.keys() == {"role"}:
            finish_reason = candidate.get("finishReason", "UNKNOWN")
            if finish_reason == "MAX_TOKENS":
                return "回應被截斷（達到最大token限制）"
            elif finish_reason == "SAFETY":
                return "回應被安全過濾器阻止"
            else:
                return "API 回應為空"

        # 如果所有方法都失敗，記錄詳細資訊並拋出異常
        logger.error(f"無法解析 Gemini 回應格式: {content_obj}")
        raise ProviderUnavailableError(f"無法解析 Gemini 回應格式: {content_obj}")

    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        images: List[str],
        model: str,
        **kwargs
    ) -> ModelResponse:
        """Gemini 視覺完成"""

        # 轉換消息格式以支持圖片
        enhanced_messages = self._format_vision_messages(messages, images)

        payload = {
            "contents": enhanced_messages,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
            }
        }

        max_tokens = kwargs.get("max_tokens")
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        # 清理模型名稱
        clean_model = model.replace("models/", "")

        try:
            url = f"{self.base_url}/models/{clean_model}:generateContent"
            response = await self.client.post(
                url,
                json=payload,
                params={"key": self.api_key}
            )

            if response.status_code == 429:
                raise QuotaExceededError(f"Gemini quota exceeded for model {model}")

            if response.status_code != 200:
                error_msg = f"Gemini API error: {response.status_code} - {response.text}"
                raise ProviderUnavailableError(error_msg)

            data = response.json()

            # 解析回應
            if "candidates" not in data or not data["candidates"]:
                raise ProviderUnavailableError("No candidates in Gemini response")

            candidate = data["candidates"][0]
            content = self._extract_content_from_candidate(candidate)
            usage_metadata = data.get("usageMetadata", {})

            return ModelResponse(
                content=content,
                provider=self.name,
                model=model,
                usage={
                    "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                    "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    "total_tokens": usage_metadata.get("totalTokenCount", 0)
                },
                cost=0.0
            )

        except Exception as e:
            error_msg = f"Gemini vision completion error: {e}"
            logger.error(error_msg)
            raise ProviderUnavailableError(error_msg)

    def _format_vision_messages(
        self,
        messages: List[Dict[str, str]],
        images: List[str]
    ) -> List[Dict[str, Any]]:
        """格式化視覺消息 - Gemini 格式"""

        enhanced_messages = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            # 角色映射
            if role == "system":
                gemini_role = "user"
                content = f"Instructions: {content}"
            elif role == "assistant":
                gemini_role = "model"
            else:
                gemini_role = "user"

            parts = [{"text": content}]

            # 為用戶消息添加圖片
            if gemini_role == "user" and images:
                for image in images:
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image
                        }
                    })
                images = []  # 只在第一條用戶消息中添加圖片

            enhanced_messages.append({
                "role": gemini_role,
                "parts": parts
            })

        return enhanced_messages

    async def close(self):
        """關閉 HTTP 客戶端"""
        await self.client.aclose()