import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI

from .base import LLMProvider
from ..core.config import QAConfig
from ..core.exceptions import LLMError

logger = logging.getLogger(__name__)

class OpenRouterQAProvider(LLMProvider):
    """OpenRouter QA LLM提供商"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化OpenRouter客戶端"""
        try:
            self.client = ChatOpenAI(
                api_key=self.api_key,
                base_url=QAConfig.OPENROUTER_BASE_URL,
                model=self.model_name,
                temperature=QAConfig.LLM_TEMPERATURE,
                max_tokens=QAConfig.LLM_MAX_TOKENS,
                timeout=30.0
            )
            logger.info(f"OpenRouter QA provider initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter QA provider: {e}")
            raise LLMError(f"OpenRouter初始化失敗: {e}")

    async def generate_answer(self, question: str, context: str) -> Dict[str, Any]:
        """使用OpenRouter生成答案"""
        if not self.client:
            raise LLMError("OpenRouter客戶端未初始化")

        try:
            # 根據上下文選擇提示模板
            if context == "無需參考文檔":
                # 簡單問題使用精簡提示
                prompt = QAConfig.SIMPLE_PROMPT
            else:
                # 財務問題使用完整提示
                prompt = QAConfig.SYSTEM_PROMPT.format(context=context)

            # 調用LLM
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": question}
            ]

            response = await self.client.ainvoke(messages)

            # 處理回應
            return {
                "answer": response.content,
                "model": self.model_name,
                "provider": "openrouter",
                # OpenRouter通常不返回詳細的token使用情況
                "tokens": {
                    "total": 0,
                    "prompt": 0,
                    "completion": 0
                },
                "cost": 0.0
            }

        except Exception as e:
            logger.error(f"OpenRouter QA generation failed: {e}")
            raise LLMError(f"OpenRouter生成答案失敗: {e}")

    async def generate_answer_with_history(self, question: str, context: str, chat_history: list) -> Dict[str, Any]:
        """使用OpenRouter生成答案 - 包含會話記憶"""
        if not self.client:
            raise LLMError("OpenRouter客戶端未初始化")

        try:
            # 根據上下文選擇提示模板
            if context == "無需參考文檔":
                # 簡單問題使用精簡提示
                system_prompt = QAConfig.SIMPLE_PROMPT
            else:
                # 財務問題使用完整提示
                system_prompt = QAConfig.SYSTEM_PROMPT.format(context=context)

            # 構建包含歷史記錄的對話
            messages = [{"role": "system", "content": system_prompt}]

            # 添加最近的對話歷史 (最多3輪)
            for q, a in chat_history:
                messages.append({"role": "user", "content": q})
                messages.append({"role": "assistant", "content": a})

            # 添加當前問題
            messages.append({"role": "user", "content": question})

            response = await self.client.ainvoke(messages)

            return {
                "answer": response.content,
                "model": self.model_name,
                "provider": "openrouter",
                "tokens": {
                    "total": 0,
                    "prompt": 0,
                    "completion": 0
                },
                "cost": 0.0
            }

        except Exception as e:
            logger.error(f"OpenRouter QA generation with history failed: {e}")
            raise LLMError(f"OpenRouter生成答案失敗: {e}")

    def get_model_info(self) -> Dict[str, str]:
        """獲取模型信息"""
        return {
            "provider": "openrouter",
            "model": self.model_name,
            "base_url": QAConfig.OPENROUTER_BASE_URL
        }