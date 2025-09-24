import pandas as pd
from typing import List

def calculate_total(df: pd.DataFrame, column_name: str) -> str:
    """
    計算 DataFrame 中指定數值欄位的總和。
    Args:
        column_name (str): 需要計算總和的欄位名稱。例如 '發票金額'。
    """
    if column_name not in df.columns:
        return f"錯誤：找不到名為 '{column_name}' 的欄位。"
    try:
        # 確保欄位是數值類型
        numeric_column = pd.to_numeric(df[column_name], errors='coerce')
        total = numeric_column.sum()
        return f"欄位 '{column_name}' 的總和為: {total}"
    except Exception as e:
        return f"計算總和時發生錯誤: {e}"

def get_summary_statistics(df: pd.DataFrame, column_name: str) -> str:
    """
    提供指定數值欄位的描述性統計數據 (計數, 平均值, 標準差, 最小值, 最大值等)。
    Args:
        column_name (str): 需要分析的欄位名稱。例如 '發票金額'。
    """
    if column_name not in df.columns:
        return f"錯誤：找不到名為 '{column_name}' 的欄位。"
    try:
        numeric_column = pd.to_numeric(df[column_name], errors='coerce')
        stats = numeric_column.describe()
        return f"欄位 '{column_name}' 的統計數據如下:\n{stats.to_string()}"
    except Exception as e:
        return f"獲取統計數據時發生錯誤: {e}"

def filter_by_category(df: pd.DataFrame, category_column: str, category_value: str) -> str:
    """
    根據指定的類別值篩選 DataFrame，並返回篩選後的結果。
    Args:
        category_column (str): 用於篩選的類別欄位名稱。例如 '項目'。
        category_value (str): 要篩選的類別值。例如 '餐飲'。
    """
    if category_column not in df.columns:
        return f"錯誤：找不到名為 '{category_column}' 的欄位。"
    try:
        filtered_df = df[df[category_column].astype(str).str.contains(category_value, case=False, na=False)]
        if filtered_df.empty:
            return f"在 '{category_column}' 中找不到包含 '{category_value}' 的紀錄。"
        return f"篩選結果如下:\n{filtered_df.to_string()}"
    except Exception as e:
        return f"篩選數據時發生錯誤: {e}"

def get_top_n_items(df: pd.DataFrame, value_column: str, n: int = 5) -> str:
    """
    找出指定數值欄位中最大的 N 筆紀錄。
    Args:
        value_column (str): 用於排序的數值欄位名稱。例如 '發票金額'。
        n (int): 要返回的紀錄數量，預設為 5。
    """
    if value_column not in df.columns:
        return f"錯誤：找不到名為 '{value_column}' 的欄位。"
    try:
        numeric_column = pd.to_numeric(df[value_column], errors='coerce').dropna()
        top_n = df.loc[numeric_column.nlargest(n).index]
        return f"'{value_column}' 最大的 {n} 筆紀錄如下:\n{top_n.to_string()}"
    except Exception as e:
        return f"查找最大紀錄時發生錯誤: {e}"
