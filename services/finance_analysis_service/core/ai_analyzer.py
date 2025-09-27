import json
import logging
from typing import Dict, Any

from .config import FinanceConfig, QuestionType
from .exceptions import AIError, ConfigError

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """AI分析器 - 使用統一 model_service"""

    def __init__(self):
        self.model_service = self._initialize_model_service()

    def _initialize_model_service(self):
        """初始化統一 model_service"""
        try:
            from services.model_service import create_model_service
            return create_model_service()
        except Exception as e:
            logger.error(f"Model service 初始化失敗: {e}")
            raise ConfigError(f"LLM配置錯誤: {str(e)}")

    async def answer(self, question: str, metrics: Dict[str, Any], question_type: QuestionType) -> str:
        """生成AI回答 - 結合問題、計算結果和問題類型"""
        try:
            prompt = self._build_prompt(question, metrics, question_type)

            # 使用統一 model_service 進行財務分析
            messages = [{"role": "user", "content": prompt}]
            response = await self.model_service.finance_completion(messages)

            # 提取回應內容
            content = response.content if hasattr(response, 'content') else str(response)
            return self._format_response(content)

        except Exception as e:
            logger.error(f"AI分析失敗: {e}")
            # 優雅降級：返回純計算結果
            return self._fallback_response(question, metrics)

    def _build_prompt(self, question: str, metrics: Dict[str, Any], question_type: QuestionType) -> str:
        """構建給LLM的提示詞 - 簡單直接"""

        system_context = self._get_system_context()
        financial_data = self._format_metrics_for_llm(metrics, question_type)

        prompt = f"""你是專業的財務分析師，請根據以下財務數據回答用戶問題。這是LINE訊息回覆，請用簡潔易讀的格式。

{system_context}

### 用戶問題
{question}

### 財務數據
{financial_data}

### LINE訊息回答格式要求
請用以下簡潔格式回答，每部分用換行分隔：

💰 **核心發現**
[1句話總結關鍵結果]

📈 **關鍵數據**
• 營收：$XXX
• 支出：$XXX
• 淨利：$XXX

💡 **建議**
[1-2個簡短實用建議，每個用• 開頭]

注意：保持簡潔，避免長段落，適合手機閱讀。"""

        return prompt

    def _get_system_context(self) -> str:
        """獲取系統上下文"""
        return """### 財務分析規則
- 營業收入：類別為「收入」但排除資本額、股東往來、借款、利息收入等非營業項目
- 營業費用：類別為「支出」
- 淨利潤：營業收入 - 營業費用
- 利潤率：(營業收入 - 營業費用) / 營業收入 × 100%"""

    def _format_metrics_for_llm(self, metrics: Dict[str, Any], question_type: QuestionType) -> str:
        """格式化財務指標給LLM閱讀"""
        formatted_lines = []

        # 基礎指標
        formatted_lines.append(f"**數據期間**：{metrics.get('data_period', 'N/A')}")
        formatted_lines.append(f"**總記錄數**：{metrics.get('total_records', 0):,} 筆")
        formatted_lines.append(f"**總營收**：${metrics.get('total_revenue', 0):,.2f}")
        formatted_lines.append(f"**總支出**：${metrics.get('total_expense', 0):,.2f}")
        formatted_lines.append(f"**淨利潤**：${metrics.get('net_profit', 0):,.2f}")

        # 根據問題類型添加特定指標
        if question_type == QuestionType.REVENUE_ANALYSIS and 'revenue_breakdown' in metrics:
            formatted_lines.append("\n**營收分解**：")
            for category, amount in metrics['revenue_breakdown'].items():
                formatted_lines.append(f"  - {category}：${amount:,.2f}")

        elif question_type == QuestionType.EXPENSE_ANALYSIS and 'expense_breakdown' in metrics:
            formatted_lines.append("\n**支出分解**：")
            for category, amount in metrics['expense_breakdown'].items():
                formatted_lines.append(f"  - {category}：${amount:,.2f}")

        elif question_type == QuestionType.RATIO_ANALYSIS:
            if 'profit_ratio' in metrics:
                formatted_lines.append(f"**利潤率**：{metrics['profit_ratio']:.2f}%")
            if 'expense_ratio' in metrics:
                formatted_lines.append(f"**費用率**：{metrics['expense_ratio']:.2f}%")

        elif question_type == QuestionType.TREND_ANALYSIS and 'monthly_trend' in metrics:
            formatted_lines.append("\n**月度趨勢**：")
            for month, data in list(metrics['monthly_trend'].items())[-3:]:  # 最近3個月
                formatted_lines.append(f"  - {month}：收入 ${data['revenue']:,.2f}，支出 ${data['expense']:,.2f}")

        return "\n".join(formatted_lines)

    def _format_response(self, response_content: str) -> str:
        """格式化LLM回應"""
        # 簡單清理，確保格式正確
        return response_content.strip()

    def _fallback_response(self, question: str, metrics: Dict[str, Any]) -> str:
        """降級回應 - AI失敗時的純數據回答"""
        return f"""抱歉，AI分析暫時不可用，以下是關於「{question}」的基礎數據：

📊 **財務概覽**
- 數據期間：{metrics.get('data_period', 'N/A')}
- 總營收：${metrics.get('total_revenue', 0):,.2f}
- 總支出：${metrics.get('total_expense', 0):,.2f}
- 淨利潤：${metrics.get('net_profit', 0):,.2f}

建議您稍後再試，或聯系技術支持。"""

    async def close(self):
        """關閉 model_service"""
        if self.model_service:
            await self.model_service.close()