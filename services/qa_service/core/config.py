import os
from typing import Dict, Any

class QAConfig:
    """QA Service 配置管理 - 統一LLM提供商設定"""

    # LLM 配置
    LLM_PROVIDER: str = os.getenv("QA_PROVIDER", "openrouter")
    LLM_MODEL: str = os.getenv("QA_SERVICE_MODEL", "openai/gpt-oss-20b:free")
    LLM_TEMPERATURE: float = float(os.getenv("QA_SERVICE_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("QA_SERVICE_MAX_TOKENS", "4096"))

    # OpenRouter 配置
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # OpenAI 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Gemini 配置
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_MODEL_NAME: str = os.getenv("GOOGLE_MODEL_NAME", "models/gemini-2.5-flash")

    # Vector Store 配置
    VECTORSTORE_PATH: str = os.getenv("QA_VECTORSTORE_PATH", "data/vectorstore")
    COLLECTION_NAME: str = os.getenv("QA_COLLECTION_NAME", "finance_tax_documents")

    # 檢索配置
    TOP_K_SOURCES: int = int(os.getenv("QA_TOP_K_SOURCES", "3"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("QA_SIMILARITY_THRESHOLD", "0.7"))

    # 系統提示
    SYSTEM_PROMPT: str = """你是果果財務稅法顧問，一位親切專業的財務稅法專家，致力於用最易懂的方式幫助客戶解決財務和稅務問題。

🎯 回答風格要求：
1. 以親切、專業且有溫度的語調回答，就像面對面諮詢的顧問
2. 用簡潔易懂的語言解釋複雜概念，避免過於艱澀的專業術語
3. 優先回答用戶最關心的核心問題，再提供相關細節
4. 語氣親和但專業，展現專業度的同時保持親切感

📋 回答原則：
• 使用繁體中文，語氣自然流暢
• 基於提供的文檔內容作為主要依據
• 如文檔信息不足，會明確說明並提供專業建議
• 避免冗長的條列式回答，改用對話式說明
• 回答要準確可靠，如有不確定會誠實說明

📚 參考文檔: {context}

💡 回答架構：
1. 簡潔開場：直接回應用戶關心的核心問題
2. 清楚說明：用親切的語言解釋相關概念或規定
3. 實用建議：提供具體可行的建議或下一步作法
4. 適時提醒：如有重要注意事項會特別提醒

請用這種親切專業的顧問風格來回答用戶的問題。"""

    # 簡單問題的精簡提示 (無需文檔參考)
    SIMPLE_PROMPT: str = """你是果果財務稅法顧問，一位親切專業的財務稅法專家。

重要指引：
• 記住我們之前的對話內容，保持對話的連貫性
• 如果我們已經互相認識，不需要重複自我介紹
• 用自然流暢的語調回應，就像面對面聊天
• 避免重複提及相同的服務或能力

請用簡潔親切的語調回答用戶的問題，保持專業但溫暖的個性。使用繁體中文，語氣自然流暢。"""

    @classmethod
    def validate_llm_config(cls) -> bool:
        """驗證LLM配置是否完整"""
        if cls.LLM_PROVIDER == "openrouter":
            return bool(cls.OPENROUTER_API_KEY)
        elif cls.LLM_PROVIDER == "openai":
            return bool(cls.OPENAI_API_KEY)
        elif cls.LLM_PROVIDER == "google":
            return bool(cls.GOOGLE_API_KEY)
        return False

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """獲取當前LLM配置"""
        return {
            "provider": cls.LLM_PROVIDER,
            "model": cls.LLM_MODEL,
            "temperature": cls.LLM_TEMPERATURE,
            "max_tokens": cls.LLM_MAX_TOKENS
        }