"""
財務分析處理器
"""

import logging
import time
from .base_handler import BaseHandler, HandlerResponse

logger = logging.getLogger(__name__)

class FinanceHandler(BaseHandler):
    """財務分析處理器"""

    def __init__(self):
        super().__init__("財務分析")
        self.finance_service = None
        self._initialize_service()

    def _initialize_service(self):
        """初始化財務分析服務"""
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
            text="已進入財務分析模式，請直接提出您的財務問題。",
            quick_replies=self.create_exit_reply()
        )

    async def handle_message(self, user_id: str, message: str) -> HandlerResponse:
        """處理財務分析問題"""
        if not self.finance_service:
            return HandlerResponse(
                text="財務分析服務尚未準備好，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

        try:
            start_time = time.time()

            # 使用SimpleFinanceService處理問題
            finance_response = await self.finance_service.ask(message)

            processing_time = time.time() - start_time

            if finance_response["status"] == "success":
                response_text = finance_response["answer"]
            else:
                response_text = "抱歉，財務分析過程中發生錯誤。"

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

    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """財務分析不支持文件處理"""
        return HandlerResponse(
            text="財務分析模式不支持文件上傳，請直接輸入財務問題。",
            quick_replies=self.create_exit_reply()
        )