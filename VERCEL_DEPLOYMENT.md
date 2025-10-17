# Vercel 部署指南

## 🎯 解決Google帳號綁定問題

你的「無法選擇Google帳號」問題是因為OAuth redirect URI不匹配。Vercel提供固定網址，完美解決此問題。

## 📋 部署步驟

### 1. 準備Vercel帳號
- 前往 [vercel.com](https://vercel.com)
- 使用GitHub帳號登入（免費）

### 2. 部署專案
```bash
# 安裝 Vercel CLI（可選）
npm i -g vercel

# 或直接在網站上導入GitHub repo
```

### 3. 設定環境變數
在Vercel專案設定中，添加以下環境變數（參考 `.env.example.vercel`）：

**必須設定**：
- `LINE_CHANNEL_ID`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `GOOGLE_AUTH_BASE_URL` = `https://你的應用名稱.vercel.app`

### 4. 更新Google OAuth設定

**重要**：部署後，你會得到固定網址如 `https://goyo-finance-bot.vercel.app`

#### 更新Google Cloud Console：
1. 前往 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. 選擇專案 `goyo-line-ai`
3. 編輯OAuth 2.0客戶端ID
4. 在「授權重新導向URI」中新增：
   ```
   https://你的應用名稱.vercel.app/oauth/callback
   ```

#### 更新client_secret.json：
```json
{
  "web": {
    "redirect_uris": [
      "https://你的應用名稱.vercel.app/oauth/callback"
    ]
  }
}
```

### 5. 上傳Google憑證文件
Vercel需要你的Google service account文件：
- 將 `config/gmail_accounts/itsdoryhsu/client_secret_*.json`
- 上傳到Vercel專案的檔案系統中

### 6. 更新LINE Webhook URL
```
https://你的應用名稱.vercel.app/callback
```

## ✅ 驗證部署

部署成功後：
1. 訪問 `https://你的應用名稱.vercel.app/health`
2. 測試LINE Bot綁定Google帳號功能
3. **現在應該可以正常選擇Google帳號了！**

## 🚀 優勢

- ✅ **固定網址**：解決OAuth redirect問題
- ✅ **免費**：個人使用完全免費
- ✅ **自動HTTPS**：安全連接
- ✅ **Git集成**：推送代碼自動部署
- ✅ **環境變數管理**：安全的配置管理

## 🔧 故障排除

如果仍無法選擇Google帳號：
1. 檢查Vercel環境變數是否正確設定
2. 確認Google OAuth redirect URI包含正確的Vercel網址
3. 檢查瀏覽器開發者工具的網路請求錯誤