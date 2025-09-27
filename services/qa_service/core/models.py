from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class QAResponse:
    """QA回應數據模型"""
    answer: str
    sources: List[str] = field(default_factory=list)
    duration: float = 0.0
    cost: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

@dataclass
class QADocument:
    """QA文檔數據模型"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return self.metadata.get("source", "unknown")

    @property
    def doc_type(self) -> str:
        return self.metadata.get("type", "document")

@dataclass
class UserSession:
    """用戶會話數據模型"""
    user_id: str
    platform: str
    chat_history: List[tuple] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def add_interaction(self, question: str, answer: str):
        """添加問答互動"""
        self.chat_history.append((question, answer))
        self.last_activity = datetime.now()

    def get_recent_history(self, max_items: int = 5) -> List[tuple]:
        """獲取最近的對話歷史"""
        return self.chat_history[-max_items:] if self.chat_history else []

@dataclass
class QARequest:
    """QA請求數據模型"""
    user_id: str
    platform: str
    question: str
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "platform": self.platform,
            "question": self.question,
            "session_id": self.session_id
        }