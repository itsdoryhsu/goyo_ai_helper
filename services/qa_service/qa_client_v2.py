"""
QA Client v2 - 統一LLM提供商架構
取代原本的LangChain重型實現，使用乾淨的依賴注入設計
"""

import os
import sys
import logging
import asyncio
from typing import Dict, Any, Optional

# 將專案根目錄添加到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# 載入環境變數 - 強制覆蓋系統環境變數
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'), override=True)

# 設置日誌
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "qa_client_v2.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 導入新的QA服務
from .core.service import QAService
from .core.models import QARequest, QAResponse
from .core.exceptions import QAServiceError

# 全局服務實例
_qa_service: Optional[QAService] = None

def get_qa_service() -> QAService:
    """獲取QA服務實例 - 單例模式"""
    global _qa_service
    if _qa_service is None:
        _qa_service = QAService()
    return _qa_service

async def process_qa_query(
    platform: str,
    user_id: str,
    query: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_k_sources: Optional[int] = None,
    similarity_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    處理QA查詢 - 兼容舊接口的統一入口

    Args:
        platform: 平台名稱 (e.g., "LINE")
        user_id: 用戶ID
        query: 用戶問題
        model: 模型名稱 (暫時忽略，使用配置中的模型)
        temperature: 溫度參數 (暫時忽略，使用配置中的溫度)
        top_k_sources: 來源數量 (暫時忽略，使用配置中的值)
        similarity_threshold: 相似度閾值 (暫時忽略，使用配置中的值)

    Returns:
        包含回應和統計信息的字典
    """
    try:
        # 創建請求對象
        request = QARequest(
            user_id=user_id,
            platform=platform,
            question=query
        )

        # 獲取QA服務並處理請求
        qa_service = get_qa_service()
        response = await qa_service.ask(request)

        # 格式化回應以兼容舊接口
        return {
            "response": response.answer,
            "sources": response.sources,
            "total_tokens": response.total_tokens,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_cost": response.cost,
            "duration": response.duration
        }

    except Exception as e:
        logger.error(f"處理QA查詢失敗: {e}")
        return {
            "response": f"處理您的問題時出錯: {str(e)}",
            "sources": [],
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": 0.0,
            "duration": 0.0
        }

def startup_qa_client():
    """應用啟動時的事件處理"""
    logger.info("正在啟動QA客戶端v2 (統一LLM架構)...")
    try:
        qa_service = get_qa_service()
        status = qa_service.get_service_status()
        logger.info(f"QA客戶端v2初始化成功: {status}")
    except Exception as e:
        logger.error(f"QA客戶端v2初始化失敗: {e}")

def get_service_status() -> Dict[str, Any]:
    """獲取服務狀態 - 新增接口"""
    try:
        qa_service = get_qa_service()
        return qa_service.get_service_status()
    except Exception as e:
        logger.error(f"獲取服務狀態失敗: {e}")
        return {"error": str(e)}

# 在模塊載入時執行初始化
startup_qa_client()

# 向後兼容性支援
# 以下函數保持與舊接口的兼容性，但內部使用新架構

def init_qa_chain():
    """向後兼容：初始化問答鏈"""
    try:
        qa_service = get_qa_service()
        return qa_service.vectorstore_provider.is_available() if qa_service.vectorstore_provider else False
    except Exception as e:
        logger.error(f"向後兼容init_qa_chain失敗: {e}")
        return False

def get_user_session(platform, user_id):
    """向後兼容：獲取用戶會話"""
    try:
        qa_service = get_qa_service()
        session = qa_service.session_manager.get_session(platform, user_id)
        # 轉換為舊格式
        return {
            "chat_history": [(q, a) for q, a in session.chat_history],
            "memory": None  # 新架構不使用LangChain的memory
        }
    except Exception as e:
        logger.error(f"向後兼容get_user_session失敗: {e}")
        return {"chat_history": [], "memory": None}

# 保持其他向後兼容函數
def get_user_settings(platform, user_id):
    """向後兼容：獲取用戶設置"""
    from .core.config import QAConfig
    return {
        "model": QAConfig.LLM_MODEL,
        "temperature": QAConfig.LLM_TEMPERATURE,
        "top_k_sources": QAConfig.TOP_K_SOURCES,
        "similarity_threshold": QAConfig.SIMILARITY_THRESHOLD
    }

def save_user_settings(platform, user_id, settings):
    """向後兼容：保存用戶設置 (新架構中設置由配置文件管理)"""
    logger.info(f"用戶設置保存請求已忽略 (新架構使用配置文件): {settings}")
    return get_user_settings(platform, user_id)