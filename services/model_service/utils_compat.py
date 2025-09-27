"""
向後兼容的工具函數
為平滑遷移提供舊接口的實現
"""

import base64
import logging
from typing import Dict, Any, List, Optional

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


def extract_text_content(response) -> str:
    """
    從模型回應中提取文字內容 - 極簡版本

    兼容新舊回應格式：
    - 新格式: ModelResponse 對象
    - 舊格式: Dict 格式
    """
    # 新格式：ModelResponse 對象
    if hasattr(response, 'content') and hasattr(response, 'provider'):
        content = getattr(response, 'content', '')
        return str(content) if content is not None else ""

    # 字符串格式
    if isinstance(response, str):
        return response

    # 舊格式：Dict
    if isinstance(response, dict):
        # OpenAI/OpenRouter 格式
        try:
            choices = response.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if content:
                    return content
        except:
            pass

        # 直接 content 字段
        try:
            content = response.get("content", "")
            if content:
                return content
        except:
            pass

    return ""


def get_usage_info(response) -> Dict[str, int]:
    """從回應中提取使用量資訊"""
    try:
        # 新格式：ModelResponse 對象
        if hasattr(response, 'usage'):
            return response.usage

        # 舊格式：Dict 格式
        if isinstance(response, dict):
            return response.get("usage", {})

        return {}
    except Exception:
        return {}


def create_system_message(content: str) -> Dict[str, str]:
    """創建系統消息"""
    return {"role": "system", "content": content}


def create_user_message(content: str) -> Dict[str, str]:
    """創建用戶消息"""
    return {"role": "user", "content": content}


def create_assistant_message(content: str) -> Dict[str, str]:
    """創建助手消息"""
    return {"role": "assistant", "content": content}


def is_free_model(model_name: str) -> bool:
    """檢查是否為免費模型"""
    return ":free" in model_name.lower() or "free" in model_name.lower()


def get_recommended_model(task_type: str) -> Optional[str]:
    """根據任務類型獲取推薦模型"""
    recommendations = {
        "qa": "x-ai/grok-4-fast:free",
        "finance": "x-ai/grok-4-fast:free",
        "ocr": "gemini-2.5-flash",
        "vision": "gemini-2.5-flash",
        "chat": "x-ai/grok-4-fast:free",
        "analysis": "x-ai/grok-4-fast:free"
    }
    return recommendations.get(task_type.lower())


def calculate_estimated_cost(usage: Dict[str, int], model_name: str) -> float:
    """計算預估成本（免費模型返回 0）"""
    if is_free_model(model_name):
        return 0.0

    # 簡化的成本計算
    total_tokens = usage.get("total_tokens", 0)

    if "gpt-4" in model_name.lower():
        return total_tokens * 0.00003  # 估算
    elif "gpt-3.5" in model_name.lower():
        return total_tokens * 0.000002  # 估算
    else:
        return 0.0