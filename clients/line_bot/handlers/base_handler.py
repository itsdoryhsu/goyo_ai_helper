"""
基礎處理器 - Linus式簡潔設計
消除特殊情況，統一處理接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class HandlerResponse:
    """統一的處理器回應格式"""
    text: str
    quick_replies: Optional[List[Dict[str, str]]] = None
    needs_loading: bool = False
    processing_time: Optional[float] = None
    template_data: Optional[Dict[str, Any]] = None

class BaseHandler(ABC):
    """基礎處理器 - 所有服務處理器的父類"""

    def __init__(self, service_name: str):
        self.service_name = service_name

    @abstractmethod
    async def enter_mode(self, user_id: str) -> HandlerResponse:
        """進入服務模式時的歡迎訊息"""
        pass

    @abstractmethod
    async def handle_message(self, user_id: str, message: str) -> HandlerResponse:
        """處理用戶訊息"""
        pass

    @abstractmethod
    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """處理文件上傳（如果支持）"""
        pass

    def create_quick_reply(self, label: str, text: str) -> Dict[str, str]:
        """創建快速回復按鈕"""
        return {"label": label, "text": text}

    def create_exit_reply(self) -> List[Dict[str, str]]:
        """創建退出按鈕"""
        return [self.create_quick_reply("離開", "返回主選單")]