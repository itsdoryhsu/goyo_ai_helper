# LINE Bot 行事曆整合功能

## 功能概述

LINE Bot 現已整合 Google Calendar 功能，提供以下服務：

### 🎯 主要功能

1. **Google 帳號綁定**
   - 安全的 OAuth 2.0 授權流程
   - 最小權限原則（僅讀取行事曆）
   - 支援一般 Google 帳號用戶

2. **行事曆選擇**
   - 可選擇要追蹤的特定行事曆
   - 支援多個行事曆同時追蹤
   - 靈活的行事曆管理

3. **每日自動提醒**
   - 每天早上 9:00 自動發送
   - 包含今天的行程
   - 本週即將到來的行程預覽

4. **手動查詢**
   - 隨時查看今天行程
   - 查看本週行程
   - 行事曆設定管理

## 🚀 使用方式

### 首次設定流程

1. **啟動功能**
   ```
   在 LINE 中輸入：行事曆
   ```

2. **綁定 Google 帳號**
   - 點選「綁定 Google 帳號」
   - 在瀏覽器中完成授權
   - 輸入「檢查綁定狀態」確認

3. **選擇追蹤的行事曆**
   - 點選「選擇行事曆」
   - 選擇要追蹤的行事曆（可多選）
   - 點選「完成選擇」

### 日常使用

- **今天行程**：查看今日所有行程
- **本週行程**：查看未來一週行程
- **行事曆設定**：管理綁定狀態和選擇的行事曆
- **解除綁定**：移除 Google 帳號綁定

## 🔧 技術實作

### 整合的服務

1. **Google OAuth 服務** (`services/google_auth_service/`)
   - OAuth 2.0 流程處理
   - 用戶憑證管理
   - 行事曆 API 存取

2. **排程器服務** (APScheduler)
   - 每日 9:00 自動提醒
   - 非同步執行
   - 容錯處理

3. **LINE Bot 整合**
   - 新增行事曆相關命令
   - Quick Reply 介面
   - Postback 事件處理

### 資料儲存

- **用戶綁定資料**：`data/user_bindings.sqlite`
- **OAuth 狀態**：暫存於資料庫
- **行事曆選擇**：JSON 格式儲存

## 🛡️ 安全與隱私

### 權限控制

- **最小必要權限**：
  - `https://www.googleapis.com/auth/calendar.readonly`
  - `https://www.googleapis.com/auth/userinfo.email`

### 資料保護

- 不儲存行事曆內容
- 僅儲存必要的 OAuth tokens
- 自動 token 刷新機制
- 支援用戶主動解除綁定

## 📋 部署需求

### 環境變數

```bash
# Google OAuth 設定
GOOGLE_AUTH_BASE_URL=http://localhost:8080  # 或你的正式域名

# LINE Bot 憑證（原有）
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret
```

### 依賴套件

主要新增的套件：
- `google-auth`
- `google-auth-oauthlib`
- `google-api-python-client`
- `apscheduler`

### Google Cloud Console 設定

1. **OAuth 同意畫面**
   - 用戶類型：外部
   - 應用程式名稱：goyo_line_ai
   - 必要範圍：calendar.readonly, userinfo.email

2. **OAuth 2.0 憑證**
   - 已授權的重新導向 URI：
     - `http://localhost:8080/oauth/callback`（開發）
     - `https://yourdomain.com/oauth/callback`（正式）

## 🔍 測試

使用測試腳本驗證整合：

```bash
python scripts/test_line_bot_calendar.py
```

## 📊 監控與記錄

- 完整的日誌記錄
- 錯誤處理和重試機制
- 用戶操作追蹤
- 每日提醒執行狀況

## 🎉 使用範例

### 每日提醒訊息格式

```
🌅 早安！今日行程提醒

📅 今天的行程：
⏰ 09:00 - 團隊會議 @ 會議室A
⏰ 14:30 - 客戶訪談

📋 本週即將到來的行程：
⏰ 明天 10:00 - 專案檢討
⏰ 09/25 15:00 - 設計評審

祝您有美好的一天！ 😊
```

這個整合讓用戶可以透過 LINE 輕鬆管理和查看他們的 Google Calendar 行程，提升日常工作效率。