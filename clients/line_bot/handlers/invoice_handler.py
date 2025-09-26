"""
照片記帳處理器
"""

import logging
from typing import Dict, Any
from .base_handler import BaseHandler, HandlerResponse

logger = logging.getLogger(__name__)

class InvoiceHandler(BaseHandler):
    """照片記帳處理器"""

    def __init__(self):
        super().__init__("照片記帳")
        self.invoice_service = None
        self._initialize_service()

    def _initialize_service(self):
        """初始化發票處理服務"""
        try:
            from services.invoice_service.main import InvoiceProcessor
            self.invoice_service = InvoiceProcessor()
            logger.info("發票處理服務初始化成功")
        except Exception as e:
            logger.error(f"發票處理服務初始化失敗: {e}")
            self.invoice_service = None

    async def enter_mode(self, user_id: str) -> HandlerResponse:
        """進入照片記帳模式"""
        return HandlerResponse(
            text="已進入照片記帳模式，請傳送您的發票圖片或PDF。",
            quick_replies=self.create_exit_reply()
        )

    async def handle_message(self, user_id: str, message: str) -> HandlerResponse:
        """處理文字訊息（在照片記帳模式中主要是提醒）"""
        return HandlerResponse(
            text="請傳送發票檔案，或輸入「返回主選單」以離開。",
            quick_replies=self.create_exit_reply()
        )

    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """處理發票文件"""
        if not self.invoice_service:
            return HandlerResponse(
                text="發票處理服務尚未準備好，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

        try:
            # 處理發票
            invoice_data, usage = await self.invoice_service.process_invoice_from_data(
                file_data, media_type
            )

            # 格式化確認卡片文字
            confirm_text = self._format_invoice_confirm_text(invoice_data, usage)

            return HandlerResponse(
                text="confirm_template",  # 特殊標記
                template_data={
                    "text": confirm_text,
                    "confirm_label": "確認儲存",
                    "confirm_data": f"action=save_invoice&user_id={user_id}",
                    "cancel_label": "編輯發票",
                    "cancel_data": f"action=edit_invoice&user_id={user_id}",
                    "alt_text": "發票辨識結果確認"
                },
                needs_loading=True
            )

        except Exception as e:
            logger.error(f"發票處理失敗: {e}")
            return HandlerResponse(
                text="抱歉，辨識發票時發生錯誤，請重新上傳或檢查檔案格式。",
                quick_replies=self.create_exit_reply()
            )

    def _format_invoice_confirm_text(self, invoice_data: Dict[str, Any], usage: Dict[str, Any]) -> str:
        """格式化發票確認卡片文字"""
        # 計算成本
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)

        input_cost = (prompt_tokens / 1_000_000) * 5.0
        output_cost = (completion_tokens / 1_000_000) * 15.0
        total_cost_usd = input_cost + output_cost
        total_cost_twd = total_cost_usd * 32
        cost_text = f"\n辨識成本約 NT$ {total_cost_twd:.4f}"

        return (
            f"發票辨識結果：\n"
            f"類型: {invoice_data.get('transaction_type', 'N/A')}\n"
            f"賣方統編: {invoice_data.get('seller_id', '無法辨識')}\n"
            f"發票號碼: {invoice_data.get('invoice_number', '無法辨識')}\n"
            f"日期: {invoice_data.get('invoice_date', '無法辨識')}\n"
            f"金額: {invoice_data.get('account', '無法辨識')}\n"
            f"格式: {invoice_data.get('invoice_type', '無法辨識')}\n"
            f"品項: {invoice_data.get('invoice_description', '無品名資訊')[:60]}\n"
            f"類別: {invoice_data.get('category', '無法辨識')}"
            f"{cost_text}"
        )