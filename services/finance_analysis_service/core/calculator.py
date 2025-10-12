import pandas as pd
import logging
from typing import Dict, Any, List
from datetime import datetime

from .config import FinanceConfig, QuestionType
from .exceptions import CalculationError

logger = logging.getLogger(__name__)

class FinancialCalculator:
    """財務計算器 - 只管計算，不管AI"""

    def analyze_question(self, question: str) -> QuestionType:
        """分析問題類型 - 簡單關鍵詞匹配，教學問題優先"""
        question_lower = question.lower()

        # 優先檢查教學問題
        teaching_keywords = FinanceConfig.QUESTION_KEYWORDS.get(QuestionType.TEACHING, [])
        if any(keyword in question_lower for keyword in teaching_keywords):
            return QuestionType.TEACHING

        # 然後檢查其他類型
        for question_type, keywords in FinanceConfig.QUESTION_KEYWORDS.items():
            if question_type == QuestionType.TEACHING:
                continue  # 已經檢查過了
            if any(keyword in question_lower for keyword in keywords):
                return question_type

        return QuestionType.GENERAL_QUERY

    def calculate_metrics(self, df: pd.DataFrame, question_type: QuestionType) -> Dict[str, Any]:
        """根據問題類型計算相應指標"""
        try:
            base_metrics = self._get_base_metrics(df)

            if question_type == QuestionType.REVENUE_ANALYSIS:
                return {**base_metrics, **self._get_revenue_metrics(df)}
            elif question_type == QuestionType.EXPENSE_ANALYSIS:
                return {**base_metrics, **self._get_expense_metrics(df)}
            elif question_type == QuestionType.PROFIT_ANALYSIS:
                return {**base_metrics, **self._get_profit_metrics(df)}
            elif question_type == QuestionType.RATIO_ANALYSIS:
                return {**base_metrics, **self._get_ratio_metrics(df)}
            elif question_type == QuestionType.TREND_ANALYSIS:
                return {**base_metrics, **self._get_trend_metrics(df)}
            elif question_type == QuestionType.TEACHING:
                # 教學問題只需要基本指標即可，重點在AI的解釋
                return base_metrics
            else:
                return base_metrics

        except Exception as e:
            logger.error(f"計算指標失敗: {e}")
            raise CalculationError(f"財務計算失敗: {str(e)}")

    def _get_base_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """基礎指標 - 每次都計算"""
        logger.info(f"開始計算基礎指標，數據筆數: {len(df)}")
        total_revenue = self._calculate_revenue(df)
        total_expense = self._calculate_expense(df)
        logger.info(f"計算完成 - 總營收: {total_revenue}, 總支出: {total_expense}")

        return {
            "data_period": self._get_date_range(df),
            "total_records": len(df),
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "net_profit": total_revenue - total_expense
        }

    def _get_revenue_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """營收分析指標"""
        revenue_df = self._filter_revenue_data(df)

        return {
            "revenue_breakdown": self._breakdown_by_category(revenue_df, 'account_name'),
            "revenue_by_month": self._breakdown_by_month(revenue_df),
            "avg_monthly_revenue": revenue_df['invoice_amount'].sum() / max(1, revenue_df['invoice_date'].dt.month.nunique())
        }

    def _get_expense_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """支出分析指標"""
        expense_df = self._filter_expense_data(df)
        logger.info(f"支出數據筆數: {len(expense_df)}")

        expense_breakdown = self._breakdown_by_category(expense_df, 'category')
        logger.info(f"支出分解: {expense_breakdown}")

        return {
            "expense_breakdown": expense_breakdown,
            "expense_by_month": self._breakdown_by_month(expense_df),
            "avg_monthly_expense": expense_df['invoice_amount'].sum() / max(1, expense_df['invoice_date'].dt.month.nunique())
        }

    def _get_profit_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """獲利分析指標"""
        revenue = self._calculate_revenue(df)
        expense = self._calculate_expense(df)

        return {
            "gross_profit": revenue - expense,
            "profit_margin": (revenue - expense) / revenue * 100 if revenue > 0 else 0,
            "monthly_profit": self._calculate_monthly_profit(df)
        }

    def _get_ratio_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """比率分析指標"""
        revenue = self._calculate_revenue(df)
        expense = self._calculate_expense(df)

        return {
            "expense_ratio": expense / revenue * 100 if revenue > 0 else 0,
            "profit_ratio": (revenue - expense) / revenue * 100 if revenue > 0 else 0,
            "expense_structure": self._calculate_expense_structure(df)
        }

    def _get_trend_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """趋势分析指標"""
        return {
            "monthly_trend": self._calculate_monthly_trend(df),
            "growth_rate": self._calculate_growth_rate(df)
        }

    def _calculate_revenue(self, df: pd.DataFrame) -> float:
        """計算營業收入 - 使用關鍵詞匹配，更靈活的業務規則"""
        # 在多個欄位中尋找收入相關關鍵詞
        revenue_mask = False

        # 檢查 transaction_type (項目) 欄位
        if 'transaction_type' in df.columns:
            revenue_mask |= df['transaction_type'].str.contains('|'.join(FinanceConfig.REVENUE_KEYWORDS), na=False, case=False)

        # 檢查 category (類別) 欄位
        if 'category' in df.columns:
            revenue_mask |= df['category'].str.contains('|'.join(FinanceConfig.REVENUE_KEYWORDS), na=False, case=False)

        # 檢查 account_name (帳號名稱) 欄位
        if 'account_name' in df.columns:
            revenue_mask |= df['account_name'].str.contains('|'.join(FinanceConfig.REVENUE_KEYWORDS), na=False, case=False)

        # 排除非營業項目
        if 'item_description' in df.columns:
            revenue_mask &= ~df['item_description'].str.contains('|'.join(FinanceConfig.NON_OPERATING_KEYWORDS), na=False, case=False)

        return df[revenue_mask]['invoice_amount'].sum()

    def _calculate_expense(self, df: pd.DataFrame) -> float:
        """計算營業費用 - 使用關鍵詞匹配"""
        expense_mask = False

        # 檢查 transaction_type (項目) 欄位
        if 'transaction_type' in df.columns:
            expense_mask |= df['transaction_type'].str.contains('|'.join(FinanceConfig.EXPENSE_KEYWORDS), na=False, case=False)

        # 檢查 category (類別) 欄位
        if 'category' in df.columns:
            expense_mask |= df['category'].str.contains('|'.join(FinanceConfig.EXPENSE_KEYWORDS), na=False, case=False)

        # 檢查 account_name (帳號名稱) 欄位
        if 'account_name' in df.columns:
            expense_mask |= df['account_name'].str.contains('|'.join(FinanceConfig.EXPENSE_KEYWORDS), na=False, case=False)

        return df[expense_mask]['invoice_amount'].sum()

    def _filter_revenue_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """篩選營收數據 - 使用與 _calculate_revenue 相同的邏輯"""
        # 正確初始化 mask 為 pandas Series
        revenue_mask = pd.Series([False] * len(df), index=df.index)

        # 檢查 transaction_type (項目) 欄位
        if 'transaction_type' in df.columns:
            revenue_mask |= df['transaction_type'].str.contains('|'.join(FinanceConfig.REVENUE_KEYWORDS), na=False, case=False)

        # 檢查 category (類別) 欄位
        if 'category' in df.columns:
            revenue_mask |= df['category'].str.contains('|'.join(FinanceConfig.REVENUE_KEYWORDS), na=False, case=False)

        # 檢查 account_name (帳號名稱) 欄位
        if 'account_name' in df.columns:
            revenue_mask |= df['account_name'].str.contains('|'.join(FinanceConfig.REVENUE_KEYWORDS), na=False, case=False)

        # 排除非營業項目
        if 'item_description' in df.columns:
            revenue_mask &= ~df['item_description'].str.contains('|'.join(FinanceConfig.NON_OPERATING_KEYWORDS), na=False, case=False)

        logger.info(f"篩選營收數據: 找到 {revenue_mask.sum()} 筆收入記錄")
        return df[revenue_mask].copy()

    def _filter_expense_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """篩選支出數據 - 使用與 _calculate_expense 相同的邏輯"""
        # 正確初始化 mask 為 pandas Series
        expense_mask = pd.Series([False] * len(df), index=df.index)

        # 檢查 transaction_type (項目) 欄位
        if 'transaction_type' in df.columns:
            expense_mask |= df['transaction_type'].str.contains('|'.join(FinanceConfig.EXPENSE_KEYWORDS), na=False, case=False)

        # 檢查 category (類別) 欄位
        if 'category' in df.columns:
            expense_mask |= df['category'].str.contains('|'.join(FinanceConfig.EXPENSE_KEYWORDS), na=False, case=False)

        # 檢查 account_name (帳號名稱) 欄位
        if 'account_name' in df.columns:
            expense_mask |= df['account_name'].str.contains('|'.join(FinanceConfig.EXPENSE_KEYWORDS), na=False, case=False)

        logger.info(f"篩選支出數據: 找到 {expense_mask.sum()} 筆支出記錄")
        return df[expense_mask].copy()

    def _breakdown_by_category(self, df: pd.DataFrame, column: str) -> Dict[str, float]:
        """按分類分解數據"""
        return df.groupby(column)['invoice_amount'].sum().round(2).to_dict()

    def _breakdown_by_month(self, df: pd.DataFrame) -> Dict[str, float]:
        """按月份分解數據"""
        df['month'] = df['invoice_date'].dt.to_period('M').astype(str)
        return df.groupby('month')['invoice_amount'].sum().round(2).to_dict()

    def _get_date_range(self, df: pd.DataFrame) -> str:
        """獲取數據日期範圍"""
        if df['invoice_date'].isna().all():
            return "日期數據不完整"

        start_date = df['invoice_date'].min()
        end_date = df['invoice_date'].max()
        return f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"

    def _calculate_monthly_profit(self, df: pd.DataFrame) -> Dict[str, float]:
        """計算月度利潤"""
        df['month'] = df['invoice_date'].dt.to_period('M').astype(str)
        monthly_revenue = self._filter_revenue_data(df).groupby('month')['invoice_amount'].sum()
        monthly_expense = self._filter_expense_data(df).groupby('month')['invoice_amount'].sum()

        monthly_profit = {}
        all_months = set(monthly_revenue.index) | set(monthly_expense.index)

        for month in all_months:
            revenue = monthly_revenue.get(month, 0)
            expense = monthly_expense.get(month, 0)
            monthly_profit[month] = round(revenue - expense, 2)

        return monthly_profit

    def _calculate_expense_structure(self, df: pd.DataFrame) -> Dict[str, float]:
        """計算支出結構佔比"""
        expense_df = self._filter_expense_data(df)
        total_expense = expense_df['invoice_amount'].sum()

        if total_expense == 0:
            return {}

        structure = expense_df.groupby('account_name')['invoice_amount'].sum()
        return {k: round(v / total_expense * 100, 2) for k, v in structure.items()}

    def _calculate_monthly_trend(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """計算月度趨勢"""
        df['month'] = df['invoice_date'].dt.to_period('M').astype(str)

        monthly_revenue = self._filter_revenue_data(df).groupby('month')['invoice_amount'].sum()
        monthly_expense = self._filter_expense_data(df).groupby('month')['invoice_amount'].sum()

        trend = {}
        all_months = sorted(set(monthly_revenue.index) | set(monthly_expense.index))

        for month in all_months:
            trend[month] = {
                "revenue": round(monthly_revenue.get(month, 0), 2),
                "expense": round(monthly_expense.get(month, 0), 2)
            }

        return trend

    def _calculate_growth_rate(self, df: pd.DataFrame) -> Dict[str, float]:
        """計算成長率"""
        monthly_revenue = self._filter_revenue_data(df).groupby(
            df['invoice_date'].dt.to_period('M')
        )['invoice_amount'].sum().sort_index()

        if len(monthly_revenue) < 2:
            return {"revenue_growth_rate": 0}

        first_month = monthly_revenue.iloc[0]
        last_month = monthly_revenue.iloc[-1]

        if first_month == 0:
            return {"revenue_growth_rate": 0}

        growth_rate = (last_month - first_month) / first_month * 100
        return {"revenue_growth_rate": round(growth_rate, 2)}