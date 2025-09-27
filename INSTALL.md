# Goyo AI Helper - 安裝指南

## Linus 風格：簡單、直接、無廢話

### 🎯 快速安裝（推薦）

```bash
# 1. 創建虛擬環境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate     # Windows

# 2. 安裝所有依賴
pip install -r requirements.txt

# 3. 配置環境變數
cp .env.example .env
# 編輯 .env 文件，填入你的 API keys

# 4. 啟動服務
python clients/line_bot/line_bot_v5_clean.py
```

### 🔧 分服務安裝（開發用）

如果你只想使用特定服務：

```bash
# Model Service（AI 核心）
pip install -r services/model_service/requirements.txt

# QA Service（問答服務）
pip install -r services/qa_service/requirements.txt

# Finance Service（財務分析）
pip install -r services/finance_analysis_service/requirements.txt

# Invoice Service（發票處理）
pip install -r services/invoice_service/requirements.txt
```

### 📋 依賴架構

```
根目錄 requirements.txt
├── 合併所有服務依賴
├── LINE Bot 核心依賴
└── 部署友好（一次安裝全部）

服務獨立 requirements.txt
├── services/model_service/requirements.txt      # 純淨 AI 抽象層
├── services/qa_service/requirements.txt         # 問答 + 向量檢索
├── services/finance_analysis_service/requirements.txt  # 財務分析
└── services/invoice_service/requirements.txt    # 發票 OCR
```

### ⚡ 環境變數配置

```bash
# === 必填 ===
OPENROUTER_API_KEY="your_key_here"    # 主要 AI 提供商
LINE_CHANNEL_ACCESS_TOKEN="..."       # LINE Bot
LINE_CHANNEL_SECRET="..."

# === 可選（備援）===
OPENAI_API_KEY="your_key_here"        # OpenAI 備援
GOOGLE_API_KEY="your_key_here"        # Gemini 備援

# === 服務配置（可選）===
QA_SERVICE_MODEL="x-ai/grok-4-fast:free"
FINANCE_SERVICE_MODEL="x-ai/grok-4-fast:free"
OCR_SERVICE_MODEL="gemini-2.5-flash"
```

### 🚀 驗證安裝

```bash
# 檢查服務啟動
python clients/line_bot/line_bot_v5_clean.py

# 預期日誌：
# ✅ QA服務v2初始化成功
# ✅ 發票處理服務初始化成功
# ✅ SimpleFinanceService 初始化成功
# ✅ 財務分析服務初始化成功
# ✅ LINE Bot v5 初始化完成
```

### 🐧 Linus 語錄

> "This is what happens when you don't think about your dependencies. It becomes a mess."

現在的架構遵循：
- **一個服務，一個 requirements**
- **明確的依賴關係**
- **無隱藏的傳遞依賴**
- **可預測的安裝過程**

沒有更多的混亂文件，沒有"神秘"的依賴。就是這麼簡單。