# AI 財稅助理

本專案是一個整合式的 AI 財稅應用，結合了財務稅法問答 (RAG) 和發票 OCR 辨識功能。專案已從微服務架構重構為更簡潔的單體應用程式架構，方便部署與維護。

## 功能

*   **財務稅法問答:** 使用 RAG (Retrieval-Augmented Generation) 技術，提供基於專業知識庫的問答能力。
*   **發票 OCR:** 自動辨識並提取發票圖片中的重要資訊。
*   **Line Bot 整合:** 透過 Line Bot 提供服務，方便使用者互動。
*   **Web 操作介面:** 提供一個基於 Streamlit 的網頁介面，方便進行測試與操作。

## 資料夾結構概覽

-   `/_archive/`: 存放舊的、不再使用的架構原型。
-   `/_mcp_archive/`: 封存舊的 MCP (Model Context Protocol) 微服務架構相關檔案。
-   `/clients/`: 存放與使用者互動的客戶端應用。
    -   `line_bot/`: Line Bot 相關程式碼。
-   `/services/`: 存放核心後端服務模組。
    -   `qa_service/`: 財務稅法問答 (RAG) 模組。
    -   `invoice_service/`: 發票 OCR 辨識與處理模組。
-   `/config/`: 統一存放所有設定檔與憑證。
-   `/scripts/`: 存放各類輔助腳本 (如：憑證生成)。
-   `/data/`: 存放知識庫來源文件和向量資料庫。
-   `/logs/`: 存放所有服務的日誌檔案。
-   `streamlit_app.py`: 應用的 Web 操作介面。

## 運行指南

請依照以下步驟來啟動系統。

### 1. 安裝/更新依賴

首先，請確保您已安裝所有必要的 Python 套件：

```bash
pip install -r services/requirement.txt
```

### 2. 準備環境變數與憑證

#### a. `.env` 文件

請複製 `.env.example` 為 `.env`，並填入您的個人金鑰與憑證：

```
# OpenAI API Key (用於QA服務和發票OCR)
OPENAI_API_KEY="sk-..."
GOOGLE_API_KEY="..."

# Line Bot 憑證
LINE_CHANNEL_ACCESS_TOKEN="..."
LINE_CHANNEL_SECRET="..."

# Line Notify Token (如果需要通知功能)
LINE_NOTIFY_TOKEN="..."
```

#### b. 憑證檔案

所有憑證檔案都統一存放在 `/config` 目錄下：

1.  **Google Service Account (用於發票服務)**: 請將您的 `sonic-wonder-....json` 憑證檔案放置在 `/config` 目錄下。
2.  **Gmail API (若需使用通知功能)**: 請遵循 `scripts/generate_gmail_tokens.py` 中的指示生成 `token.json`，並將其與 `credentials.json` 放置在 `/config/gmail_accounts/your_account_name/` 目錄下。

### 3. 啟動應用

您可以根據需求，選擇啟動 Web 介面或 Line Bot。

#### 方式一：啟動 Streamlit Web 介面 (建議用於測試)

在專案根目錄執行以下命令：

```bash
streamlit run streamlit_app.py
```

啟動後，您可以透過瀏覽器訪問指定的網址，直接與 QA 和 Invoice OCR 功能互動。

#### 方式二：啟動 Line Bot (推薦)

我們提供了一個自動化腳本，可以一次性啟動 Line Bot 和 ngrok，並自動更新 Webhook URL。

在專案根目錄執行以下命令：

```bash
./scripts/run_app.sh
```

啟動後，您的 Line Bot 將會上線，並可以開始接收與回覆使用者的訊息。

## 如何使用

-   **透過 Web 介面:** 直接在 Streamlit 頁面上傳發票圖片或輸入問題，即可看到結果。
-   **透過 Line Bot:** 將發票圖片傳送給 Line Bot，它會自動進行 OCR 辨識；輸入文字問題，它會使用 QA 系統進行回覆。