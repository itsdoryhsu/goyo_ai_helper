#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google OAuth Web 路由
提供 OAuth 授權網頁和 callback 處理
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from .oauth_service import GoogleOAuthService

logger = logging.getLogger(__name__)


def create_oauth_routes(oauth_service: GoogleOAuthService) -> APIRouter:
    """建立 OAuth 相關路由"""

    router = APIRouter()

    @router.get("/oauth/auth")
    async def start_auth(user_id: str = Query(..., description="LINE User ID")):
        """啟動 OAuth 授權流程"""
        try:
            auth_url = oauth_service.start_oauth_flow(user_id)
            return RedirectResponse(url=auth_url)
        except Exception as e:
            logger.error(f"Failed to start OAuth: {e}")
            raise HTTPException(status_code=500, detail="啟動授權失敗")

    @router.get("/")
    async def root():
        """根路徑"""
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>goyo_line_ai OAuth Service</title></head>
        <body>
            <h1>goyo_line_ai OAuth Service</h1>
            <p>OAuth 服務正在運行</p>
            <p><a href="/oauth/auth?user_id=test_user">測試授權</a></p>
        </body>
        </html>
        """)

    @router.get("/oauth/callback")
    async def oauth_callback(
        code: str = Query(None, description="Authorization code"),
        state: str = Query(None, description="State parameter")
    ):
        """處理 OAuth callback"""

        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state parameter")

        logger.info(f"Processing OAuth callback with code: {code[:20]}... and state: {state}")
        success, message, line_user_id = oauth_service.handle_oauth_callback(code, state)
        logger.info(f"OAuth callback result: success={success}, message={message}, user_id={line_user_id}")

        if success:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>授權成功</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 400px;
                        width: 100%;
                    }}
                    .success-icon {{
                        font-size: 60px;
                        color: #4CAF50;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #333;
                        margin-bottom: 10px;
                        font-size: 24px;
                    }}
                    p {{
                        color: #666;
                        line-height: 1.6;
                        margin-bottom: 30px;
                    }}
                    .close-btn {{
                        background: #00C851;
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 25px;
                        font-size: 16px;
                        cursor: pointer;
                        transition: background 0.3s;
                    }}
                    .close-btn:hover {{
                        background: #00a041;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h1>綁定成功！</h1>
                    <p>{message}</p>
                    <p>您現在可以關閉此頁面，回到 LINE 使用行事曆功能。</p>
                    <button class="close-btn" onclick="window.close()">關閉頁面</button>
                </div>
                <script>
                    // 自動關閉頁面 (3秒後)
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                </script>
            </body>
            </html>
            """
        else:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>授權失敗</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 400px;
                        width: 100%;
                    }}
                    .error-icon {{
                        font-size: 60px;
                        color: #f44336;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #333;
                        margin-bottom: 10px;
                        font-size: 24px;
                    }}
                    p {{
                        color: #666;
                        line-height: 1.6;
                        margin-bottom: 30px;
                    }}
                    .close-btn {{
                        background: #f44336;
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 25px;
                        font-size: 16px;
                        cursor: pointer;
                        transition: background 0.3s;
                    }}
                    .close-btn:hover {{
                        background: #d32f2f;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error-icon">❌</div>
                    <h1>授權失敗</h1>
                    <p>{message}</p>
                    <p>請回到 LINE 重新嘗試綁定 Google 帳號。</p>
                    <button class="close-btn" onclick="window.close()">關閉頁面</button>
                </div>
                <script>
                    setTimeout(() => {{
                        window.close();
                    }}, 5000);
                </script>
            </body>
            </html>
            """

        return HTMLResponse(content=html_content)

    return router