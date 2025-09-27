import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback

from .base import LLMProvider
from ..core.config import QAConfig
from ..core.exceptions import LLMError

logger = logging.getLogger(__name__)

class OpenAIQAProvider(LLMProvider):
    """OpenAI QA LLM提供商"""

    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo-16k"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化OpenAI客戶端"""
        try:
            self.client = ChatOpenAI(
                api_key=self.api_key,
                model=self.model_name,
                temperature=QAConfig.LLM_TEMPERATURE,
                max_tokens=QAConfig.LLM_MAX_TOKENS,
                timeout=30.0
            )
            logger.info(f"OpenAI QA provider initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI QA provider: {e}")
            raise LLMError(f"OpenAI初始化失敗: {e}")

    async def generate_answer(self, question: str, context: str) -> Dict[str, Any]:
        """使用OpenAI生成答案"""
        if not self.client:
            raise LLMError("OpenAI客戶端未初始化")

        try:
            # 構建提示
            prompt = QAConfig.SYSTEM_PROMPT.format(context=context)

            # 使用callback追蹤token使用
            with get_openai_callback() as cb:
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question}
                ]

                response = await self.client.ainvoke(messages)

                return {
                    "answer": response.content,
                    "model": self.model_name,
                    "provider": "openai",
                    "tokens": {
                        "total": cb.total_tokens,
                        "prompt": cb.prompt_tokens,
                        "completion": cb.completion_tokens
                    },
                    "cost": cb.total_cost
                }

        except Exception as e:
            logger.error(f"OpenAI QA generation failed: {e}")
            raise LLMError(f"OpenAI生成答案失敗: {e}")

    def get_model_info(self) -> Dict[str, str]:
        """獲取模型信息"""
        return {
            "provider": "openai",
            "model": self.model_name,
            "base_url": QAConfig.OPENAI_BASE_URL
        }