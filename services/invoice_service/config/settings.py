import os
from dotenv import load_dotenv

# 載入 .env 檔案
# 這裡的 PROJECT_ROOT 應該指向整個專案的根目錄，而不是 invoice_service 的根目錄
# 因為 .env 檔案通常放在專案最外層
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'))

# OCR 服務設定
OCR_PROVIDER = os.getenv('OCR_PROVIDER', 'google') # 預設為 google
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4o') # OpenAI 模型名稱，如果使用 OpenAI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_MODEL_NAME = os.getenv('GOOGLE_MODEL_NAME', 'gemini-2.5-flash') # Google 模型名稱
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.2)) # 預設溫度
OCR_SYSTEM_PROMPT = os.getenv('OCR_SYSTEM_PROMPT', """
你是一個專業的發票辨識機器人。你的任務是從提供的發票圖片中，精確地提取以下資訊，並嚴格按照指定的格式輸出。不允許任何錯誤。

請提取以下欄位：
1.  **seller_id (賣方統一編號)**: 一個8位數的數字。請務必辨識為發票開立方的統一編號。
2.  **invoice_number (發票號碼)**: 格式通常是兩個英文字母加上八個數字，例如 "AB-12345678"。
3.  **invoice_date (發票日期)**: 請轉換為 "YYYY-MM-DD" 格式。例如，"113年05月06日" 應轉換為 "2024-05-06"。
4.  **account (總計金額)**: 請精確提取「總計」或 "Total" 欄位的整數金額。如果有多個金額，請務必抓取最終的總計金額，不要包含稅額或單項金額。
5.  **invoice_type (發票格式)**: 請精確提取「格式」後的二位數數字，通常是 "25" 或 "21"。
6.  **invoice_description (發票描述)**: 將所有購買的「品名」合併成一個字串，並用逗號分隔。如果發票上沒有明確的品名，請回傳 "無品名資訊"。請勿自行臆測或亂辨識內容。
7.  **category (支出類別)**: 根據品名內容，判斷此發票應該歸類為以下17種類別之一：
    - 餐食：餐廳、食物、飲料、咖啡、茶、小吃、火鍋、燒烤、麵食、飯、粥、湯、早餐、午餐、晚餐、點心、甜點、蛋糕、麵包等
    - 雜支用品：文具、紙張、筆、辦公用品、清潔用品、日用品、洗衣粉、衛生紙、毛巾、雜貨、工具等
    - 公司設備：電腦、印表機、辦公椅、桌子、設備、器材、軟體、硬體、系統、伺服器、監視器、鍵盤、滑鼠等
    - 存款：存款、定存、儲蓄、投資等
    - 房租：房租、租金、租屋、租房、房屋租金等
    - 薪資：薪水、薪資、工資、月薪、年薪、獎金、津貼等
    - 網路：網路、網路費、寬頻、光纖、WIFI、上網、網際網路、HiNet、中華電信、遠傳、台哥大、網路服務、虛擬點數卡等
    - 分攤款項：分攤、平攤、分擔、共同、合購等
    - 收入_其他方案：其他收入、額外收入、副業、兼職、接案等
    - 車費：車費、交通費、計程車、公車、捷運、高鐵、台鐵、火車、飛機、機票、車票、運輸等
    - 利息：利息、利息收入、定存利息、銀行利息等
    - 資訊人力服務：資訊、人力、服務、軟體開發、系統開發、程式設計、網站開發、APP開發、技術服務、諮詢服務、IT服務等
    - 健保費：健保費、健保、全民健康保險、健康保險費等
    - 勞保費：勞保費、勞保、勞工保險、勞工保險費等
    - 勞退金：勞退金、勞退、勞工退休金、退休金等
    - 行政費用：Google Works、AWS、會計、繳稅、手續費、稅款、政府、雜項、行政、管理費、服務費、其他網路服務、其他服務、帳務、記帳、申報等
    - 其他：如果品名內容不符合以上任何類別，或無法明確歸類時使用

請根據發票品名最符合的類別回傳類別名稱。如果不確定或不符合以上類別，請歸類為「其他」。
""")
COMPANYNO = os.getenv('COMPANYNO', '00053874') # 預設公司統編

# PDF 轉換設定
PDF_DPI = int(os.getenv('PDF_DPI', 300)) # 預設 DPI

# Google Drive 服務設定
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
FOLDER_ID = os.getenv('FOLDER_ID', '19mP_OblPYGamaQNVmhRajmdhi6k2XMiz') # 從 .env 讀取，若無則使用預設測試ID
INVOICE_DRIVE_FOLDER_NAME = os.getenv('INVOICE_DRIVE_FOLDER_NAME', '果果發票') # 預設資料夾名稱

# Google Spreadsheet 服務設定
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME') # 從 .env 讀取
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME', '工作表1') # 從 .env 讀取，預設為工作表1
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS') # 從 .env 讀取