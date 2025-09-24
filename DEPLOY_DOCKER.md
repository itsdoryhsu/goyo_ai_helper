# EC2 Docker 部署指南

本指南將引導您如何在一個全新的 AWS EC2 實例 (Ubuntu) 上，使用 Docker 和 Docker Compose 來部署此應用程式。

## 0. 前提條件

1.  一個 AWS EC2 實例 (建議使用 Ubuntu 22.04 LTS)。
2.  EC2 實例已綁定一個彈性 IP (Elastic IP)，以獲得固定的公開 IP 位址。
3.  您的本機已安裝 `git`。

## 1. 設定 EC2 安全組 (Security Group)

在您的 EC2 管理控制台中，找到您的實例所使用的安全組，並確保以下入站規則 (Inbound Rules) 已被設定：

| 類型      | 協定 | 連接埠範圍 | 來源        | 描述                       |
| :-------- | :--- | :------- | :---------- | :------------------------- |
| HTTP      | TCP  | 80       | `0.0.0.0/0` | 允許來自任何地方的 HTTP 流量 |
| HTTPS     | TCP  | 443      | `0.0.0.0/0` | (可選) 如果您未來要設定 SSL |
| SSH       | TCP  | 22       | 您的 IP     | 限制只有您能透過 SSH 連線  |

## 2. 連線到 EC2 並安裝 Docker

首先，使用您的金鑰連線到 EC2 實例：

```bash
ssh -i "your-key.pem" ubuntu@YOUR_EC2_IP
```

連線成功後，執行以下指令來安裝 Docker 和 Docker Compose：

```bash
# 更新套件列表
sudo apt-get update

# 安裝 Docker
sudo apt-get install -y docker.io

# 將目前使用者加入 docker 群組，這樣就不需要每次都加 sudo
sudo usermod -aG docker ${USER}

# 安裝 Docker Compose
sudo apt-get install -y docker-compose

# 驗證安裝
docker --version
docker-compose --version

# 重新登入或執行 newgrp docker 以讓群組變更生效
echo "請重新登入您的 SSH 連線，或執行 'newgrp docker' 來讓權限生效。"
newgrp docker
```

## 3. 複製專案程式碼

從您的 Git 儲存庫複製最新的程式碼：

```bash
git clone YOUR_GIT_REPOSITORY_URL
cd YOUR_PROJECT_DIRECTORY
```

## 4. 準備環境變數與憑證

這是部署中最關鍵的一步。

### a. 建立 `.env` 檔案

複製範例檔案，並填入您在 AWS 生產環境中要使用的金鑰：

```bash
cp .env.example .env
nano .env
```

**重要：** 請確保檔案中的 `LINE_BOT_PORT` 仍然是 `8013`，因為我們的 Nginx 設定依賴這個端口。

### b. 上傳 `config` 資料夾

您需要將包含所有憑證的 `config` 資料夾從您的本機安全地傳輸到 EC2 實例的專案目錄中。您可以使用 `scp` (Secure Copy) 指令。

在**您的本機**上執行以下指令：

```bash
# -r 表示遞迴複製整個資料夾
scp -r -i "your-key.pem" ./config ubuntu@YOUR_EC2_IP:~/YOUR_PROJECT_DIRECTORY/
```

## 5. 啟動應用程式

現在所有東西都已準備就緒，您只需要一個指令就可以啟動所有服務：

```bash
# -d 表示在背景 (detached mode) 執行
docker-compose up --build -d
```

*   `--build`：這個旗標會告訴 Docker Compose 在啟動前先根據 `Dockerfile` 建置您的應用程式映像檔。
*   `-d`：讓容器在背景運行。

## 6. 驗證服務狀態

您可以透過以下指令來檢查容器是否正常運行：

```bash
# 查看正在運行的容器
docker-compose ps

# 查看應用程式的即時日誌
docker-compose logs -f app

# 查看 Nginx 的即時日誌
docker-compose logs -f nginx
```

如果一切順利，您應該會看到 `finance-app` 和 `nginx-proxy` 兩個容器都處於 `Up` 的狀態。

## 7. 更新 Line Bot Webhook

最後一步，您需要將 Line Bot 的 Webhook URL 更新為您 EC2 的固定 IP 位址。

1.  登入 [Line Developers Console](https://developers.line.biz/console/)。
2.  選擇您的 Provider 和 Channel。
3.  進入 "Messaging API" 分頁。
4.  在 "Webhook URL" 欄位，點擊 "Edit"。
5.  輸入 `http://YOUR_EC2_IP/callback`。
6.  點擊 "Update"。
7.  啟用 "Use webhook"。

完成後，您的 Line Bot 就正式在 EC2 上線了！

## 常用 Docker Compose 指令

*   **停止服務**: `docker-compose down`
*   **重新啟動服務**: `docker-compose restart`
*   **查看所有日誌**: `docker-compose logs`
*   **更新並重啟服務 (例如您更新了程式碼後)**: `git pull && docker-compose up --build -d`