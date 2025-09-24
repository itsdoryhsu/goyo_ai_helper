#!/bin/bash
# 修復虛擬環境

echo "=== 修復虛擬環境 ==="
echo

# 退出當前虛擬環境
deactivate 2>/dev/null || true

# 刪除舊的虛擬環境
echo "刪除舊的虛擬環境..."
rm -rf .venv_local_test

# 建立新的虛擬環境
echo "建立新的虛擬環境..."
python3 -m venv .venv_local_test

# 激活虛擬環境
echo "激活虛擬環境..."
source .venv_local_test/bin/activate

# 檢查 Python 和 pip
echo
echo "=== 檢查環境 ==="
echo "Python 版本: $(python --version)"
echo "Python 路徑: $(which python)"
echo "pip 版本: $(pip --version)"
echo "pip 路徑: $(which pip)"

# 升級 pip
echo
echo "升級 pip..."
pip install --upgrade pip

# 安裝套件
echo
echo "=== 安裝必要套件 ==="
pip install google-auth google-auth-oauthlib google-api-python-client fastapi uvicorn python-dotenv

echo
echo "=== 檢查已安裝套件 ==="
pip list | grep -E "(google|fastapi|uvicorn|dotenv)"

echo
echo "=== 完成 ==="
echo "請執行以下命令激活虛擬環境："
echo "source .venv_local_test/bin/activate"
echo
echo "然後測試："
echo "python scripts/setup_google_oauth_test.py"