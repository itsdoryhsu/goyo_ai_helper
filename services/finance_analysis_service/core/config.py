import os
from typing import Dict, List
from enum import Enum

class QuestionType(Enum):
    REVENUE_ANALYSIS = "revenue"
    EXPENSE_ANALYSIS = "expense"
    PROFIT_ANALYSIS = "profit"
    RATIO_ANALYSIS = "ratio"
    TREND_ANALYSIS = "trend"
    TEACHING = "teaching"
    GENERAL_QUERY = "general"

class FinanceConfig:
    # 數據源配置
    SPREADSHEET_URL: str = os.getenv("SPREADSHEET_URL")
    SPREADSHEET_NAME: str = os.getenv("SPREADSHEET_NAME")

    # 欄位映射 - 統一數據結構（根據實際spreadsheet結構）
    COLUMN_MAPPING: Dict[str, str] = {
        "帳號名稱": "account_name",
        "項目": "transaction_type",  # 收入/支出
        "類別": "category",         # 具體類別
        "品項": "item_description",
        "日期": "invoice_date",
        "發票金額": "invoice_amount"
    }

    # 必需欄位 - 缺少任何一個就報錯
    REQUIRED_COLUMNS: List[str] = ["帳號名稱", "項目", "類別", "品項", "日期", "發票金額"]

    # 工作表名稱配置
    WORKSHEET_NAME: str = "收入支出"

    # 業務規則 - 營收和支出的判斷邏輯 (根據實際數據結構調整)
    # 可能在 "項目" 欄位或 "類別" 欄位
    REVENUE_KEYWORDS: List[str] = ["收入", "營收", "業績", "銷售", "進帳"]
    EXPENSE_KEYWORDS: List[str] = ["支出", "費用", "成本", "開銷", "支付"]
    NON_OPERATING_KEYWORDS: List[str] = ["資本額", "股東往來", "借款", "利息收入", "資本"]

    # 問題分類關鍵詞
    QUESTION_KEYWORDS: Dict[QuestionType, List[str]] = {
        QuestionType.REVENUE_ANALYSIS: ["收入", "營收", "業績", "銷售"],
        QuestionType.EXPENSE_ANALYSIS: ["支出", "費用", "成本", "開銷"],
        QuestionType.PROFIT_ANALYSIS: ["利潤", "獲利", "盈利", "淨利"],
        QuestionType.RATIO_ANALYSIS: ["率", "比率", "比例", "佔比"],
        QuestionType.TREND_ANALYSIS: ["趨勢", "變化", "成長", "月份", "季度", "年度"],
        QuestionType.TEACHING: ["什麼是", "如何計算", "怎麼算", "定義", "解釋", "教我", "學習", "概念", "意思", "怎麼看", "有什麼", "哪些", "可以", "推薦", "建議", "指標", "評估", "分析方法", "怎麼選"]
    }

    # LLM配置 - 使用新的服務專用配置格式
    LLM_PROVIDER: str = os.getenv("FINANCE_PROVIDER", "openrouter")
    LLM_MODEL: str = os.getenv("FINANCE_SERVICE_MODEL", "x-ai/grok-4-fast:free")
    LLM_TEMPERATURE: float = float(os.getenv("FINANCE_SERVICE_TEMPERATURE", "0.3"))
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    @classmethod
    def validate_data_config(cls) -> bool:
        """驗證數據配置是否完整"""
        return bool(cls.SPREADSHEET_URL or cls.SPREADSHEET_NAME)

    @classmethod
    def validate_llm_config(cls) -> bool:
        """驗證LLM配置是否完整"""
        if cls.LLM_PROVIDER == "openrouter":
            return bool(cls.OPENROUTER_API_KEY)
        elif cls.LLM_PROVIDER == "openai":
            return bool(cls.OPENAI_API_KEY)
        return False

    @classmethod
    def get_data_source(cls) -> Dict[str, str]:
        """獲取數據源配置"""
        if cls.SPREADSHEET_URL:
            return {"type": "url", "value": cls.SPREADSHEET_URL}
        elif cls.SPREADSHEET_NAME:
            return {"type": "name", "value": cls.SPREADSHEET_NAME}
        else:
            raise ValueError("未配置數據源：請設置 SPREADSHEET_URL 或 SPREADSHEET_NAME")