#!/bin/bash

echo "正在啟動 Google OAuth 服務 (localhost:8080)..."

# 停止舊的程序
pkill -f "oauth_server.py"
pkill -f "line_bot_v5_clean.py"
pkill -f "ngrok http"

# 載入環境變數
if [ -f .env ]; then
  export $(sed -e 's/#.*$//' -e '/^$/d' .env | xargs)
fi

# 啟動 OAuth 服務 (背景執行)
echo "啟動 Google OAuth 服務於 localhost:8080..."
.venv_test/bin/python services/google_auth_service/oauth_server.py > logs/oauth_server.log 2>&1 &
OAUTH_PID=$!
echo "OAuth 服務已啟動，PID: $OAUTH_PID"

# 等待 OAuth 服務啟動
sleep 3

# 啟動 LINE Bot 和 ngrok
echo "啟動 LINE Bot 服務..."
./scripts/run_app.sh

echo "========================================================================"
echo "✅ 完整服務已啟動！"
echo ""
echo "🔐 Google OAuth 服務: http://localhost:8080"
echo "📱 LINE Bot 服務: 使用 ngrok URL"
echo ""
echo "現在可以測試 Google 帳號綁定功能！"
echo "========================================================================"