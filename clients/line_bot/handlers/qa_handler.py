"""
QA問答處理器
"""

import logging
from .base_handler import BaseHandler, HandlerResponse

logger = logging.getLogger(__name__)

class QAHandler(BaseHandler):
    """QA問答處理器"""

    def __init__(self):
        super().__init__("QA問答")
        self.qa_service = None
        self._initialize_service()

    def _initialize_service(self):
        """初始化QA服務"""
        try:
            # 直接導入存在的模組
            from services.qa_service.qa_client_v2 import process_qa_query
            self.process_qa_query = process_qa_query
            logger.info("QA服務初始化成功")
        except ImportError as e:
            logger.error(f"QA服務初始化失敗: {e}")
            self.process_qa_query = None

    async def enter_mode(self, user_id: str) -> HandlerResponse:
        """進入QA模式"""
        return HandlerResponse(
            text="已進入QA問答模式，請直接提出您的問題。",
            quick_replies=self.create_exit_reply()
        )

    async def handle_message(self, user_id: str, message: str) -> HandlerResponse:
        """處理QA問題"""
        if not self.process_qa_query:
            return HandlerResponse(
                text="抱歉，QA服務暫時不可用，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

        try:
            qa_response = await self.process_qa_query(
                platform="LINE",
                user_id=user_id,
                query=message
            )
            response_text = qa_response.get("response", "抱歉，我無法處理您的請求。")

            return HandlerResponse(
                text=response_text,
                quick_replies=self.create_exit_reply()
            )

        except Exception as e:
            logger.error(f"QA請求失敗: {e}")
            return HandlerResponse(
                text="抱歉，服務暫時無法回應。",
                quick_replies=self.create_exit_reply()
            )

    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """QA不支持文件處理"""
        return HandlerResponse(
            text="QA問答模式不支持文件上傳，請直接輸入文字問題。",
            quick_replies=self.create_exit_reply()
        )