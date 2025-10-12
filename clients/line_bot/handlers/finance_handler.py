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

        # 輸入分類和早期驗證 - 避免無效請求觸發昂貴的數據載入
        validation_result = self._validate_and_classify_input(message)

        if validation_result["type"] == "invalid":
            return HandlerResponse(
                text=validation_result["response"],
                quick_replies=self.create_exit_reply()
            )

        if validation_result["type"] == "help":
            return HandlerResponse(
                text=self._get_help_message(),
                quick_replies=self.create_exit_reply()
            )

        try:
            start_time = time.time()

            # 使用SimpleFinanceService處理問題
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

    def _validate_and_classify_input(self, message: str) -> dict:
        """
        輸入驗證和分類 - Linus式設計：早期驗證，避免無效計算

        Returns:
            dict: {"type": "valid|invalid|help", "response": "回應文字"}
        """
        message_clean = message.strip()
        message_lower = message_clean.lower()

        # 1. 空輸入檢查
        if not message_clean or len(message_clean) < 2:
            return {
                "type": "invalid",
                "response": "請輸入有效的財務問題。"
            }

        # 2. 問候語和幫助請求
        greetings = {"hi", "hello", "你好", "嗨", "哈囉", "早安", "午安", "晚安", "安安"}
        help_keywords = {"help", "幫助", "幫忙", "怎麼用", "如何使用", "?", "？"}

        if message_lower in greetings or any(word in message_lower for word in help_keywords):
            return {"type": "help", "response": ""}

        # 3. 財務關鍵詞檢查 - 核心業務邏輯
        finance_keywords = {
            # 基礎財務概念
            "收入", "支出", "營收", "費用", "成本", "利潤", "獲利", "盈利", "虧損",
            "現金", "資金", "金額", "錢", "財務", "會計", "帳", "賺", "花",
            # 分析相關
            "分析", "統計", "報表", "數據", "趨勢", "比較", "佔比", "比率",
            # 時間相關
            "月", "季", "年", "本期", "上期", "今年", "去年", "最近",
            # 具體項目
            "發票", "收據", "稅", "折舊", "投資", "貸款", "股東", "資本"
        }

        # 檢查是否包含財務關鍵詞
        if not any(keyword in message for keyword in finance_keywords):
            return {
                "type": "invalid",
                "response": "請提出財務相關的問題。我可以幫您分析收入、支出、利潤等財務數據。"
            }

        # 4. 長度檢查 - 太短的問題可能不夠具體
        if len(message_clean) < 4:
            return {
                "type": "invalid",
                "response": "請提出更具體的財務問題，例如：「公司本月收支狀況如何？」"
            }

        return {"type": "valid", "response": ""}

    def _get_help_message(self) -> str:
        """獲取幫助訊息"""
        return """您好！我是財務分析助手 💰

我可以幫您分析：
• 📊 收支狀況：「公司本月收入和支出如何？」
• 💹 利潤分析：「最近的獲利情況怎樣？」
• 📈 趨勢分析：「營收趨勢如何？」
• 🏢 成本結構：「主要支出項目有哪些？」

請直接提出您的財務問題！"""

    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """財務分析不支持文件處理"""
        return HandlerResponse(
            text="財務分析模式不支持文件上傳，請直接輸入財務問題。",
            quick_replies=self.create_exit_reply()
        )