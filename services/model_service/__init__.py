"""
模型服務模組
提供統一的 AI 模型調用接口，支援多種提供商

遷移說明：
- 舊接口 (manager.py) 仍然可用，但已標記為過時
- 新接口 (service.py) 提供更乾淨的架構
- 建議逐步遷移到新接口
"""

import logging

logger = logging.getLogger(__name__)

# 使用新的乾淨架構
from .service import qa_completion, finance_completion, ocr_completion
from .service import ModelService, create_model_service
from .core.config import ServiceType

logger.info("Using new clean model service architecture")
NEW_ARCHITECTURE = True

__all__ = [
    # 向後兼容的函數接口
    'qa_completion',
    'finance_completion',
    'ocr_completion',

    # 新的服務接口
    'ModelService',
    'create_model_service',

    # 配置
    'ServiceType',

    # 架構標記
    'NEW_ARCHITECTURE'
]

# 導入 utils 函數
from .utils_compat import (
    create_system_message, create_user_message, create_assistant_message,
    extract_text_content, get_usage_info, encode_image_to_base64,
    validate_messages, is_free_model, get_recommended_model,
    calculate_estimated_cost
)

# 添加 utils 函數到導出列表
__all__.extend([
    'create_system_message', 'create_user_message', 'create_assistant_message',
    'extract_text_content', 'get_usage_info', 'encode_image_to_base64',
    'validate_messages', 'is_free_model', 'get_recommended_model',
    'calculate_estimated_cost'
])