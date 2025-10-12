"""
乾淨的財務分析處理器 - 正確的架構
簡單過濾 + 現有財務服務 + 改進的AI分析
"""

import logging
import time
from .base_handler import BaseHandler, HandlerResponse

logger = logging.getLogger(__name__)

class FinanceHandlerClean(BaseHandler):
    """乾淨的財務處理器 - 使用正確的服務分離"""

    def __init__(self):
        super().__init__("財務分析")
        self.finance_service = None
        self._init_service()

    def _init_service(self):
        """初始化現有的財務分析服務"""
        try:
            from services.finance_analysis_service.simple_main import SimpleFinanceService
            self.finance_service = SimpleFinanceService()
            logger.info("財務分析服務初始化成功")
        except Exception as e:
            logger.error(f"財務分析服務初始化失敗: {e}")
            self.finance_service = None

    async def enter_mode(self, user_id: str) -> HandlerResponse:
        """進入財務分析模式"""
        return HandlerResponse(
            text="💰 專業財務分析師就緒\n\n請提出您的財務問題，我會為您提供深度專業分析。",
            quick_replies=self.create_exit_reply()
        )

    async def handle_message(self, user_id: str, message: str) -> HandlerResponse:
        """處理財務分析問題 - Linus原則：簡單直接"""

        # 檢查服務狀態
        if not self.finance_service:
            return HandlerResponse(
                text="財務分析服務尚未準備好，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

        # 簡單過濾 - 早期返回原則
        filter_result = self._simple_filter(message)
        if filter_result:
            return filter_result

        # 使用現有的財務分析服務
        try:
            start_time = time.time()

            logger.info(f"開始處理財務問題: {message}")
            finance_response = await self.finance_service.ask(message)
            logger.info(f"財務服務回應: {finance_response}")

            processing_time = time.time() - start_time

            if finance_response["status"] == "success":
                response_text = finance_response["answer"]
                logger.info(f"財務分析成功，回應長度: {len(response_text)}")
            else:
                response_text = f"抱歉，財務分析過程中發生錯誤: {finance_response.get('error', '未知錯誤')}"
                logger.error(f"財務分析失敗: {finance_response}")

            return HandlerResponse(
                text=response_text,
                quick_replies=self.create_exit_reply(),
                needs_loading=True,
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"財務分析處理失敗: {e}")
            return HandlerResponse(
                text=f"財務分析處理時發生錯誤：{str(e)}",
                quick_replies=self.create_exit_reply()
            )

    def _simple_filter(self, message: str) -> HandlerResponse:
        """簡單過濾器 - Linus原則：早期返回"""
        clean_msg = message.strip().lower()

        # 空訊息
        if len(clean_msg) < 2:
            return HandlerResponse(
                text="請輸入財務問題。",
                quick_replies=self.create_exit_reply()
            )

        # 問候語
        greetings = {"hi", "hello", "你好", "嗨", "早安", "午安", "晚安"}
        if clean_msg in greetings:
            return HandlerResponse(
                text=self._get_greeting_response(),
                quick_replies=self.create_exit_reply()
            )

        # 非財務問題 - 關鍵詞檢查
        finance_words = ["收入", "支出", "營收", "費用", "利潤", "財務", "錢", "分析", "趨勢", "成本", "資金", "獲利"]
        if not any(word in message for word in finance_words):
            return HandlerResponse(
                text="請提出財務相關問題。例如：收入狀況、支出分析、利潤趨勢等。",
                quick_replies=self.create_exit_reply()
            )

        return None  # 通過過濾

    def _get_greeting_response(self) -> str:
        """問候回應"""
        return """您好！我是專業財務分析師 💰

我能為您提供：
• 📊 收支分析：整體財務狀況和健康度
• 📈 趨勢分析：營收成長和變化趨勢
• 📋 結構分析：收入支出分類明細
• 📐 比率分析：利潤率、費用率等指標
• 💡 專業建議：具體可行的改善策略

請直接提出您的財務問題！"""

    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """不支持文件"""
        return HandlerResponse(
            text="財務分析模式僅接受文字問題，不支援文件上傳。",
            quick_replies=self.create_exit_reply()
        )