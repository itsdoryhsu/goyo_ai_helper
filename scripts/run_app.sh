#!/bin/bash

# 腳本：啟動 Line Bot 和 ngrok
#
# 這個腳本會：
# 1. 從 .env 檔案讀取 LINE_BOT_PORT。
# 2. 在背景啟動 Line Bot 伺服器。
# 3. 在背景啟動 ngrok 並將其連接到 Line Bot 的端口。
# 4. 抓取並顯示 ngrok 的公開 URL。
# 5. 提供一個函式來停止所有背景程序。

# 載入環境變數
if [ -f .env ]; then
  export $(sed -e 's/#.*$//' -e '/^$/d' .env | xargs)
fi

# 檢查 LINE_BOT_PORT 是否已設定
if [ -z "$LINE_BOT_PORT" ]; then
  echo "錯誤：請在 .env 檔案中設定 LINE_BOT_PORT。"
  exit 1
fi

# 停止舊的程序
echo "正在停止任何可能在運行的舊程序..."
pkill -f "line_bot_v4_simple_client.py"
pkill -f "line_bot_v5_clean.py"
pkill -f "ngrok http"
pkill -f "run_app.sh"

# 啟動 ngrok 先 (背景執行)
echo "正在背景啟動 ngrok..."
ngrok http $LINE_BOT_PORT > logs/ngrok.log 2>&1 &
NGROK_PID=$!
echo "ngrok 已啟動，PID: $NGROK_PID"

# 等待 ngrok 準備就緒
echo "等待 ngrok 啟動 (約 5 秒)..."
sleep 5

# 從 ngrok API 獲取公開 URL
PUBLIC_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"https[^"]*' | grep -o 'https://[^"]*')

if [ -z "$PUBLIC_URL" ]; then
  echo "錯誤：無法從 ngrok 獲取公開 URL。請檢查 ngrok 是否已正確安裝並授權。"
  echo "您可以查看 logs/ngrok.log 來獲取更多資訊。"
  # 清理已啟動的程序
  kill $NGROK_PID
  exit 1
fi

# 設定環境變數給 LINE Bot 使用
export GOOGLE_AUTH_BASE_URL="$PUBLIC_URL"

# 啟動 Line Bot 伺服器 v5 (背景執行)
echo "正在背景啟動 Line Bot v5 伺服器 (重構架構)..."
.venv_test/bin/python clients/line_bot/line_bot_v5_clean.py > logs/line_bot_v5_clean.log 2>&1 &
BOT_PID=$!
echo "Line Bot v5 已啟動，PID: $BOT_PID (Linus式乾淨架構)"


# 自動更新 Line Webhook URL
echo "正在自動更新 Line Webhook URL..."
UPDATE_RESPONSE=$(curl -s -X PUT \
     -H "Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"endpoint\":\"${PUBLIC_URL}/callback\"}" \
     https://api.line.me/v2/bot/channel/webhook/endpoint)

# 檢查 API 回應
if [[ "$UPDATE_RESPONSE" == "{}" ]]; then
  echo "✅ Line Webhook URL 已成功更新！"
else
  echo "❌ 更新 Line Webhook URL 失敗。"
  echo "API 回應: $UPDATE_RESPONSE"
  echo "請檢查您的 LINE_CHANNEL_ACCESS_TOKEN 是否正確。"
fi


# 顯示重要資訊
echo "========================================================================"
echo "✅ LINE Bot v5 系統已啟動！(Linus式重構架構)"
echo ""
echo "🚀 新架構特色："
echo "   • 900行 → 180行核心代碼"
echo "   • 模組化設計，統一接口"
echo "   • 狀態機管理，無全局狀態"
echo ""
echo "Line Bot v5 已在以下公開網址上運行："
echo "$PUBLIC_URL/callback"
echo ""
echo "📋 健康檢查端點: $PUBLIC_URL/health"
echo "📝 日誌檔案: /logs/line_bot_v5_clean.log"
echo "========================================================================"
echo ""
echo "若要停止所有服務，請執行以下命令："
echo "pkill -f 'line_bot_v5_clean.py' && pkill -f 'ngrok http $LINE_BOT_PORT'"
echo ""
