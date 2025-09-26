"""
服務註冊器 - 消除硬編碼服務選擇
"""

from typing import Dict
from ..handlers.base_handler import BaseHandler
from ..handlers.qa_handler import QAHandler
from ..handlers.finance_handler import FinanceHandler
from ..handlers.invoice_handler import InvoiceHandler
from ..handlers.calendar_handler import CalendarHandler
from ..models.user_session import SessionState

class ServiceRegistry:
    """服務註冊器 - 統一管理4個核心服務"""

    def __init__(self):
        # 服務名稱映射 - 消除硬編碼字符串比較
        self._handlers: Dict[str, BaseHandler] = {
            "QA問答": QAHandler(),
            "照片記帳": InvoiceHandler(),
            "財務分析": FinanceHandler(),
            "記事提醒": CalendarHandler()
        }

        # 服務狀態映射
        self._service_states: Dict[str, SessionState] = {
            "QA問答": SessionState.QA_MODE,
            "照片記帳": SessionState.INVOICE_MODE,
            "財務分析": SessionState.FINANCE_MODE,
            "記事提醒": SessionState.CALENDAR_MODE
        }

    def get_handler(self, service_name: str) -> BaseHandler:
        """獲取服務處理器"""
        return self._handlers.get(service_name)

    def get_service_state(self, service_name: str) -> SessionState:
        """獲取服務對應的狀態"""
        return self._service_states.get(service_name, SessionState.IDLE)

    def is_valid_service(self, service_name: str) -> bool:
        """檢查是否為有效服務"""
        return service_name in self._handlers

    def list_services(self) -> list[str]:
        """列出所有可用服務"""
        return list(self._handlers.keys())