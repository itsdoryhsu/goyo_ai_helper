# Google OAuth 一般用戶授權設定指南

## 概述
一般用戶只需要有 Google 帳號就能授權使用行事曆功能，不需要 GCP 帳號。

## Google Cloud Console 設定

### 1. OAuth 同意畫面設定（重要！）

前往 Google Cloud Console → API 和服務 → OAuth 同意畫面

#### 用戶類型選擇：
- **內部**：只有你組織內的用戶可以使用（需要 Google Workspace）
- **外部**：任何有 Google 帳號的用戶都可以使用 ✅

選擇「外部」！

#### 應用程式資訊：
- **應用程式名稱**：goyo_line_ai
- **使用者支援電子郵件**：你的 email
- **應用程式標誌**：可選
- **開發人員聯絡資訊**：你的 email

#### 範圍（Scopes）：
新增以下**最小必要**範圍：
- `https://www.googleapis.com/auth/calendar.readonly` - 只讀取行事曆事件
- `https://www.googleapis.com/auth/userinfo.email` - 取得用戶 email 用於識別

**已移除過度權限：**
- ❌ `calendar.readonly` - 權限過於廣泛
- ❌ `userinfo.profile` - 不需要用戶姓名等資料

#### 測試使用者（開發階段）：
如果應用程式還在「測試」狀態，需要新增測試使用者的 email 地址。

### 2. 憑證設定

在「憑證」頁面：

#### 編輯 OAuth 2.0 用戶端 ID：
- **已授權的重新導向 URI**：
  - `http://localhost:8080/oauth/callback`
  - `http://127.0.0.1:8080/oauth/callback`
  - 生產環境：`https://yourdomain.com/oauth/callback`

### 3. API 啟用

確保以下 API 已啟用：
- Google Calendar API
- Google People API（用於取得用戶資訊）

## 用戶授權流程

### 對一般用戶的體驗：

1. **點擊綁定**：用戶在 LINE 中點擊「綁定 Google 帳號」
2. **開啟瀏覽器**：LINE 開啟 Google 授權頁面
3. **登入 Google**：用戶用自己的 Gmail 帳號登入
4. **授權確認**：Google 顯示：
   ```
   goyo_line_ai 想要存取您的 Google 帳戶

   此應用程式將能夠：
   ✓ 查看您的行事曆活動
   ✓ 查看您的電子郵件地址

   [允許] [拒絕]
   ```
5. **完成綁定**：用戶點擊「允許」，返回成功頁面

## 安全考量

### 最小權限原則：
- 只要求必要的權限（行事曆讀取）
- 不要求修改或刪除權限

### 資料保護：
- 不儲存用戶的行事曆資料
- 只儲存必要的 token 用於 API 呼叫
- Token 有過期機制

### 透明度：
- 清楚說明為什麼需要這些權限
- 提供隱私政策連結

## 測試用戶設定

### 開發階段：
1. 前往 OAuth 同意畫面
2. 在「測試使用者」區域
3. 新增要測試的 Gmail 地址
4. 只有這些用戶可以進行授權

### 發布後：
- 應用程式經過 Google 審核後
- 任何 Google 用戶都可以授權使用

## 限制和注意事項

### 測試階段限制：
- 最多 100 個測試用戶
- Token 7天後過期（發布後無此限制）

### 發布要求：
- 如要讓所有用戶使用，需要通過 Google 的應用程式審核
- 需要提供隱私政策
- 需要說明為什麼需要這些權限

## 本機測試

即使在開發階段，一般用戶也可以測試：
1. 將測試用戶的 email 加入測試清單
2. 該用戶就可以完整體驗授權流程
3. 無需任何 GCP 知識