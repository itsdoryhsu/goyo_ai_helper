"""
乾淨的模型服務配置管理
消除複雜的動態配置，使用簡單明確的配置
"""

import os
from typing import Dict, Any, Optional
from enum import Enum
from dotenv import load_dotenv

# 專案根目錄
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# 載入環境變數 - 強制覆蓋系統環境變數
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'), override=True)

# 導入 ServiceType 從 models.py
from .models import ServiceType


class ProviderType(Enum):
    """提供商類型"""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    GEMINI = "gemini"


class ModelConfig:
    """模型配置類 - 不可變配置對象"""

    def __init__(
        self,
        provider: ProviderType,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 30.0
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout
        }


class ServiceConfig:
    """服務配置管理器 - 靜態配置，避免複雜性"""

    # 服務默認配置
    _DEFAULT_CONFIGS = {
        ServiceType.QA: ModelConfig(
            provider=ProviderType.OPENROUTER,
            model="openai/gpt-oss-20b:free",
            temperature=0.4,
            max_tokens=4096
        ),
        ServiceType.FINANCE: ModelConfig(
            provider=ProviderType.OPENROUTER,
            model="deepseek/deepseek-r1:free",
            temperature=0.3,
            max_tokens=8192
        ),
        ServiceType.OCR: ModelConfig(
            provider=ProviderType.GEMINI,
            model="gemini-2.5-flash",
            temperature=0.1,
            max_tokens=2048
        )
    }

    # 備援配置鏈 - 按優先級排序，使用環境變數配置
    @classmethod
    def _get_fallback_configs(cls):
        """動態生成備援配置，使用環境變數中的模型"""
        # 從環境變數讀取備用模型
        backup_chat_model = os.getenv("BACKUP_CHAT_MODEL", "gpt-4")
        backup_analysis_model = os.getenv("BACKUP_ANALYSIS_MODEL", "gpt-4")
        backup_vision_model = os.getenv("BACKUP_VISION_MODEL", "gpt-4o")

        # 如果配置了MODEL_NAME，優先使用它作為OpenAI備用模型
        openai_model = os.getenv("MODEL_NAME", backup_chat_model)

        return {
            ServiceType.QA: [
                ModelConfig(ProviderType.OPENROUTER, "x-ai/grok-4-fast:free", 0.4),
                ModelConfig(ProviderType.OPENAI, openai_model, 0.4),
                ModelConfig(ProviderType.GEMINI, "gemini-2.0-flash-exp", 0.4),
            ],
            ServiceType.FINANCE: [
                ModelConfig(ProviderType.OPENROUTER, "x-ai/grok-4-fast:free", 0.3),
                ModelConfig(ProviderType.OPENAI, openai_model, 0.3),
                ModelConfig(ProviderType.GEMINI, "gemini-2.0-flash-exp", 0.3),
            ],
            ServiceType.OCR: [
                ModelConfig(ProviderType.GEMINI, "gemini-2.5-flash", 0.1),
                ModelConfig(ProviderType.OPENAI, backup_vision_model, 0.1),
                ModelConfig(ProviderType.OPENROUTER, "google/gemini-2.0-flash-exp:free", 0.1),
            ]
        }

    _FALLBACK_CONFIGS = None  # 將在第一次調用時初始化

    @classmethod
    def get_primary_config(cls, service_type: ServiceType) -> ModelConfig:
        """獲取服務的主要配置"""
        # 嘗試從環境變數覆蓋
        env_config = cls._load_from_env(service_type)
        if env_config:
            return env_config

        return cls._DEFAULT_CONFIGS.get(service_type, cls._DEFAULT_CONFIGS[ServiceType.QA])

    @classmethod
    def get_fallback_chain(cls, service_type: ServiceType) -> list[ModelConfig]:
        """獲取服務的備援配置鏈"""
        if cls._FALLBACK_CONFIGS is None:
            cls._FALLBACK_CONFIGS = cls._get_fallback_configs()

        return cls._FALLBACK_CONFIGS.get(service_type, cls._FALLBACK_CONFIGS[ServiceType.QA])

    @classmethod
    def _load_from_env(cls, service_type: ServiceType) -> Optional[ModelConfig]:
        """從環境變數載入配置"""
        service_prefix = f"{service_type.value.upper()}_SERVICE"

        model = os.getenv(f"{service_prefix}_MODEL")
        if not model:
            return None

        # 根據模型名稱推斷提供商
        provider = cls._infer_provider(model)

        return ModelConfig(
            provider=provider,
            model=model,
            temperature=float(os.getenv(f"{service_prefix}_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv(f"{service_prefix}_MAX_TOKENS", "4096")),
            timeout=float(os.getenv(f"{service_prefix}_TIMEOUT", "30.0"))
        )

    @classmethod
    def _infer_provider(cls, model: str) -> ProviderType:
        """根據模型名稱推斷提供商"""
        if model.startswith("gpt-") or "openai" in model.lower():
            return ProviderType.OPENAI
        elif model.startswith("gemini") or "google" in model.lower():
            return ProviderType.GEMINI
        else:
            return ProviderType.OPENROUTER


class ProviderConfig:
    """提供商配置管理"""

    @staticmethod
    def get_openrouter_config() -> Dict[str, str]:
        """獲取OpenRouter配置"""
        return {
            "api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            "app_name": os.getenv("OPENROUTER_APP_NAME", "Finance Assistant"),
            "site_url": os.getenv("OPENROUTER_SITE_URL", "https://your-app.com")
        }

    @staticmethod
    def get_openai_config() -> Dict[str, str]:
        """獲取OpenAI配置"""
        return {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        }

    @staticmethod
    def get_gemini_config() -> Dict[str, str]:
        """獲取Gemini配置"""
        return {
            "api_key": os.getenv("GOOGLE_API_KEY", ""),
            "model_name": os.getenv("GOOGLE_MODEL_NAME", "models/gemini-2.5-flash")
        }