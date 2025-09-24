"""
模型服務工具函數
"""

import base64
import logging
from typing import Dict, Any, List, Optional

from .config.models import get_model_config, get_vision_models, get_free_models

logger = logging.getLogger(__name__)


def encode_image_to_base64(image_path: str) -> str:
    """將圖片文件編碼為 base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        raise


def validate_messages(messages: List[Dict[str, str]]) -> bool:
    """驗證消息格式"""
    if not messages:
        return False

    for msg in messages:
        if not isinstance(msg, dict):
            return False
        if "role" not in msg or "content" not in msg:
            return False
        if msg["role"] not in ["system", "user", "assistant"]:
            return False

    return True


def format_openai_to_openrouter(openai_response: Dict[str, Any]) -> Dict[str, Any]:
    """將 OpenAI 格式的回應轉換為標準格式"""
    if "choices" not in openai_response:
        return openai_response

    # OpenRouter 回應格式與 OpenAI 相容，無需轉換
    return openai_response


def extract_text_content(response: Dict[str, Any]) -> str:
    """從模型回應中提取文字內容"""
    try:
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
        return ""
    except Exception as e:
        logger.error(f"Failed to extract content from response: {e}")
        return ""


def get_usage_info(response: Dict[str, Any]) -> Dict[str, int]:
    """從回應中提取使用量資訊"""
    try:
        return response.get("usage", {})
    except Exception:
        return {}


def is_vision_model(model_name: str) -> bool:
    """檢查模型是否支援視覺功能"""
    vision_models = get_vision_models()
    for config in vision_models.values():
        if config.name == model_name:
            return True
    return False


def is_free_model(model_name: str) -> bool:
    """檢查是否為免費模型"""
    return ":free" in model_name


def get_recommended_model(task_type: str) -> Optional[str]:
    """根據任務類型獲取推薦模型"""
    recommendations = {
        "qa": "x-ai/grok-4-fast:free",
        "finance": "deepseek/deepseek-r1-0528:free",
        "ocr": "google/gemini-2.0-flash-exp:free",
        "vision": "google/gemini-2.0-flash-exp:free",
        "chat": "x-ai/grok-4-fast:free",
        "analysis": "deepseek/deepseek-r1-0528:free"
    }
    return recommendations.get(task_type.lower())


def calculate_estimated_cost(usage: Dict[str, int], model_name: str) -> float:
    """計算預估成本（免費模型返回 0）"""
    if is_free_model(model_name):
        return 0.0

    # 這裡可以根據不同模型的定價來計算
    # 暫時返回 0，實際使用時需要查詢 OpenRouter 的定價
    return 0.0


def create_system_message(content: str) -> Dict[str, str]:
    """創建系統消息"""
    return {"role": "system", "content": content}


def create_user_message(content: str) -> Dict[str, str]:
    """創建用戶消息"""
    return {"role": "user", "content": content}


def create_assistant_message(content: str) -> Dict[str, str]:
    """創建助手消息"""
    return {"role": "assistant", "content": content}