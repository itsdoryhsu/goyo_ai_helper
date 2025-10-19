#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google OAuth 獨立服務器
運行在 localhost:8080，專門處理 Google OAuth 授權
遵循 Linus 設計哲學：單一職責，模組化設計
"""

import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# 添加專案根目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from services.google_auth_service.services.oauth_service import GoogleOAuthService
from services.google_auth_service.services.web_routes import create_oauth_routes

app = FastAPI(title="Google OAuth Service")

# 初始化 OAuth 服務
client_secrets_path = 'config/gmail_accounts/itsdoryhsu/client_secret_865894595003-1tp7pt3rdn0ku3cb1sd8dac9gjdt8qu3.apps.googleusercontent.com.json'
oauth_service = GoogleOAuthService(client_secrets_path, 'http://localhost:8080')
oauth_router = create_oauth_routes(oauth_service)

# 將 OAuth 路由包含到應用
app.include_router(oauth_router)

@app.get("/")
async def root():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google OAuth Service</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
            .status { color: #00C851; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Google OAuth Service</h1>
            <p class="status">✅ 服務正在運行於 localhost:8080</p>
            <p>此服務專門處理 Google 帳號授權，遵循 Linus 設計哲學：</p>
            <ul>
                <li>單一職責：只處理 OAuth 授權</li>
                <li>無特殊情況：統一的授權流程</li>
                <li>簡單可靠：最少的複雜度</li>
            </ul>
            <hr>
            <p><strong>可用端點：</strong></p>
            <ul>
                <li><code>GET /oauth/auth?user_id=USER_ID</code> - 啟動授權</li>
                <li><code>GET /oauth/callback</code> - 授權回調</li>
            </ul>
        </div>
    </body>
    </html>
    """)

def start_server():
    """啟動 OAuth 服務器"""
    print("🔐 啟動 Google OAuth 服務於 localhost:8080...")
    print("📋 遵循 Linus 哲學：簡單、可靠、無特殊情況")
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    start_server()