import pandas as pd
import logging
from typing import Optional

from .config import FinanceConfig
from .exceptions import DataLoadError, ConfigError

logger = logging.getLogger(__name__)

class DataLoader:
    """簡化的數據加載器 - 只管加載和標準化"""

    def __init__(self):
        # 重用現有的SpreadsheetService
        from services.invoice_service.services.spreadsheet_service import SpreadsheetService
        self.spreadsheet_service = SpreadsheetService()

    def load_from_env(self) -> pd.DataFrame:
        """從環境變數配置加載財務數據"""
        if not FinanceConfig.validate_data_config():
            raise ConfigError("數據源配置錯誤：請設置 SPREADSHEET_URL 或 SPREADSHEET_NAME")

        data_source = FinanceConfig.get_data_source()

        try:
            # 直接讀取指定的工作表
            df = self._read_finance_worksheet(data_source["value"])

            if df is None or df.empty:
                raise DataLoadError(f"無法從數據源加載數據：{data_source['value']}")

            return self._standardize_dataframe(df)

        except Exception as e:
            logger.error(f"數據加載失敗: {e}")
            raise DataLoadError(f"數據加載失敗: {str(e)}")

    def _read_finance_worksheet(self, spreadsheet_id: str) -> pd.DataFrame:
        """讀取指定的財務工作表"""
        import gspread
        from google.oauth2.service_account import Credentials
        import os
        import pandas as pd
        import json

        try:
            # 使用Google Sheets API直接讀取
            creds_data = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_data:
                raise DataLoadError("GOOGLE_APPLICATION_CREDENTIALS 未設置")

            scope = ['https://www.googleapis.com/auth/spreadsheets',
                     'https://www.googleapis.com/auth/drive']

            # 檢查是否為 JSON 字符串或文件路徑
            try:
                # 嘗試解析為 JSON 字符串
                creds_dict = json.loads(creds_data)
                credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            except json.JSONDecodeError:
                # 如果不是 JSON，當作文件路徑處理
                creds_path = creds_data

                # 處理相對路徑問題
                if not os.path.isabs(creds_path):
                    # 相對於項目根目錄
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                    creds_path = os.path.join(project_root, creds_path)

                if not os.path.exists(creds_path):
                    raise DataLoadError(f"Google認證文件不存在：{creds_path}")

                credentials = Credentials.from_service_account_file(creds_path, scopes=scope)

            client = gspread.authorize(credentials)

            # 打開指定的工作表
            sheet = client.open_by_key(spreadsheet_id)
            worksheet = sheet.worksheet(FinanceConfig.WORKSHEET_NAME)

            # 讀取所有數據
            data = worksheet.get_all_values()
            if not data:
                raise DataLoadError(f"工作表 '{FinanceConfig.WORKSHEET_NAME}' 無數據")

            # 創建DataFrame並處理重複欄位
            headers = data[0]
            rows = data[1:]

            # 處理重複欄位名稱 - 為重複的欄位添加序號
            clean_headers = []
            header_counts = {}
            for header in headers:
                if header in header_counts:
                    header_counts[header] += 1
                    clean_headers.append(f"{header}_{header_counts[header]}")
                else:
                    header_counts[header] = 1
                    clean_headers.append(header)

            df = pd.DataFrame(rows, columns=clean_headers)

            logger.info(f"成功從工作表 '{FinanceConfig.WORKSHEET_NAME}' 讀取 {len(df)} 筆數據")
            logger.info(f"處理後的欄位: {list(df.columns)}")
            return df

        except gspread.WorksheetNotFound:
            raise DataLoadError(f"找不到工作表：{FinanceConfig.WORKSHEET_NAME}")
        except Exception as e:
            raise DataLoadError(f"讀取工作表失敗：{str(e)}")

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """標準化DataFrame - 統一欄位名稱和數據類型"""
        # 檢查必需欄位
        missing_columns = [col for col in FinanceConfig.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise DataLoadError(f"數據缺少必需欄位：{missing_columns}")

        # 只保留需要的欄位
        df_filtered = df[FinanceConfig.REQUIRED_COLUMNS].copy()

        # 重命名欄位為英文
        df_filtered = df_filtered.rename(columns=FinanceConfig.COLUMN_MAPPING)

        # 標準化數據類型
        try:
            # 清理並轉換金額欄位
            df_filtered['invoice_amount'] = self._clean_amount_column(df_filtered['invoice_amount'])

            # 確保日期是日期格式
            df_filtered['invoice_date'] = pd.to_datetime(
                df_filtered['invoice_date'], errors='coerce'
            )

            # 清理字符串欄位
            for col in ['account_name', 'category', 'item_description']:
                if col in df_filtered.columns:
                    df_filtered[col] = df_filtered[col].astype(str).str.strip()

        except Exception as e:
            logger.warning(f"數據類型轉換警告: {e}")

        logger.info(f"成功載入並標準化 {len(df_filtered)} 筆財務數據")
        return df_filtered

    def _clean_amount_column(self, amount_series):
        """清理金額欄位 - 處理 NT$ 格式和負號"""
        def clean_amount(amount_str):
            if pd.isna(amount_str) or amount_str == '':
                return 0.0

            # 轉為字符串並清理
            amount_str = str(amount_str).strip()

            # 移除 NT$ 前綴
            amount_str = amount_str.replace('NT$', '').replace('$', '')

            # 移除逗號
            amount_str = amount_str.replace(',', '')

            # 處理負號
            is_negative = amount_str.startswith('-')
            if is_negative:
                amount_str = amount_str[1:]

            # 轉換為數字
            try:
                value = float(amount_str)
                return -value if is_negative else value
            except ValueError:
                logger.warning(f"無法解析金額: {amount_str}")
                return 0.0

        return amount_series.apply(clean_amount)