#!/bin/bash
# Google Auth 測試環境安裝腳本

echo "=== Google Auth 測試環境安裝 ==="
echo

# 檢查是否在虛擬環境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 檢測到虛擬環境: $VIRTUAL_ENV"
    echo "檢查 pip 是否可用..."

    # 檢查 pip 是否存在
    if ! command -v pip &> /dev/null; then
        echo "❌ pip 不可用，嘗試重新建立虛擬環境..."
        deactivate 2>/dev/null || true
        rm -rf .venv_local_test
        python3 -m venv .venv_local_test
        source .venv_local_test/bin/activate
        echo "✅ 重新建立並激活虛擬環境"
    else
        echo "✅ pip 可用"
    fi
else
    echo "⚠️  未檢測到虛擬環境，建立新的虛擬環境..."
    rm -rf .venv_local_test
    python3 -m venv .venv_local_test
    source .venv_local_test/bin/activate
    echo "✅ 建立並激活新的虛擬環境"
fi

echo
echo "=== 檢查 Python 和 pip 版本 ==="
echo "Python 版本: $(python --version)"
echo "Python 路徑: $(which python)"
echo "pip 版本: $(pip --version)"
echo "pip 路徑: $(which pip)"

echo
echo "=== 安裝 Python 套件 ==="

# 升級 pip
echo "升級 pip..."
python -m pip install --upgrade pip

# 安裝必要套件
echo "安裝 Google API 套件..."
python -m pip install google-auth google-auth-oauthlib google-api-python-client

echo "安裝 Web 框架套件..."
python -m pip install fastapi uvicorn

echo "安裝其他必要套件..."
python -m pip install python-dotenv

echo
echo "=== 安裝完成 ==="
echo "已安裝的套件:"
python -m pip list | grep -E "(google|fastapi|uvicorn|dotenv)"

echo
echo "=== 下一步 ==="
echo "1. 確保虛擬環境已激活:"
echo "   source .venv_local_test/bin/activate"
echo
echo "2. 執行環境檢查:"
echo "   python scripts/setup_google_oauth_test.py"
echo
echo "3. 如果檢查通過，啟動測試:"
echo "   python scripts/test_google_auth_local.py"