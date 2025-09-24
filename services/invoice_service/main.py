import pandas as pd
import asyncio # 導入 asyncio
from .services.drive_service import DriveService
from .services.ocr_service import OCRService
from .services.spreadsheet_service import SpreadsheetService
from services.model_service.manager import model_manager # 導入 model_manager 實例
from .utils.file_utils import get_media_type, generate_drive_link

class InvoiceProcessor:
    def __init__(self):
        self.drive_service = DriveService()
        self.ocr_service = OCRService()
        self.spreadsheet_service = SpreadsheetService()
        self.model_manager = model_manager # 使用 model_manager 實例
        self.category_keywords = self.spreadsheet_service.category_keywords # 取得類別關鍵字

    async def determine_category(self, invoice_description: str) -> str:
        """
        根據發票描述判斷類別，優先使用關鍵字匹配，若無則使用 AI 輔助判斷。
        """
        # 1. 關鍵字匹配
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in invoice_description:
                    print(f"🔍 關鍵字匹配成功，類別為: {category}")
                    return category
        
        # 2. AI 輔助判斷
        print("🤖 關鍵字匹配失敗，啟動 AI 輔助判斷類別...")
        prompt = (
            f"請根據以下發票描述判斷最符合的類別。請從以下類別中選擇一個：{list(self.category_keywords.keys())}。\n"
            f"如果沒有任何類別符合，請回答 '其他'。\n"
            f"發票描述: {invoice_description}\n"
            f"請直接回答類別名稱，不要包含任何額外文字。"
        )
        
        try:
            # 這裡假設 model_manager.send_message 是一個非同步方法
            response = await self.model_manager.send_message(
                prompt=prompt,
                model_profile="default_text_model" # 假設有一個預設的文字模型配置
            )
            ai_category = response.strip()
            if ai_category in self.category_keywords:
                print(f"✅ AI 輔助判斷成功，類別為: {ai_category}")
                return ai_category
            else:
                print(f"⚠️ AI 輔助判斷結果 '{ai_category}' 不在預設類別中，將使用 '其他'")
                return '其他'
        except Exception as e:
            print(f"❌ AI 輔助判斷類別時發生錯誤: {e}，將使用 '其他'")
            return '其他'

    async def process_invoice_from_data(self, file_data: bytes, media_type: str):
        """從二進位資料處理單一發票檔案並進行 OCR 分析"""
        try:
            print(f"處理來自 LINE Bot 的檔案，媒體類型: {media_type}")
            # 解開 OCR 服務回傳的元組
            invoice_data, usage = await self.ocr_service.extract_invoice_data(file_data, media_type) # 使用 await
            transaction_type = self.ocr_service.define_trancsaction_type(invoice_data)
            
            # 使用新的 determine_category 方法判斷類別
            determined_category = await self.determine_category(invoice_data.invoice_description)

            # 保持您期望的 'result' 結構
            result = {
                'transaction_type': transaction_type,
                'seller_id': invoice_data.seller_id,
                'invoice_description': invoice_data.invoice_description,
                'invoice_number': invoice_data.invoice_number,
                'invoice_date': invoice_data.invoice_date,
                'account': invoice_data.account,
                'invoice_type': invoice_data.invoice_type,
                'category': determined_category,  # 使用判斷後的類別
                'file_path': 'N/A (from LINE Bot)'
            }
            print(f"✅ 成功辨識發票: {result}")
            # 同時回傳辨識結果和 usage 資訊
            return result, usage
            
        except Exception as e:
            print(f"處理檔案時發生錯誤: {e}")
            raise

    def save_invoice_data(self, invoice_data: dict, file_data: bytes, media_type: str) -> str:
        """將單筆發票資料儲存到試算表並上傳檔案到 Google Drive"""
        try:
            print(f"正在儲存發票資料到試算表: {invoice_data}")

            # 從 invoice_data 中提取使用者資訊
            user_id = invoice_data.get('user_id', 'unknown_user')
            user_display_name = invoice_data.get('user_display_name', '未知使用者')

            # 上傳檔案到 Google Drive
            file_name = f"invoice_{invoice_data['invoice_number']}_{invoice_data['invoice_date']}.{media_type.split('/')[-1]}"
            drive_link = self.drive_service.upload_file(file_data, file_name, media_type)
            if drive_link:
                invoice_data['file_path'] = drive_link
                print(f"✅ 檔案已上傳到 Google Drive: {drive_link}")
            else:
                print("❌ 檔案上傳失敗，file_path 將為 '上傳失敗'")
                invoice_data['file_path'] = '上傳失敗'

            df = pd.DataFrame([invoice_data])
            spreadsheet_url = self.spreadsheet_service.update_spreadsheet(df)
            print("✅ 成功儲存發票資料")
            return spreadsheet_url
        except Exception as e:
            print(f"儲存發票資料時發生錯誤: {e}")
            raise

if __name__ == "__main__":
    import sys
    import json
    import os

    async def main():
        """主執行函數，專門處理從命令列傳入的單一檔案。"""
        if len(sys.argv) < 2:
            print("錯誤：請提供一個檔案路徑作為命令列參數。")
            sys.exit(1)
            
        file_path = sys.argv[1]
        
        # 為了除錯，打印出路徑的原始表示
        print(f"收到的原始路徑參數 (raw): {repr(file_path)}")
        
        # 移除路徑前後可能存在的引號
        file_path = file_path.strip("'\"")
        print(f"清理引號後的路徑: {repr(file_path)}")

        if not os.path.exists(file_path):
            print(f"錯誤: os.path.exists 檢查失敗，找不到指定的檔案路徑 '{file_path}'")
            sys.exit(1)

        print(f"從命令列接收到單一檔案處理請求: {file_path}")
        
        try:
            processor = InvoiceProcessor()
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # 從副檔名判斷媒體類型
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.pdf':
                media_type = 'application/pdf'
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                media_type = f'image/{file_ext[1:]}'
            else:
                raise ValueError(f"不支援的檔案類型: {file_ext}")

            result, usage = await processor.process_invoice_from_data(file_data, media_type)
            
            # 以 JSON 格式打印結果，方便 mcp_server.py 捕獲和解析
            print("---辨識結果---")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("---使用量---")
            print(json.dumps(usage, ensure_ascii=False, indent=2))


        except FileNotFoundError:
            print(f"錯誤: 找不到檔案 {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"處理單一檔案時發生錯誤: {e}")
            sys.exit(1)

    # 執行主函數
    asyncio.run(main())
