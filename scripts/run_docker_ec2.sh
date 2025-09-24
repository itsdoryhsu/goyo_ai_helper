#!/bin/bash

# 腳本：在 EC2 上使用 Docker 和 Ngrok 啟動 Line Bot
#
# 這個腳本會：
# 1. 從 .env 檔案讀取環境變數。
# 2. 使用 docker-compose 啟動應用程式容器。
# 3. 在背景啟動 ngrok 並將其連接到應用程式的端口。
# 4. 抓取 ngrok 的公開 URL 並自動更新 Line Webhook。

# 載入環境變數
if [ -f .env ]; then
  export $(sed -e 's/#.*$//' -e '/^$/d' .env | xargs)
fi

# 檢查必要的變數
if [ -z "$LINE_BOT_PORT" ] || [ -z "$LINE_CHANNEL_ACCESS_TOKEN" ]; then
  echo "錯誤：請確保 .env 檔案中已設定 LINE_BOT_PORT 和 LINE_CHANNEL_ACCESS_TOKEN。"
  exit 1
fi

# 停止舊的程序
echo "正在停止任何可能在運行的舊程序..."
sudo docker-compose down
pkill -f "ngrok http"

# 啟動 Docker 容器 (背景執行)
echo "正在背景啟動 Docker 容器..."
sudo docker-compose up --build -d

# 等待應用程式啟動
echo "等待應用程式啟動 (約 10 秒)..."
sleep 10

# 設定 ngrok Authtoken (如果有的話)
if [ -n "$NGROK_AUTHTOKEN" ]; then
  echo "正在設定 ngrok Authtoken..."
  ngrok config add-authtoken $NGROK_AUTHTOKEN
fi

# 建立日誌資料夾 (如果不存在)
mkdir -p logs

# 啟動 ngrok (背景執行)
echo "正在背景啟動 ngrok..."
ngrok http $LINE_BOT_PORT > logs/ngrok.log 2>&1 &
sleep 5 # 等待 ngrok 準備就緒

# 從 ngrok API 獲取公開 URL
PUBLIC_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"https[^"]*' | grep -o 'https://[^"]*')

if [ -z "$PUBLIC_URL" ]; then
  echo "錯誤：無法從 ngrok 獲取公開 URL。請檢查 ngrok 是否已正確安裝並授權。"
  echo "您可以查看 logs/ngrok.log 來獲取更多資訊。"
  exit 1
fi

# 自動更新 Line Webhook URL
echo "正在自動更新 Line Webhook URL..."
UPDATE_RESPONSE=$(curl -s -X PUT \
     -H "Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"endpoint\":\"${PUBLIC_URL}/callback\"}" \
     https://api.line.me/v2/bot/channel/webhook/endpoint)

if [[ "$UPDATE_RESPONSE" == "{}" ]]; then
  echo "✅ Line Webhook URL 已成功更新！"
else
  echo "❌ 更新 Line Webhook URL 失敗。"
  echo "API 回應: $UPDATE_RESPONSE"
fi

# 顯示重要資訊
echo "========================================================================"
echo "✅ 系統已啟動！"
echo "Line Bot Webhook URL: $PUBLIC_URL/callback"
echo "服務正在背景運行中。日誌檔案位於 /logs 資料夾。"
echo "使用 'docker-compose logs -f' 來查看應用程式日誌。"
echo "========================================================================"