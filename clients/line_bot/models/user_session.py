"""
用戶會話管理 - Linus式簡潔狀態管理
取代全局字典的混亂狀態
"""

from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import time

class SessionState(Enum):
    """會話狀態枚舉"""
    IDLE = "idle"
    QA_MODE = "qa_mode"
    INVOICE_MODE = "invoice_mode"
    FINANCE_MODE = "finance_mode"
    CALENDAR_MODE = "calendar_mode"

@dataclass
class UserSession:
    """用戶會話狀態"""
    user_id: str
    state: SessionState = SessionState.IDLE
    current_handler: Optional[str] = None
    temp_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def update_activity(self):
        """更新最後活動時間"""
        self.last_activity = time.time()

    def enter_service(self, service_name: str, state: SessionState):
        """進入服務模式"""
        self.current_handler = service_name
        self.state = state
        self.update_activity()

    def exit_service(self):
        """退出服務模式"""
        self.current_handler = None
        self.state = SessionState.IDLE
        self.temp_data.clear()
        self.update_activity()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """檢查會話是否過期"""
        return (time.time() - self.last_activity) > (timeout_minutes * 60)

class SessionManager:
    """會話管理器 - 取代全局字典"""

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}

    def get_session(self, user_id: str) -> UserSession:
        """獲取用戶會話，不存在則創建"""
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession(user_id=user_id)

        session = self._sessions[user_id]
        session.update_activity()
        return session

    def clear_session(self, user_id: str):
        """清除用戶會話"""
        if user_id in self._sessions:
            del self._sessions[user_id]

    def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """清理過期會話"""
        expired_users = [
            user_id for user_id, session in self._sessions.items()
            if session.is_expired(timeout_minutes)
        ]

        for user_id in expired_users:
            del self._sessions[user_id]

        return len(expired_users)