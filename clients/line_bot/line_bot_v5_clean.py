#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LINE Bot v5 - 重構版
Linus式乾淨架構：消除特殊情況，簡化數據結構，統一接口

架構原則：
1. 單一職責：每個類只做一件事
2. 依賴注入：無全局狀態
3. 統一接口：消除重複代碼
4. 狀態機：取代複雜的if/elif鏈
"""

# 抑制SSL警告
import warnings
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings('ignore', category=NotOpenSSLWarning)
except ImportError:
    pass

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 將專案根目錄添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# LINE Bot SDK v3
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, AsyncApiClient
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, ImageMessageContent,
    FileMessageContent, PostbackEvent
)

# 重構後的模組
from clients.line_bot.models.user_session import SessionManager, SessionState
from clients.line_bot.services.service_registry import ServiceRegistry
from clients.line_bot.services.line_client import LineClient
from clients.line_bot.handlers.base_handler import HandlerResponse

# --- 設定與初始化 ---
# 載入環境變數 - 強制覆蓋系統環境變數
load_dotenv(override=True)

# 設定日誌
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "line_bot_v5_clean.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# LINE Bot 憑證
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.error("LINE Bot 憑證未設定！")
    exit(1)

# FastAPI 和 LINE Bot 初始化
app = FastAPI(title="財務稅法顧問 LINE Bot v5")
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 核心服務實例 - 依賴注入，無全局狀態
session_manager: SessionManager = None
service_registry: ServiceRegistry = None
line_client: LineClient = None

class LineBotController:
    """LINE Bot 控制器 - 統一處理所有訊息"""

    def __init__(self, session_manager: SessionManager, service_registry: ServiceRegistry, line_client: LineClient):
        self.session_manager = session_manager
        self.service_registry = service_registry
        self.line_client = line_client

    async def handle_text_message(self, event: MessageEvent):
        """處理文字訊息 - 40行代替300行"""
        user_id = event.source.user_id
        text = event.message.text.strip()
        session = self.session_manager.get_session(user_id)

        logger.info(f"用戶 {user_id} 發送訊息: {text} (狀態: {session.state.value})")

        try:
            # 退出命令
            if text in ["取消", "離開", "返回主選單"]:
                session.exit_service()
                await self.line_client.reply_main_menu(event.reply_token)
                return

            # 主選單服務選擇
            if self.service_registry.is_valid_service(text):
                handler = self.service_registry.get_handler(text)
                service_state = self.service_registry.get_service_state(text)

                session.enter_service(text, service_state)
                response = await handler.enter_mode(user_id)

                await self._send_handler_response(event.reply_token, user_id, response)
                return

            # 在服務模式中處理訊息
            if session.state != SessionState.IDLE and session.current_handler:
                handler = self.service_registry.get_handler(session.current_handler)

                if handler:
                    # 預先發送loading動畫
                    await self.line_client.send_loading_animation(user_id)
                    response = await handler.handle_message(user_id, text)
                    await self._send_handler_response(event.reply_token, user_id, response)
                    return

            # 預設：回到主選單
            await self.line_client.reply_main_menu(event.reply_token)

        except Exception as e:
            logger.error(f"處理文字訊息失敗: {e}")
            await self.line_client.reply_text(
                event.reply_token,
                "抱歉，處理您的請求時發生錯誤，請稍後再試。"
            )

    async def handle_file_message(self, event: MessageEvent):
        """處理文件訊息 - 統一接口"""
        user_id = event.source.user_id
        session = self.session_manager.get_session(user_id)

        # 只有在照片記帳模式才處理文件
        if session.state != SessionState.INVOICE_MODE:
            await self.line_client.reply_text(
                event.reply_token,
                "請先選擇照片記帳功能再上傳檔案。"
            )
            return

        try:
            # 獲取文件數據
            from linebot.v3.messaging import AsyncMessagingApiBlob
            blob_api = AsyncMessagingApiBlob(self.line_client.api_client)
            file_data = await blob_api.get_message_content(message_id=event.message.id)

            # 判斷媒體類型
            media_type = 'image/jpeg' if isinstance(event.message, ImageMessageContent) else 'application/pdf'

            # 預先發送loading動畫 (文件處理通常需要較長時間)
            await self.line_client.send_loading_animation(user_id)

            # 處理文件
            handler = self.service_registry.get_handler(session.current_handler)
            response = await handler.handle_file(user_id, file_data, media_type)

            await self._send_handler_response(event.reply_token, user_id, response)

        except Exception as e:
            logger.error(f"處理文件失敗: {e}")
            await self.line_client.reply_text(
                event.reply_token,
                "抱歉，處理文件時發生錯誤。"
            )

    async def handle_postback_event(self, event: PostbackEvent):
        """處理postback事件 - 確認卡片按鈕"""
        user_id = event.source.user_id
        data = event.postback.data

        logger.info(f"用戶 {user_id} postback: {data}")

        try:
            # 解析postback data
            params = dict(param.split('=') for param in data.split('&'))
            action = params.get('action')

            if action == 'save_invoice':
                # 實際儲存邏輯
                try:
                    user_session = self.session_manager.get_session(params.get('user_id'))
                    if 'last_invoice' in user_session.temp_data:
                        invoice_data = user_session.temp_data['last_invoice']
                        file_data = user_session.temp_data.get('last_file_data', b'')
                        media_type = user_session.temp_data.get('last_media_type', 'image/jpeg')

                        # 調用invoice_service的save_invoice_data
                        invoice_handler = self.service_registry.get_handler("照片記帳")
                        if invoice_handler and invoice_handler.invoice_service:
                            spreadsheet_url = invoice_handler.invoice_service.save_invoice_data(invoice_data, file_data, media_type)
                            user_session.temp_data.clear()

                            await self.line_client.reply_text(
                                event.reply_token,
                                f"✅ 發票資料已確認儲存到試算表！\n\n📊 試算表連結:\n{spreadsheet_url}\n\n感謝您的使用。"
                            )
                        else:
                            await self.line_client.reply_text(event.reply_token, "❌ 發票服務未準備好，無法儲存")
                    else:
                        await self.line_client.reply_text(event.reply_token, "❌ 找不到發票資料，請重新辨識")
                except Exception as e:
                    logger.error(f"儲存發票失敗: {e}")
                    await self.line_client.reply_text(event.reply_token, "❌ 儲存發票時發生錯誤，請稍後再試")

            elif action == 'edit_invoice':
                await self.line_client.reply_text(
                    event.reply_token,
                    "📝 請重新上傳發票或返回主選單。",
                    quick_replies=[
                        {"label": "重新上傳", "text": "重新上傳"},
                        {"label": "返回主選單", "text": "返回主選單"}
                    ]
                )
            else:
                await self.line_client.reply_text(
                    event.reply_token,
                    "未知的操作，請返回主選單。"
                )

        except Exception as e:
            logger.error(f"處理postback失敗: {e}")
            await self.line_client.reply_text(
                event.reply_token,
                "處理請求時發生錯誤，請稍後再試。"
            )

    async def _send_handler_response(self, reply_token: str, user_id: str, response: HandlerResponse):
        """發送處理器回應 - 統一接口"""
        # loading動畫現在在handler調用前發送，這裡不需要重複

        # 保存臨時數據到會話
        if response.temp_data:
            session = self.session_manager.get_session(user_id)
            session.temp_data.update(response.temp_data)

        # 處理確認卡片
        if response.text == "confirm_template" and response.template_data:
            await self.line_client.reply_confirm_template(
                reply_token=reply_token,
                **response.template_data
            )
        else:
            await self.line_client.reply_text(
                reply_token=reply_token,
                text=response.text,
                quick_replies=response.quick_replies
            )

# 全局控制器實例
bot_controller: LineBotController = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global session_manager, service_registry, line_client, bot_controller

    logger.info("初始化 LINE Bot v5...")

    # 初始化核心服務
    async_api_client = AsyncApiClient(configuration)
    session_manager = SessionManager()
    service_registry = ServiceRegistry()
    line_client = LineClient(async_api_client, LINE_CHANNEL_ACCESS_TOKEN)
    bot_controller = LineBotController(session_manager, service_registry, line_client)

    logger.info("LINE Bot v5 初始化完成")

    yield

    # 關閉資源
    logger.info("關閉 LINE Bot v5...")
    if async_api_client:
        await async_api_client.close()
    logger.info("LINE Bot v5 已關閉")

app.router.lifespan_context = lifespan

# --- Webhook 處理 ---
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()

    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="無效的簽名")

    return JSONResponse(content={"status": "OK"})

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event: MessageEvent):
    """文字訊息處理入口"""
    asyncio.create_task(bot_controller.handle_text_message(event))

@handler.add(MessageEvent, message=[ImageMessageContent, FileMessageContent])
def handle_file(event: MessageEvent):
    """文件訊息處理入口"""
    asyncio.create_task(bot_controller.handle_file_message(event))

@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent):
    """Postback 事件處理 - 處理確認卡片按鈕"""
    asyncio.create_task(bot_controller.handle_postback_event(event))

# --- 健康檢查 ---
@app.get("/health")
async def health_check():
    """健康檢查端點"""
    services_status = {}

    if service_registry:
        for service_name in service_registry.list_services():
            handler = service_registry.get_handler(service_name)
            # 簡單檢查處理器是否初始化
            services_status[service_name] = handler is not None

    return {
        "status": "healthy",
        "services": services_status,
        "active_sessions": len(session_manager._sessions) if session_manager else 0
    }

# --- 主程式啟動 ---
if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Line Bot v5 Clean Architecture")
    parser.add_argument("--port", type=int, default=8013, help="Port to run the server")
    args = parser.parse_args()

    port = int(os.getenv('LINE_BOT_PORT', args.port))
    logger.info(f"啟動 LINE Bot v5 於端口 {port}")

    uvicorn.run(app, host="0.0.0.0", port=port)