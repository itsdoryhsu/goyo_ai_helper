import os
import gspread
import pandas as pd
from datetime import datetime
from ..config.settings import SPREADSHEET_NAME, WORKSHEET_NAME, GOOGLE_APPLICATION_CREDENTIALS

class SpreadsheetService:
    def __init__(self):
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        self.credentials_path = os.path.join(PROJECT_ROOT, GOOGLE_APPLICATION_CREDENTIALS)
        self.spreadsheet_name = SPREADSHEET_NAME
        self.worksheet_name = WORKSHEET_NAME
        self.gc = gspread.service_account(filename=self.credentials_path)

        # 定義類別關鍵字對應表
        self.category_keywords = {
            "餐食": ["餐廳", "食物", "便當", "飲料", "咖啡", "茶", "速食", "小吃", "自助餐", "火鍋", "燒烤", "麵食", "飯", "粥", "湯", "早餐", "午餐", "晚餐", "點心", "甜點", "蛋糕", "麵包", "飲品"],
            "雜支用品": ["文具", "紙張", "筆", "辦公用品", "清潔用品", "日用品", "洗衣粉", "衛生紙", "毛巾", "雜貨", "用品", "工具"],
            "公司設備": ["電腦", "印表機", "辦公椅", "桌子", "設備", "器材", "軟體", "硬體", "系統", "伺服器", "監視器", "鍵盤", "滑鼠"],
            "存款": ["存款", "定存", "儲蓄", "投資"],
            "房租": ["房租", "租金", "租屋", "租房", "房屋租金"],
            "薪資": ["薪水", "薪資", "工資", "月薪", "年薪", "獎金", "津貼"],
            "分攤款項": ["分攤", "平攤", "分擔", "共同", "合購"],
            "其他收入": ["其他收入", "專案服務"],
            "車費": ["車費", "交通費", "計程車", "公車", "捷運", "高鐵", "台鐵", "火車", "飛機", "機票", "車票", "運輸"],
            "利息": ["利息", "利息收入", "定存利息", "銀行利息"],
            "資訊人力服務": ["資訊", "人力", "服務", "軟體開發", "系統開發", "程式設計", "網站開發", "APP開發", "技術服務", "諮詢服務", "IT服務"],
            "健保費": ["健保費", "健保", "全民健康保險", "健康保險費"],
            "勞保費": ["勞保費", "勞保", "勞工保險", "勞工保險費"],
            "勞退金": ["勞退金", "勞退", "勞工退休金", "退休金"],
            "行政費用": ["Google Works", "AWS", "會計", "繳稅", "手續費", "政府", "雜項", "行政", "管理費", "服務費", "網路費", "點數卡", "事務所", "申報", "報名費", "HiNet"],
            "其他": ["其他", "未分類", "無法歸類"]
        }
    
    def update_spreadsheet(self, df):
        """更新 Google 試算表"""
        try:
            # 如果 spreadsheet_name 看起來像是 ID (長度大於30且包含字母數字)，使用 open_by_key
            # 否則使用 open (根據名稱開啟)
            if len(self.spreadsheet_name) > 30 and any(c.isalnum() for c in self.spreadsheet_name):
                sheet = self.gc.open_by_key(self.spreadsheet_name)
            else:
                sheet = self.gc.open(self.spreadsheet_name)

            # 嘗試開啟指定的工作表，如果失敗則使用第一個工作表
            try:
                worksheet = sheet.worksheet(self.worksheet_name)
                print(f"使用工作表: {self.worksheet_name}")
            except gspread.exceptions.WorksheetNotFound:
                print(f"找不到工作表 '{self.worksheet_name}'，使用預設工作表")
                worksheet = sheet.worksheets()[0]
            
            # 取得目前資料行數
            all_values = worksheet.get_all_values()
            current_row = len(all_values)
            
            # 取得工作表的表頭來確認欄位結構
            headers = worksheet.row_values(1) if len(all_values) > 0 else []

            # 寫入新資料 - 按照試算表現有的欄位結構
            for _, row in df.iterrows():
                current_row += 1

                # 按照試算表欄位順序建立資料陣列，只寫入到「結清」欄位
                data = []
                for header in headers:
                    if not header:  # 空欄位
                        data.append("")
                    elif header == "資料儲存時間":
                        data.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    elif header == "LINE_ID":
                        data.append(row.get('user_id', ''))
                    elif header == "帳號名稱":
                        data.append(row.get('user_display_name', ''))
                    elif header == "日期":
                        data.append(row.get('invoice_date', ''))
                    elif header == "項目":
                        data.append(row.get('transaction_type', ''))
                    elif header == "開立統編":
                        data.append(row.get('seller_id', ''))
                    elif header == "類別":
                        data.append(row.get('category', '雜支用品'))  # 使用 AI 判斷的類別，預設為雜支用品
                    elif header == "品項":
                        data.append(row.get('invoice_description', ''))
                    elif header == "發票金額":
                        data.append(int(row.get('account', 0)) if row.get('account') else "")
                    elif header == "格式":
                        data.append(row.get('invoice_type', ''))  # 這裡才是真正的發票格式
                    elif header == "發票圖片位置":
                        data.append(row.get('file_path', ''))
                    elif header == "收支人":
                        data.append("")  # 空值
                    elif header == "結清":
                        data.append("")  # 空值
                        break  # 結清後的欄位不需要處理
                    else:
                        data.append("")  # 其他未知欄位留空

                # 寫入資料到結清欄位為止（前13個欄位：A到M）
                end_col = chr(ord('A') + min(len(data), 13) - 1) if len(data) > 0 else 'A'
                worksheet.update(range_name=f'A{current_row}:{end_col}{current_row}', values=[data[:13]])
            
            print(f"成功寫入 {len(df)} 筆資料到試算表")
            return sheet.url
        except Exception as e:
           # 使用 repr(e) 來取得更詳細的錯誤物件表示法，這對除錯很有幫助
           print(f"更新試算表時發生錯誤: {repr(e)}")
           # 印出錯誤的類型，幫助我們了解 gspread 拋出了什麼類型的例外
           print(f"錯誤類型: {type(e)}")
           raise

    def read_spreadsheet(self, spreadsheet_url: str) -> pd.DataFrame:
        """
        從 Google Sheet 讀取數據並返回 Pandas DataFrame。
        這裡假設 spreadsheet_url 是一個可以直接打開的 URL。
        """
        try:
            # 從 URL 打開試算表
            # gspread 的 open_by_url 方法可以直接打開 Google Sheet
            sheet = self.gc.open_by_url(spreadsheet_url)
            worksheet = sheet.worksheets()[0]  # 讀取第一個工作表

            # 獲取所有記錄作為字典列表
            data = worksheet.get_all_records()

            # 將數據轉換為 Pandas DataFrame
            df = pd.DataFrame(data)
            return df
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"錯誤：找不到試算表，URL: {spreadsheet_url}")
            return None
        except Exception as e:
            print(f"讀取試算表時發生錯誤: {repr(e)}")
            return None

    def read_spreadsheet_by_name(self, spreadsheet_name: str) -> pd.DataFrame:
        """
        從 Google Sheet 讀取數據並返回 Pandas DataFrame。
        這裡假設 spreadsheet_name 是試算表的名稱或ID。
        """
        try:
            # 如果 spreadsheet_name 看起來像是 ID (長度大於30且包含字母數字)，使用 open_by_key
            # 否則使用 open (根據名稱開啟)
            if len(spreadsheet_name) > 30 and any(c.isalnum() for c in spreadsheet_name):
                sheet = self.gc.open_by_key(spreadsheet_name)
            else:
                sheet = self.gc.open(spreadsheet_name)
            worksheet = sheet.worksheets()[0]  # 讀取第一個工作表
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            return df
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"錯誤：找不到試算表，名稱/ID: {spreadsheet_name}")
            return None
        except Exception as e:
            print(f"讀取試算表時發生錯誤: {repr(e)}")
            return None