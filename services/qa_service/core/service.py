import time
import logging
from typing import Dict, Any, Optional

from .config import QAConfig
from .models import QARequest, QAResponse, UserSession
from .exceptions import QAServiceError, LLMError, VectorStoreError, ConfigError
from ..providers.base import LLMProvider, VectorStoreProvider
# 使用統一的 model_service 替代分散的 providers
from ..providers.vectorstore_provider import ChromaVectorStoreProvider

logger = logging.getLogger(__name__)

class SessionManager:
    """會話管理器 - 消除全局字典"""

    def __init__(self, max_sessions: int = 100):
        self._sessions: Dict[str, UserSession] = {}
        self._max_sessions = max_sessions

    def get_session(self, platform: str, user_id: str) -> UserSession:
        """獲取或創建用戶會話"""
        session_key = f"{platform}:{user_id}"

        if session_key not in self._sessions:
            # 如果會話數量過多，清理舊會話
            if len(self._sessions) >= self._max_sessions:
                self._cleanup_old_sessions()

            self._sessions[session_key] = UserSession(
                user_id=user_id,
                platform=platform
            )

        return self._sessions[session_key]

    def _cleanup_old_sessions(self):
        """清理最舊的會話"""
        if not self._sessions:
            return

        # 找到最舊的會話並移除
        oldest_key = min(self._sessions.keys(),
                        key=lambda k: self._sessions[k].last_activity)
        del self._sessions[oldest_key]
        logger.info(f"清理舊會話: {oldest_key}")

class QAService:
    """QA服務核心類 - 統一LLM提供商架構"""

    def __init__(self):
        self.model_service = None  # 統一 model_service
        self.vectorstore_provider: Optional[VectorStoreProvider] = None
        self.session_manager = SessionManager()
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化提供商"""
        try:
            # 使用統一的 model_service 替代自定義 LLM providers
            from services.model_service import create_model_service
            self.model_service = create_model_service()

            # 初始化向量存儲提供商
            self.vectorstore_provider = ChromaVectorStoreProvider()

            logger.info("QA Service providers initialized successfully with unified model_service")

        except Exception as e:
            logger.error(f"Failed to initialize QA Service providers: {e}")
            raise ConfigError(f"QA服務初始化失敗: {e}")

    async def _generate_answer_with_model_service(self, question: str, context: str, chat_history: list) -> Dict[str, Any]:
        """使用統一 model_service 生成答案 - 自動 fallback"""
        try:
            # 構建提示
            if context == "無需參考文檔":
                # 簡單問題使用精簡提示
                prompt = QAConfig.SIMPLE_PROMPT
            else:
                # 財務問題使用完整提示
                prompt = QAConfig.SYSTEM_PROMPT.format(context=context)

            # 構建標準的 messages 格式
            messages = [{"role": "system", "content": prompt}]

            # 添加對話歷史
            for q, a in chat_history:
                messages.append({"role": "user", "content": q})
                messages.append({"role": "assistant", "content": a})

            # 添加當前問題
            messages.append({"role": "user", "content": question})

            # 調用統一 model_service (自動 fallback)
            response = await self.model_service.qa_completion(messages)

            return {
                "answer": response.content,
                "model": response.model_name,
                "provider": response.provider.value,
                "tokens": {
                    "total": response.usage.total_tokens,
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens
                },
                "cost": response.usage.estimated_cost
            }

        except Exception as e:
            logger.error(f"Model service 生成答案失敗: {e}")
            raise LLMError(f"AI 生成答案失敗: {e}")

    async def ask(self, request: QARequest) -> QAResponse:
        """處理QA請求 - 優化的智能路由接口"""
        start_time = time.time()

        try:
            # 檢查服務可用性
            if not self.model_service:
                raise QAServiceError("Model service 未初始化")

            # 獲取用戶會話
            session = self.session_manager.get_session(request.platform, request.user_id)

            # 智能問題分類 - 考慮會話上下文
            question_type = self._classify_question_with_context(request.question, session)

            if question_type == "simple":
                # 快速路徑：簡單問題不需要搜索文檔
                context = "無需參考文檔"
                sources = []
                logger.info(f"使用快速路徑處理簡單問題: {request.question[:30]}...")
            else:
                # 標準路徑：一次性獲取文檔和來源 (避免重複搜索)
                documents = await self._search_documents_once(request.question)
                context = self._format_context(documents)
                sources = self._extract_sources_from_docs(documents)

            # 生成答案 - 使用統一 model_service (自動 fallback)
            llm_response = await self._generate_answer_with_model_service(
                request.question, context, session.get_recent_history(3)
            )

            # 更新會話歷史
            session.add_interaction(request.question, llm_response["answer"])

            # 計算處理時間
            duration = time.time() - start_time

            # 構建回應
            response = QAResponse(
                answer=self._format_answer(llm_response["answer"], sources),
                sources=sources,
                duration=duration,
                cost=llm_response.get("cost", 0.0),
                total_tokens=llm_response.get("tokens", {}).get("total", 0),
                prompt_tokens=llm_response.get("tokens", {}).get("prompt", 0),
                completion_tokens=llm_response.get("tokens", {}).get("completion", 0)
            )

            logger.info(f"QA請求處理完成 - 用戶: {request.user_id}, 類型: {question_type}, 耗時: {duration:.2f}s")
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"QA請求處理失敗: {e}")

            return QAResponse(
                answer=f"抱歉，處理您的問題時發生錯誤: {str(e)}",
                sources=[],
                duration=duration
            )

    async def _retrieve_context(self, question: str) -> str:
        """檢索相關上下文"""
        if not self.vectorstore_provider or not self.vectorstore_provider.is_available():
            return "暫無可用的知識庫內容。"

        try:
            documents = await self.vectorstore_provider.search_documents(
                question, k=QAConfig.TOP_K_SOURCES * 2
            )

            if not documents:
                return "未找到相關的知識庫內容。"

            # 組合文檔內容
            context_parts = []
            for i, doc in enumerate(documents[:QAConfig.TOP_K_SOURCES], 1):
                context_parts.append(f"文檔{i}: {doc.content[:500]}...")

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"檢索上下文失敗: {e}")
            return "檢索知識庫時發生錯誤。"

    async def _extract_sources(self, question: str) -> list:
        """提取來源信息"""
        if not self.vectorstore_provider or not self.vectorstore_provider.is_available():
            return []

        try:
            documents = await self.vectorstore_provider.search_documents(
                question, k=QAConfig.TOP_K_SOURCES
            )

            sources = []
            for doc in documents:
                source = doc.source
                if source and source not in sources:
                    sources.append(source)

            return sources[:QAConfig.TOP_K_SOURCES]

        except Exception as e:
            logger.error(f"提取來源失敗: {e}")
            return []

    def _format_answer(self, answer: str, sources: list) -> str:
        """格式化答案 - 親切顧問風格"""
        # 清理markdown符號
        formatted_answer = self._clean_markdown(answer)

        # 移除emoji過多的情況，保持專業但親切
        formatted_answer = self._clean_excessive_emojis(formatted_answer)

        # 添加簡潔的來源信息（用更親切的語氣）
        if sources:
            sources_text = "\n\n以上資訊主要參考：\n"
            for i, source in enumerate(sources[:2], 1):  # 只顯示前2個來源
                clean_source = self._clean_source_name(source)
                sources_text += f"• {clean_source}\n"
            formatted_answer += sources_text

        return formatted_answer

    def _clean_markdown(self, text: str) -> str:
        """清理markdown符號"""
        import re

        # 移除markdown符號
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **粗體**
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # *斜體*
        text = re.sub(r'#{1,6}\s*', '', text)         # # 標題
        text = re.sub(r'`(.*?)`', r'\1', text)        # `代碼`
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # [連結](url)

        # 清理多餘空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _clean_source_name(self, source: str) -> str:
        """簡化來源名稱"""
        # 移除路徑和擴展名
        import os
        clean_name = os.path.basename(source)
        if clean_name.endswith('.pdf'):
            clean_name = clean_name[:-4]

        # 截斷過長的文件名
        if len(clean_name) > 30:
            clean_name = clean_name[:27] + "..."

        return clean_name

    def _clean_excessive_emojis(self, text: str) -> str:
        """清理過多的emoji，保持專業但親切的風格"""
        import re

        # 移除連續的emoji（保留單個emoji）
        text = re.sub(r'[🎯📋💡📚💰📊⚠️🔍✅❌]{3,}', '', text)

        # 移除行首的emoji標記符號（如 🎯、📋等），但保留內容中的適當emoji
        text = re.sub(r'^[🎯📋💡📚💰📊⚠️🔍✅❌]\s*', '', text, flags=re.MULTILINE)

        # 保留一些有用的emoji，但限制數量
        useful_emojis = ['💰', '📊', '⚠️', '✅', '❌']
        for emoji in useful_emojis:
            # 限制每種emoji最多出現2次
            parts = text.split(emoji)
            if len(parts) > 3:  # 超過2次出現
                text = emoji.join(parts[:3]) + ''.join(parts[3:])

        return text

    def _classify_question(self, question: str) -> str:
        """快速問題分類 - 判斷是否需要搜索文檔"""
        question_lower = question.lower().strip()

        # 簡單問題模式 - 不需要搜索財務文檔
        simple_patterns = [
            # 自我介紹類
            "你是誰", "你是什麼", "介紹一下", "自我介紹",
            # 打招呼類
            "你好", "哈囉", "嗨", "hi", "hello",
            # 功能詢問類
            "你能做什麼", "你會什麼", "有什麼功能", "怎麼使用",
            # 測試類
            "測試", "test", "檢查", "確認"
        ]

        # 檢查是否為簡單問題
        for pattern in simple_patterns:
            if pattern in question_lower:
                return "simple"

        # 短問題且不包含財務關鍵字，可能是簡單問題
        if len(question.strip()) <= 10:
            finance_keywords = ["稅", "財務", "會計", "發票", "扣除", "申報", "營業", "所得"]
            if not any(keyword in question for keyword in finance_keywords):
                return "simple"

        return "finance"  # 需要搜索財務文檔

    def _classify_question_with_context(self, question: str, session) -> str:
        """帶會話上下文的問題分類"""
        question_lower = question.lower().strip()

        # 獲取最近的對話歷史
        recent_history = session.get_recent_history(2)

        # 跟進問題模式 - 基於會話上下文判斷
        followup_patterns = [
            "那", "這樣", "所以", "如果", "那麼", "還有", "另外",
            "詳細", "具體", "怎麼", "如何", "步驟", "流程"
        ]

        # 如果有對話歷史且當前問題像是跟進問題
        if recent_history and any(pattern in question_lower for pattern in followup_patterns):
            # 檢查上一個問答是否涉及財務
            last_question, last_answer = recent_history[-1]
            if any(keyword in last_question.lower() or keyword in last_answer.lower()
                   for keyword in ["稅", "財務", "會計", "發票", "扣除", "申報"]):
                return "finance"  # 財務相關的跟進問題

        # 否則使用標準分類
        return self._classify_question(question)

    async def _search_documents_once(self, question: str) -> list:
        """一次性文檔搜索 - 避免重複搜索"""
        if not self.vectorstore_provider or not self.vectorstore_provider.is_available():
            return []

        try:
            documents = await self.vectorstore_provider.search_documents(
                question, k=QAConfig.TOP_K_SOURCES * 2
            )
            return documents or []
        except Exception as e:
            logger.error(f"文檔搜索失敗: {e}")
            return []

    def _format_context(self, documents: list) -> str:
        """從文檔列表格式化上下文"""
        if not documents:
            return "未找到相關的知識庫內容。"

        context_parts = []
        for i, doc in enumerate(documents[:QAConfig.TOP_K_SOURCES], 1):
            context_parts.append(f"文檔{i}: {doc.content[:500]}...")

        return "\n\n".join(context_parts)

    def _extract_sources_from_docs(self, documents: list) -> list:
        """從已搜索的文檔中提取來源"""
        sources = []
        for doc in documents[:QAConfig.TOP_K_SOURCES]:
            source = doc.source
            if source and source not in sources:
                sources.append(source)
        return sources

    def get_service_status(self) -> Dict[str, Any]:
        """獲取服務狀態"""
        return {
            "model_service": "unified_model_service" if self.model_service else None,
            "vectorstore_available": self.vectorstore_provider.is_available() if self.vectorstore_provider else False,
            "vectorstore_stats": self.vectorstore_provider.get_stats() if self.vectorstore_provider else {},
            "active_sessions": len(self.session_manager._sessions),
            "config": QAConfig.get_llm_config()
        }