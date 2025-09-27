import logging
from typing import Dict, Any
import google.generativeai as genai

from .base import LLMProvider
from ..core.config import QAConfig
from ..core.exceptions import LLMError

logger = logging.getLogger(__name__)

class GeminiQAProvider(LLMProvider):
    """Gemini QA LLM提供商"""

    def __init__(self, api_key: str, model_name: str = "models/gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化Gemini客戶端"""
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini QA provider initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini QA provider: {e}")
            raise LLMError(f"Gemini初始化失敗: {e}")

    async def generate_answer(self, question: str, context: str) -> Dict[str, Any]:
        """使用Gemini生成答案"""
        if not self.client:
            raise LLMError("Gemini客戶端未初始化")

        try:
            # 構建提示
            prompt = f"{QAConfig.SYSTEM_PROMPT.format(context=context)}\n\n用戶問題: {question}"

            # 配置生成參數
            generation_config = {
                "temperature": QAConfig.LLM_TEMPERATURE,
                "max_output_tokens": QAConfig.LLM_MAX_TOKENS,
            }

            # 調用Gemini
            response = await self.client.generate_content_async(
                prompt,
                generation_config=generation_config
            )

            # 提取使用量信息
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') and response.usage_metadata else None

            return {
                "answer": response.text,
                "model": self.model_name,
                "provider": "gemini",
                "tokens": {
                    "total": usage.total_token_count if usage else 0,
                    "prompt": usage.prompt_token_count if usage else 0,
                    "completion": usage.candidates_token_count if usage else 0
                },
                "cost": 0.0  # Gemini通常不提供實時成本信息
            }

        except Exception as e:
            logger.error(f"Gemini QA generation failed: {e}")
            raise LLMError(f"Gemini生成答案失敗: {e}")

    def get_model_info(self) -> Dict[str, str]:
        """獲取模型信息"""
        return {
            "provider": "gemini",
            "model": self.model_name,
            "api_version": "v1"
        }