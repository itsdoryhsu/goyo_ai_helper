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
            # 檢查是否為教學問題，使用特殊處理
            if question_type == QuestionType.TEACHING:
                return await self._answer_teaching_question(question, metrics)

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

        prompt = f"""你是資深財務分析師，擅長將複雜財務數據轉化為清晰洞察和專業建議。

{system_context}

### 用戶問題
{question}

### 財務數據
{financial_data}

### 專業分析要求
1. 深度解讀數據背後的商業意義
2. 提供趨勢判斷和風險評估
3. 給出具體可行的改善建議
4. 解釋重要數字的影響和原因

### LINE手機閱讀優化格式

💰 [簡潔有力的核心結論, 1行]

📊 關鍵數字
[最重要的2-3個數字, 每行1個重點]

💡 實用建議
[1-2個具體可行動的建議]

### 手機閱讀最佳化要求：
1. 每行最多15-20字, 避免折行
2. 用emoji分隔, 提升視覺層次
3. 數字要加千分位符號 (如 $1,234)
4. 重點用空行分隔, 方便快速掃讀
5. 避免超過15行, 保持訊息簡潔
6. 專業但口語化, 易於理解
7. 直接回答用戶問題, 不繞彎子

範例格式：
💰 9月營收穩步成長，毛利率維持高檔

📊 關鍵數字
• 營收：$45,678（+12.5%）
• 毛利率：38.2%（持平）
• 主力產品A：佔比60%，穩定貢獻

💡 實用建議
• 加強產品A推廣
• 關注淡季準備"""

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
        formatted_lines.append(f"數據期間：{metrics.get('data_period', 'N/A')}")
        formatted_lines.append(f"總記錄數：{metrics.get('total_records', 0):,} 筆")
        formatted_lines.append(f"總營收：${metrics.get('total_revenue', 0):,.2f}")
        formatted_lines.append(f"總支出：${metrics.get('total_expense', 0):,.2f}")
        formatted_lines.append(f"淨利潤：${metrics.get('net_profit', 0):,.2f}")

        # 根據問題類型添加特定指標
        if question_type == QuestionType.REVENUE_ANALYSIS:
            if 'revenue_breakdown' in metrics:
                formatted_lines.append("\n營收分解（按帳戶）：")
                for category, amount in metrics['revenue_breakdown'].items():
                    formatted_lines.append(f"  - {category}：${amount:,.2f}")

            if 'revenue_by_month' in metrics:
                formatted_lines.append("\n月度營收：")
                for month, amount in metrics['revenue_by_month'].items():
                    formatted_lines.append(f"  - {month}：${amount:,.2f}")

        elif question_type == QuestionType.EXPENSE_ANALYSIS and 'expense_breakdown' in metrics:
            formatted_lines.append("\n支出分解：")
            for category, amount in metrics['expense_breakdown'].items():
                formatted_lines.append(f"  - {category}：${amount:,.2f}")

        elif question_type == QuestionType.RATIO_ANALYSIS:
            if 'profit_ratio' in metrics:
                formatted_lines.append(f"利潤率：{metrics['profit_ratio']:.2f}%")
            if 'expense_ratio' in metrics:
                formatted_lines.append(f"費用率：{metrics['expense_ratio']:.2f}%")

        elif question_type == QuestionType.TREND_ANALYSIS and 'monthly_trend' in metrics:
            formatted_lines.append("\n月度趨勢：")
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

📊 財務概覽
- 數據期間：{metrics.get('data_period', 'N/A')}
- 總營收：${metrics.get('total_revenue', 0):,.2f}
- 總支出：${metrics.get('total_expense', 0):,.2f}
- 淨利潤：${metrics.get('net_profit', 0):,.2f}

建議您稍後再試，或聯系技術支持。"""

    async def _answer_teaching_question(self, question: str, metrics: Dict[str, Any]) -> str:
        """專門處理教學問題 - 提供概念解釋和實例"""
        try:
            # 建立專門的教學提示詞
            teaching_prompt = self._build_teaching_prompt(question, metrics)

            messages = [{"role": "user", "content": teaching_prompt}]
            response = await self.model_service.finance_completion(messages)

            content = response.content if hasattr(response, 'content') else str(response)
            return self._format_response(content)

        except Exception as e:
            logger.error(f"教學問題AI分析失敗: {e}")
            # 教學問題的降級回應
            return self._fallback_teaching_response(question, metrics)

    def _build_teaching_prompt(self, question: str, metrics: Dict[str, Any]) -> str:
        """構建教學專用提示詞"""

        financial_data = self._format_basic_metrics(metrics)

        prompt = f"""你是專業的財務教學老師，擅長用簡單易懂的方式解釋財務概念，並結合實際數據進行教學。

### 學生問題
{question}

### 實際財務數據（用作教學範例）
{financial_data}

### 教學目標
1. 清楚解釋財務概念的定義和意義
2. 結合實際數據示範計算過程
3. 說明該概念在實務上的應用價值
4. 提供簡單易記的理解方法

### LINE手機教學最佳化格式

📚 概念解釋
[用白話文解釋核心概念，1-2行]

🧮 計算方式
[具體公式和步驟，結合實際數據]

💡 實務意義
[為什麼要關注這個指標]

🎯 快速判斷
[簡單的判斷標準或經驗法則]

### 教學表達要求：
1. 避免專業術語，用生活化比喻
2. 計算步驟要清晰，一步一步來
3. 數字要實際代入，不要只給公式
4. 每行最多15-20字，適合手機閱讀
5. 用emoji增加親和力
6. 重點用空行分隔，方便快速理解

範例格式：
📚 概念解釋
毛利率 = 賺錢效率指標
看每100元營收能留下多少錢

🧮 計算方式
毛利率 = (營收-成本) ÷ 營收 × 100%
= ($45,000-$30,000) ÷ $45,000 × 100%
= 33.3%

💡 實務意義
毛利率越高 = 產品競爭力越強
可以承受更多行銷和管理費用

🎯 快速判斷
• 30%以上：不錯
• 20-30%：普通
• 低於20%：要注意"""

        return prompt

    def _format_basic_metrics(self, metrics: Dict[str, Any]) -> str:
        """格式化基礎指標用於教學"""
        lines = []
        lines.append(f"數據期間：{metrics.get('data_period', 'N/A')}")
        lines.append(f"總營收：${metrics.get('total_revenue', 0):,.2f}")
        lines.append(f"總支出：${metrics.get('total_expense', 0):,.2f}")
        lines.append(f"淨利潤：${metrics.get('net_profit', 0):,.2f}")

        # 添加一些基本比率用於教學
        revenue = metrics.get('total_revenue', 0)
        expense = metrics.get('total_expense', 0)
        if revenue > 0:
            profit_ratio = ((revenue - expense) / revenue) * 100
            lines.append(f"利潤率：{profit_ratio:.1f}%")

        return "\n".join(lines)

    def _fallback_teaching_response(self, question: str, metrics: Dict[str, Any]) -> str:
        """教學問題的降級回應"""
        return f"""📚 關於「{question}」

抱歉，AI教學功能暫時不可用，但我可以提供基本說明：

💼 你的數據概況
• 營收：${metrics.get('total_revenue', 0):,.2f}
• 支出：${metrics.get('total_expense', 0):,.2f}
• 淨利：${metrics.get('net_profit', 0):,.2f}

📖 建議資源
• 請查閱財務基礎教材
• 或稍後重新詢問相同問題
• 也可以更具體地描述想了解的部分

🔧 技術支援
如持續無法使用，請聯繫技術團隊"""

    async def close(self):
        """關閉 model_service"""
        if self.model_service:
            await self.model_service.close()