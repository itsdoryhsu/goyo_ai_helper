# 1. 基底映像檔：使用與您 EC2 環境一致的 Python 3.10
FROM python:3.10-slim-bookworm

# 2. 設定環境變數，確保日誌即時輸出
ENV PYTHONUNBUFFERED=1

# 3. 在容器內設定工作目錄
WORKDIR /app

# 4. 安裝系統級依賴 (用於編譯某些 Python 套件)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# 5. 複製依賴需求檔案，以便利用 Docker 快取
COPY services/requirements_ec2.txt .

# 6. 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements_ec2.txt

# 7. 複製整個專案的程式碼到工作目錄
COPY . .

# 8. 設定容器啟動時的預設指令
CMD ["python3", "clients/line_bot/line_bot_v4_simple_client.py"]