#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings('ignore', category=NotOpenSSLWarning)
except ImportError:
    # 如果 urllib3 版本較舊，可能沒有這個警告類別
    pass
import os
import sys
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 將專案根目錄添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 匯入發票處理器
from services.invoice_service.main import InvoiceProcessor
from services.invoice_service.services.ocr_service import OCRService
from typing import Dict, Any, Optional, List # 導入 Dict, Any, List
import asyncio # 導入 asyncio
from services.qa_service.qa_client import process_qa_query # 導入 QA 客戶端
from services.finance_analysis_service.main import FinanceAnalysisProcessor
from services.google_auth_service.main import GoogleAuthProcessor # 導入 Google 授權服務
import re # 導入正則表達式模組
from apscheduler.schedulers.asyncio import AsyncIOScheduler # 導入排程器
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

# 使用 LINE Bot SDK v3
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob, ReplyMessageRequest,
    PushMessageRequest, TextMessage, TemplateMessage, ConfirmTemplate,
    AsyncApiClient, AsyncMessagingApi, AsyncMessagingApiBlob # 導入非同步客戶端
)
from linebot.v3.messaging.models import QuickReply, QuickReplyItem, MessageAction, PostbackAction
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, ImageMessageContent, FileMessageContent,
    FollowEvent, PostbackEvent
)
import aiohttp

# --- 初始化與設定 ---
load_dotenv()
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "line_bot_simple_client.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.error("LINE Bot 憑證未設定！")
    exit(1)

# MCP Gateway 設定
MCP_GATEWAY_URL = f"http://{os.getenv('MCP_GATEWAY_HOST', '127.0.0.1')}:{os.getenv('MCP_GATEWAY_PORT', '8000')}"

# FastAPI, LINE Bot SDK, and Invoice Processor 初始化
app = FastAPI(title="財務稅法顧問 LINE Bot")
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 全局的 AsyncApiClient 和 AsyncMessagingApi 實例
# 這些實例將在應用程式啟動時初始化
async_api_client: Optional[AsyncApiClient] = None
line_bot_async_api: Optional[AsyncMessagingApi] = None
line_bot_blob_api: Optional[AsyncMessagingApiBlob] = None

# 將 invoice_processor 聲明為全局變數，以便在需要時重新初始化
invoice_processor: Optional[InvoiceProcessor] = None

# 將 finance_analysis_processor 聲明為全局變數
finance_analysis_processor: Optional[FinanceAnalysisProcessor] = None

# 將 google_auth_processor 聲明為全局變數
google_auth_processor: Optional[GoogleAuthProcessor] = None

# 排程器全域變數
scheduler: Optional[AsyncIOScheduler] = None

def _initialize_finance_analysis_processor():
    """初始化或重新初始化 FinanceAnalysisProcessor 實例"""
    global finance_analysis_processor
    try:
        finance_analysis_processor = FinanceAnalysisProcessor()
        logger.info("FinanceAnalysisProcessor 已初始化。")
    except Exception as e:
        logger.error(f"初始化 FinanceAnalysisProcessor 失敗: {e}")
        finance_analysis_processor = None

def _initialize_invoice_processor():
    """初始化或重新初始化 InvoiceProcessor 實例"""
    global invoice_processor
    try:
        invoice_processor = InvoiceProcessor()
        logger.info(f"InvoiceProcessor 已初始化，當前 OCR 提供者: {os.getenv('OCR_PROVIDER')}")
    except Exception as e:
        logger.error(f"初始化 InvoiceProcessor 失敗: {e}")
        invoice_processor = None

def _initialize_google_auth_processor():
    """初始化或重新初始化 GoogleAuthProcessor 實例"""
    global google_auth_processor
    try:
        # 使用環境變數或預設值設定 base_url
        base_url = os.getenv('GOOGLE_AUTH_BASE_URL', 'http://localhost:8080')
        google_auth_processor = GoogleAuthProcessor(base_url=base_url)
        logger.info("GoogleAuthProcessor 已初始化。")
    except Exception as e:
        logger.error(f"初始化 GoogleAuthProcessor 失敗: {e}")
        google_auth_processor = None

async def send_daily_calendar_reminder():
    """每日 9:00 發送行事曆提醒"""
    if not google_auth_processor or not line_bot_async_api:
        logger.warning("無法發送每日提醒：服務未初始化")
        return

    logger.info("開始發送每日行事曆提醒")

    try:
        # 取得所有已綁定的用戶
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'user_bindings.sqlite')

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT line_user_id, google_email FROM user_bindings")
            users = cursor.fetchall()

        for line_user_id, google_email in users:
            try:
                # 檢查用戶是否仍然有效
                if not google_auth_processor.is_user_bound(line_user_id):
                    continue

                # 取得今天的事件
                today_events = google_auth_processor.get_today_events(line_user_id)
                upcoming_events = google_auth_processor.get_upcoming_events(line_user_id, limit=10)

                # 組合提醒訊息
                message_parts = ["🌅 早安！今日行程提醒"]

                if today_events:
                    formatted_today = google_auth_processor.format_events_for_line(today_events)
                    message_parts.append(f"📅 今天的行程：\n{formatted_today}")
                else:
                    message_parts.append("📅 今天沒有特別的行程安排")

                if upcoming_events:
                    # 過濾出未來一週的事件（排除今天）
                    future_events = [e for e in upcoming_events if e['start_datetime'].date() > datetime.now().date()][:5]
                    if future_events:
                        formatted_upcoming = google_auth_processor.format_events_for_line(future_events)
                        message_parts.append(f"📋 本週即將到來的行程：\n{formatted_upcoming}")

                message_parts.append("祝您有美好的一天！ 😊")
                reminder_text = "\n\n".join(message_parts)

                # 發送提醒
                await line_bot_async_api.push_message(
                    PushMessageRequest(
                        to=line_user_id,
                        messages=[TextMessage(text=reminder_text)]
                    )
                )

                logger.info(f"已發送每日提醒給用戶 {line_user_id} ({google_email})")

            except Exception as user_error:
                logger.error(f"發送每日提醒給用戶 {line_user_id} 失敗: {user_error}")
                continue

    except Exception as e:
        logger.error(f"發送每日行事曆提醒失敗: {e}")

def _initialize_scheduler():
    """初始化排程器"""
    global scheduler
    try:
        scheduler = AsyncIOScheduler()

        # 設定每日 9:00 的提醒
        scheduler.add_job(
            send_daily_calendar_reminder,
            CronTrigger(hour=9, minute=0),
            id='daily_calendar_reminder',
            name='每日行事曆提醒'
        )

        scheduler.start()
        logger.info("排程器已初始化，每日 9:00 將發送行事曆提醒")
    except Exception as e:
        logger.error(f"初始化排程器失敗: {e}")
        scheduler = None

# 狀態與暫存管理
user_states: Dict[str, str] = {}
invoice_cache: Dict[str, Dict] = {}
calendar_selection_cache: Dict[str, List[str]] = {}  # 儲存用戶選擇的行事曆 IDs

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global async_api_client, line_bot_async_api, line_bot_blob_api
    logger.info("應用程式啟動，初始化 LINE Bot Async API Client...")
    
    # 啟動事件
    async_api_client = AsyncApiClient(configuration)
    line_bot_async_api = AsyncMessagingApi(async_api_client)
    line_bot_blob_api = AsyncMessagingApiBlob(async_api_client)
    _initialize_invoice_processor()
    _initialize_finance_analysis_processor()
    _initialize_google_auth_processor()
    _initialize_scheduler()
    # 加入 Google OAuth 路由
    if google_auth_processor:
        try:
            from services.google_auth_service.services.web_routes import create_oauth_routes
            oauth_router = create_oauth_routes(google_auth_processor.oauth_service)
            app.include_router(oauth_router)
            logger.info("Google OAuth 路由已加入。")
        except Exception as e:
            logger.error(f"無法加入 Google OAuth 路由: {e}")

    logger.info("初始化完成。")

    yield
    
    # 關閉事件
    if scheduler:
        logger.info("應用程式關閉，關閉排程器...")
        scheduler.shutdown()
        logger.info("排程器已關閉。")

    if async_api_client:
        logger.info("應用程式關閉，關閉 LINE Bot Async API Client...")
        await async_api_client.close()
        logger.info("Client 已關閉。")

# 將 lifespan 管理器應用到 FastAPI app
app.router.lifespan_context = lifespan

# --- Webhook 與核心邏輯 ---
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="無效的簽名")
    return JSONResponse(content={"status": "OK"})

async def reply_main_menu(reply_token: str): # 移除 api_client 參數
    """回覆主選單"""
    await line_bot_async_api.reply_message( # 使用全局實例
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(
                text="您好！請問需要什麼服務？",
                quick_reply=QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="QA問答", text="QA問答")),
                    QuickReplyItem(action=MessageAction(label="照片記帳", text="照片記帳")),
                    QuickReplyItem(action=MessageAction(label="財務分析", text="財務分析")),
                    QuickReplyItem(action=MessageAction(label="記事提醒", text="記事提醒")),
                ])
            )]
        )
    )


async def send_loading_animation(user_id: str, seconds: int = 30):
    url = "https://api.line.me/v2/bot/chat/loading/start"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    data = {
        "chatId": user_id,
        "loadingSeconds": seconds
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            pass

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent): # 保持為同步函數
    """處理文字訊息，根據使用者狀態進行路由"""
    user_id = event.source.user_id
    text = event.message.text.strip()
    current_state = user_states.get(user_id)
    
    # 在新的非同步任務中執行實際的處理邏輯
    asyncio.create_task(_async_handle_text_message(event))

async def _async_handle_text_message(event: MessageEvent):
    """非同步處理文字訊息的實際邏輯"""
    user_id = event.source.user_id
    text = event.message.text.strip()
    current_state = user_states.get(user_id)

    # 移除 async with AsyncApiClient(configuration) as api_client:
    # 移除 line_bot_api = AsyncMessagingApi(api_client)
    if text == "QA問答":
        user_states[user_id] = 'qa_mode'
        await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="已進入QA問答模式，請直接提出您的問題。")])) # 使用全局實例
    elif text == "照片記帳":
        user_states[user_id] = 'awaiting_invoice'
        await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="已進入照片記帳模式，請傳送您的發票圖片或PDF。")])) # 使用全局實例
    elif text == "財務分析":
        user_states[user_id] = 'finance_analysis_mode'
        await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="已進入財務分析模式，請提供您的財務數據試算表連結，或直接提出分析問題。")]))
    elif text == "記事提醒":
        if not google_auth_processor:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="記事提醒服務暫時無法使用，請稍後再試。")]))
            return

        # 檢查用戶是否已綁定 Google 帳號
        if google_auth_processor.is_user_bound(user_id):
            # 已綁定，顯示行事曆功能選單
            await line_bot_async_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text="記事提醒功能選單：",
                        quick_reply=QuickReply(items=[
                            QuickReplyItem(action=MessageAction(label="今天行程", text="今天行程")),
                            QuickReplyItem(action=MessageAction(label="本週行程", text="本週行程")),
                            QuickReplyItem(action=MessageAction(label="記事設定", text="記事設定")),
                            QuickReplyItem(action=MessageAction(label="解除綁定", text="解除綁定")),
                        ])
                    )]
                )
            )
        else:
            # 尚未綁定，引導綁定流程
            await line_bot_async_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text="您尚未綁定 Google 帳號。請點選「綁定 Google 帳號」開始設定，即可使用記事提醒功能。",
                        quick_reply=QuickReply(items=[
                            QuickReplyItem(action=MessageAction(label="綁定 Google 帳號", text="綁定 Google 帳號")),
                            QuickReplyItem(action=MessageAction(label="返回主選單", text="返回主選單")),
                        ])
                    )]
                )
            )
    elif text == "更換模型":
        await line_bot_async_api.reply_message( # 使用全局實例
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text="請選擇您想使用的 OCR 模型：",
                    quick_reply=QuickReply(items=[
                        QuickReplyItem(action=PostbackAction(label="OpenAI", data="action=set_ocr_model&model=openai")),
                        QuickReplyItem(action=PostbackAction(label="Google Gemini", data="action=set_ocr_model&model=google")),
                    ])
                )]
            )
        )
    elif text == "綁定 Google 帳號":
        if not google_auth_processor:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="記事提醒服務暫時無法使用，請稍後再試。")]))
            return

        try:
            auth_url = google_auth_processor.start_oauth_flow(user_id)
            await line_bot_async_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"請點擊以下連結在瀏覽器中完成 Google 帳號授權：\n{auth_url}\n\n授權完成後，請輸入「檢查綁定狀態」確認設定。")]
                )
            )
        except Exception as e:
            logger.error(f"啟動 Google 授權失敗: {e}")
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="啟動授權過程失敗，請稍後再試。")]))
    elif text == "檢查綁定狀態":
        if not google_auth_processor:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="記事提醒服務暫時無法使用，請稍後再試。")]))
            return

        status = google_auth_processor.get_user_binding_status(user_id)
        if status['is_bound']:
            await line_bot_async_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text=f"✅ {status['message']}\n行事曆存取：{'正常' if status['calendar_access'] else '異常'}\n\n請選擇您要追蹤的行事曆：",
                        quick_reply=QuickReply(items=[
                            QuickReplyItem(action=MessageAction(label="選擇行事曆", text="選擇行事曆")),
                            QuickReplyItem(action=MessageAction(label="返回主選單", text="返回主選單")),
                        ])
                    )]
                )
            )
        else:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=f"❌ {status['message']}\n請重新進行授權。")]))
    elif text == "今天行程":
        if not google_auth_processor or not google_auth_processor.is_user_bound(user_id):
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請先綁定 Google 帳號才能查看行程。")]))
            return

        try:
            await send_loading_animation(user_id)
            today_events = google_auth_processor.get_today_events(user_id)
            if today_events:
                formatted_text = google_auth_processor.format_events_for_line(today_events)
                reply_text = f"📅 今天的行程：\n{formatted_text}"
            else:
                reply_text = "📅 今天沒有行程安排。"

            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
        except Exception as e:
            logger.error(f"取得今天行程失敗: {e}")
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="取得行程時發生錯誤，請稍後再試。")]))
    elif text == "本週行程":
        if not google_auth_processor or not google_auth_processor.is_user_bound(user_id):
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請先綁定 Google 帳號才能查看行程。")]))
            return

        try:
            await send_loading_animation(user_id)
            upcoming_events = google_auth_processor.get_upcoming_events(user_id, limit=20)
            if upcoming_events:
                formatted_text = google_auth_processor.format_events_for_line(upcoming_events)
                reply_text = f"📅 本週行程預覽：\n{formatted_text}"
            else:
                reply_text = "📅 本週沒有行程安排。"

            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
        except Exception as e:
            logger.error(f"取得本週行程失敗: {e}")
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="取得行程時發生錯誤，請稍後再試。")]))
    elif text == "解除綁定":
        if not google_auth_processor:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="記事提醒服務暫時無法使用，請稍後再試。")]))
            return

        if google_auth_processor.unbind_user(user_id):
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="✅ 已成功解除 Google 帳號綁定。")]))
        else:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="❌ 解除綁定失敗，請稍後再試。")]))
    elif text == "選擇行事曆":
        if not google_auth_processor or not google_auth_processor.is_user_bound(user_id):
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請先綁定 Google 帳號才能選擇行事曆。")]))
            return

        try:
            await send_loading_animation(user_id)
            calendars = google_auth_processor.get_available_calendars(user_id)
            if calendars:
                # 準備行事曆選項
                calendar_text = "請選擇您要追蹤的行事曆（可多選）：\n\n"
                quick_reply_items = []

                for i, calendar in enumerate(calendars[:10]):  # 限制前 10 個行事曆
                    calendar_name = calendar['summary']
                    if calendar.get('primary'):
                        calendar_name += " (主要)"
                    calendar_text += f"{i+1}. {calendar_name}\n"
                    quick_reply_items.append(
                        QuickReplyItem(action=PostbackAction(
                            label=f"{i+1}. {calendar_name[:10]}...",
                            data=f"action=toggle_calendar&user_id={user_id}&calendar_id={calendar['id']}&calendar_name={calendar['summary']}"
                        ))
                    )

                quick_reply_items.append(QuickReplyItem(action=PostbackAction(label="完成選擇", data=f"action=finish_calendar_selection&user_id={user_id}")))
                quick_reply_items.append(QuickReplyItem(action=MessageAction(label="返回主選單", text="返回主選單")))

                user_states[user_id] = 'selecting_calendars'
                await line_bot_async_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=calendar_text, quick_reply=QuickReply(items=quick_reply_items))]
                    )
                )
            else:
                await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="無法取得行事曆列表，請檢查您的權限設定。")]))
        except Exception as e:
            logger.error(f"取得行事曆列表失敗: {e}")
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="取得行事曆列表時發生錯誤，請稍後再試。")]))
    elif text == "記事設定":
        if not google_auth_processor or not google_auth_processor.is_user_bound(user_id):
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請先綁定 Google 帳號才能設定行事曆。")]))
            return

        status = google_auth_processor.get_user_binding_status(user_id)
        selected_count = len(status.get('selected_calendars', []))

        await line_bot_async_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=f"📊 記事設定狀態：\n✅ Google 帳號：{status['email']}\n📅 已選擇行事曆：{selected_count} 個\n📱 行事曆存取：{'正常' if status['calendar_access'] else '異常'}",
                    quick_reply=QuickReply(items=[
                        QuickReplyItem(action=MessageAction(label="重新選擇行事曆", text="選擇行事曆")),
                        QuickReplyItem(action=MessageAction(label="解除綁定", text="解除綁定")),
                        QuickReplyItem(action=MessageAction(label="返回主選單", text="返回主選單")),
                    ])
                )]
            )
        )
    elif text in ["取消", "離開", "返回主選單"]:
        if user_id in user_states: del user_states[user_id]
        if user_id in invoice_cache: del invoice_cache[user_id]
        if user_id in calendar_selection_cache: del calendar_selection_cache[user_id]
        await reply_main_menu(event.reply_token) # 移除 api_client 參數
    elif current_state == 'qa_mode':
        await send_loading_animation(user_id)
        try:
            # 直接處理查詢並等待結果
            qa_response = await process_qa_query(platform="LINE", user_id=user_id, query=text)
            reply_text = qa_response.get("response", "抱歉，我無法處理您的請求。")
        except Exception as e:
            logger.error(f"QA請求失敗: {e}", exc_info=True)
            reply_text = "抱歉，服務暫時無法回應。"
        
        # 使用原始 reply_token 回覆最終答案
        await line_bot_async_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text, quick_reply=QuickReply(items=[QuickReplyItem(action=MessageAction(label="離開QA模式", text="離開"))]))]
            )
        )
    elif current_state == 'finance_analysis_mode':
        await send_loading_animation(user_id)
        if not finance_analysis_processor:
            reply_text = "財務分析服務尚未準備好，請稍後再試。"
            logger.error(reply_text)
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
            return

        spreadsheet_url = None
        # 簡單的 URL 識別，可以根據實際需求調整正則表達式
        url_match = re.search(r'https?://[^\s]+', text)
        if url_match:
            spreadsheet_url = url_match.group(0)
            # 從原始文本中移除 URL，只將問題部分傳遞給 AI
            query_without_url = text.replace(spreadsheet_url, "").strip()
            if not query_without_url: # 如果只有 URL，則將問題設置為預設值
                query_without_url = "請分析此試算表數據。"
            logger.info(f"檢測到試算表 URL: {spreadsheet_url}")
            logger.info(f"傳遞給 AI 的問題: {query_without_url}")
            
            finance_response = await finance_analysis_processor.process_finance_query(
                platform="LINE", user_id=user_id, query=query_without_url
            )
        else:
            # 如果沒有 URL，直接將用戶輸入作為問題
            finance_response = await finance_analysis_processor.process_finance_query(
                platform="LINE", user_id=user_id, query=text
            )
        
        response_text = finance_response.get("response", "抱歉，財務分析服務無法處理您的請求。")
        total_cost_usd = finance_response.get("total_cost", 0.0)
        duration = finance_response.get("duration", 0.0)
        
        # 將成本轉換為新台幣
        total_cost_twd = total_cost_usd * 32 # 假設匯率為 1:32
        
        # 組合最終回覆訊息
        reply_text = (
            f"{response_text}\n\n"
            f"---\n"
            f"📊 **本次分析資訊**\n"
            f"⏱️ **運行時間**: {duration:.2f} 秒\n"
            f"💰 **預估花費**: NT$ {total_cost_twd:.6f}"
        )

        await line_bot_async_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text, quick_reply=QuickReply(items=[QuickReplyItem(action=MessageAction(label="離開財務分析", text="離開"))]))]
            )
        )
    elif current_state and current_state.startswith('editing_field_'):
        field_to_edit = current_state.replace('editing_field_', '')
        if user_id in invoice_cache:
            invoice_cache[user_id][field_to_edit] = text
            user_states[user_id] = 'awaiting_invoice' # 返回等待發票狀態
            
            # 重新發送確認卡片
            await _send_confirm_card(line_bot_async_api, event.reply_token, user_id, invoice_cache[user_id]) # 使用全局實例
        else:
            await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="抱歉，找不到您的發票資料，可能已逾時，請重新操作。")])) # 使用全局實例
    elif current_state == 'awaiting_invoice':
        await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請傳送發票檔案，或輸入「離開」以返回主選單。")])) # 使用全局實例
    else:
        await reply_main_menu(event.reply_token) # 移除 api_client 參數

@handler.add(MessageEvent, message=[ImageMessageContent, FileMessageContent])
def handle_invoice_message(event: MessageEvent): # 保持為同步函數
    """處理圖片/檔案，僅在 'awaiting_invoice' 狀態下觸發"""
    user_id = event.source.user_id
    if user_states.get(user_id) != 'awaiting_invoice': return

    # 在新的非同步任務中執行實際的處理邏輯
    asyncio.create_task(_async_handle_invoice_message(event))

async def _async_handle_invoice_message(event: MessageEvent):
    """非同步處理發票訊息的實際邏輯"""
    user_id = event.source.user_id
    await send_loading_animation(user_id)
    
    if not all([invoice_processor, line_bot_async_api, line_bot_blob_api]):
        error_message = "服務尚未完全初始化，請稍後再試。"
        logger.error(error_message)
        try:
            # Try to reply, but it might fail if line_bot_async_api is the one not initialized
            if line_bot_async_api:
                await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=error_message)]))
        except Exception as reply_error:
            logger.error(f"回覆服務未初始化錯誤時失敗: {reply_error}")
        return

    try:
        message_content_bytes = await line_bot_blob_api.get_message_content(message_id=event.message.id)
        
        media_type = 'image/jpeg' if isinstance(event.message, ImageMessageContent) else 'application/pdf'
        invoice_data, usage = await invoice_processor.process_invoice_from_data(message_content_bytes, media_type)
        
        profile = await line_bot_async_api.get_profile(user_id)
        
        invoice_data['user_id'] = user_id
        invoice_data['user_display_name'] = getattr(profile, 'display_name', '未知使用者')
        invoice_data['usage'] = usage # 將 usage 資訊存入 invoice_data

        invoice_cache[user_id] = invoice_data
        # 將 file_data 和 media_type 儲存為單獨的鍵，以便稍後儲存
        invoice_cache[user_id]['file_data_for_save'] = message_content_bytes
        invoice_cache[user_id]['media_type_for_save'] = media_type
        
        await _send_confirm_card(line_bot_async_api, event.reply_token, user_id, invoice_data)

    except Exception as e:
        logger.error(f"發票處理流程出錯: {e}", exc_info=True)
        await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='抱歉，辨識發票時發生錯誤。')]))
    finally:
        if user_id in user_states:
            del user_states[user_id]

@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent): # 保持為同步函數
    """處理 Postback 事件"""
    # 在新的非同步任務中執行實際的處理邏輯
    asyncio.create_task(_async_handle_postback(event))

async def _async_handle_postback(event: PostbackEvent):
    """非同步處理 Postback 事件的實際邏輯"""
    params = dict(p.split('=', 1) for p in event.postback.data.split('&'))
    action = params.get('action')
    user_id = params.get('user_id')
    if not user_id: return

    reply_text = None # 初始化 reply_text
    try:
        if action == 'save_invoice':
            if user_id in invoice_cache:
                import time
                await send_loading_animation(user_id)
                start_time = time.time()
                
                # 執行儲存操作
                save_result_text = await _async_save_invoice(user_id, invoice_cache[user_id])
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # 根據處理時間決定回覆方式
                if processing_time < 25:
                    # 快速完成，使用 Reply Token
                    final_text = f"{save_result_text}\n(使用 Reply API，耗時 {processing_time:.2f} 秒)"
                    await line_bot_async_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=final_text)]
                        )
                    )
                else:
                    # 處理時間較長，改用 Push API
                    final_text = f"{save_result_text}\n(使用 Push API，耗時 {processing_time:.2f} 秒)"
                    await line_bot_async_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=final_text)]
                        )
                    )
                
                # 清除使用者狀態並結束
                if user_id in user_states: del user_states[user_id]
                return
            else:
                # 如果快取找不到，用 reply_message 回覆
                reply_text = "抱歉，找不到您的發票資料，可能已逾時，請重新操作。"
                await line_bot_async_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_text)]
                    )
                )
                return
        elif action == 'set_ocr_model':
            selected_model = params.get('model')
            if selected_model in ['openai', 'google']:
                os.environ['OCR_PROVIDER'] = selected_model # 更新環境變數
                _initialize_invoice_processor() # 重新初始化 InvoiceProcessor
                reply_text = f"OCR 模型已切換為 {selected_model.upper()}。"
                logger.info(f"使用者 {user_id} 將 OCR 模型切換為 {selected_model.upper()}")
            else:
                reply_text = "無效的模型選擇。"
            
            # 清除使用者狀態並返回主選單
            if user_id in user_states: del user_states[user_id]
            await line_bot_async_api.push_message(PushMessageRequest(to=user_id, messages=[ # 使用全局實例
                TextMessage(text=reply_text, quick_reply=QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="QA問答", text="QA問答")),
                    QuickReplyItem(action=MessageAction(label="照片記帳", text="照片記帳")),
                ]))
            ]))
            return # 確保沒有其他訊息被發送
        elif action == 'edit_invoice':
            # 編輯發票的邏輯
            # 這裡可以回覆一個包含所有可編輯欄位的快速回覆選單
            if user_id in invoice_cache:
                reply_text = "請選擇您要編輯的欄位："
                field_mapping = {
                    'transaction_type': '項目', 
                    'seller_id': '賣方統編',
                    'invoice_number': '發票號碼',
                    'invoice_date': '日期',
                    'account': '金額',
                    'invoice_type': '格式',
                    'invoice_description': '品項',
                    'category': '類別',
                }
                quick_reply_items = []
                for key, label in field_mapping.items():
                    quick_reply_items.append(
                        QuickReplyItem(action=PostbackAction(label=label, data=f'action=select_field&user_id={user_id}&field={key}'))
                    )
                
                await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[ # 使用全局實例
                    TextMessage(text=reply_text, quick_reply=QuickReply(items=quick_reply_items))
                ]))
                user_states[user_id] = 'editing_invoice' # 設置使用者狀態為編輯中
            else:
                reply_text = "抱歉，找不到您的發票資料，可能已逾時，請重新操作。"
                await line_bot_async_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])) # 使用全局實例
            return # 確保沒有其他訊息被發送
        elif action == 'select_field':
            field_to_edit = params.get('field')
            if user_id in invoice_cache and field_to_edit:
                user_states[user_id] = f'editing_field_{field_to_edit}'
                reply_text = f"請輸入新的「{field_to_edit}」資訊："
                await line_bot_async_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])) # 使用全局實例
            else:
                reply_text = "抱歉，找不到您的發票資料或欄位資訊，可能已逾時，請重新操作。"
                await line_bot_async_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])) # 使用全局實例
            return # 確保沒有其他訊息被發送
        elif action == 'cancel_invoice':
            reply_text = "操作已取消。"
            if user_id in invoice_cache: del invoice_cache[user_id]
        elif action == 'toggle_calendar':
            # 切換行事曆選擇狀態
            calendar_id = params.get('calendar_id')
            calendar_name = params.get('calendar_name')

            if user_id not in calendar_selection_cache:
                calendar_selection_cache[user_id] = []

            if calendar_id in calendar_selection_cache[user_id]:
                calendar_selection_cache[user_id].remove(calendar_id)
                status_text = f"已取消選擇：{calendar_name}"
            else:
                calendar_selection_cache[user_id].append(calendar_id)
                status_text = f"已選擇：{calendar_name}"

            # 顯示當前選擇狀態
            selected_count = len(calendar_selection_cache[user_id])
            reply_text = f"{status_text}\n目前已選擇 {selected_count} 個行事曆\n\n請繼續選擇或點擊「完成選擇」。"

            await line_bot_async_api.push_message(
                PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])
            )
            return
        elif action == 'finish_calendar_selection':
            # 完成行事曆選擇
            if user_id in calendar_selection_cache and calendar_selection_cache[user_id]:
                selected_calendars = calendar_selection_cache[user_id]
                success = google_auth_processor.save_calendar_selection(user_id, selected_calendars)

                if success:
                    reply_text = f"✅ 已成功儲存您的行事曆選擇！\n共選擇了 {len(selected_calendars)} 個行事曆\n\n現在您可以查看今天行程和本週行程了。"
                else:
                    reply_text = "❌ 儲存行事曆選擇失敗，請稍後再試。"

                # 清除選擇快取
                if user_id in calendar_selection_cache:
                    del calendar_selection_cache[user_id]
                if user_id in user_states:
                    del user_states[user_id]
            else:
                reply_text = "請至少選擇一個行事曆。"

            await line_bot_async_api.push_message(
                PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])
            )
            return
        if user_id in user_states: del user_states[user_id]
    except Exception as e:
        logger.error(f"Postback 處理失敗: {e}")
        reply_text = "處理您的請求時發生錯誤。"

    if reply_text: # This block should now only be hit for 'edit_invoice' or 'select_field' failures, or general exceptions
        await line_bot_async_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])) # 使用全局實例

async def _async_save_invoice(user_id: str, invoice_data: Dict) -> str:
    """非同步儲存發票資料並回傳結果訊息"""
    try:
        file_data_for_save = invoice_data.get('file_data_for_save')
        media_type_for_save = invoice_data.get('media_type_for_save')

        if file_data_for_save and media_type_for_save:
            spreadsheet_url = invoice_processor.save_invoice_data(
                invoice_data, file_data_for_save, media_type_for_save
            )
            return f"✅ 發票已成功儲存！\n🔗試算表連結: {spreadsheet_url}"
        else:
            logger.error("儲存發票資料失敗：invoice_cache 中缺少檔案資料。")
            return "❌ 儲存發票資料失敗：缺少檔案資料。"
    except Exception as save_e:
        logger.error(f"儲存發票資料時發生錯誤: {save_e}", exc_info=True)
        return "❌ 儲存發票資料失敗。"
    finally:
        if user_id in invoice_cache: del invoice_cache[user_id] # Always clear cache after attempt

async def _send_confirm_card(line_bot_api: AsyncMessagingApi, reply_token: str, user_id: str, invoice_data: Dict): # 調整參數
    """發送包含發票資訊的確認卡片"""
    # 確保 usage 字典有這些鍵，避免 KeyError
    prompt_tokens = invoice_data.get('usage', {}).get('prompt_tokens', 0)
    completion_tokens = invoice_data.get('usage', {}).get('completion_tokens', 0)

    input_cost = (prompt_tokens / 1_000_000) * 5.0
    output_cost = (completion_tokens / 1_000_000) * 15.0
    total_cost_usd = input_cost + output_cost
    total_cost_twd = total_cost_usd * 32
    cost_text = f"\n(本次辨識成本約 NT$ {total_cost_twd:.4f})"

    # 使用 .get() 來安全地獲取可選欄位
    confirm_text = (f"發票辨識結果如下，請確認：\n"
                    f"📝 類型: {invoice_data.get('transaction_type', 'N/A')}\n"
                    f"🏢 賣方統編: {invoice_data.get('seller_id', '無法辨識')}\n"
                    f"🔢 發票號碼: {invoice_data.get('invoice_number', '無法辨識')}\n"
                    f"📅 日期: {invoice_data.get('invoice_date', '無法辨識')}\n"
                    f"💰 金額: {invoice_data.get('account', '無法辨識')}\n"
                    f"📄 格式: {invoice_data.get('invoice_type', '無法辨識')}\n"
                    f"🛍️ 品項: {invoice_data.get('invoice_description', '無品名資訊')[:60]}\n"
                    f"🏷️ 類別: {invoice_data.get('category', '無法辨識')}"
                    f"{cost_text}")

    confirm_template = ConfirmTemplate(text=confirm_text, actions=[
        PostbackAction(label='確認儲存', data=f'action=save_invoice&user_id={user_id}'),
        PostbackAction(label='編輯發票', data=f'action=edit_invoice&user_id={user_id}')
    ])
    
    await line_bot_api.reply_message( # 使用傳入的 line_bot_api 實例
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TemplateMessage(alt_text='發票辨識結果確認', template=confirm_template)]
        )
    )

# --- 主程式啟動 ---
if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Line Bot Simple Client")
    parser.add_argument("--port", type=int, default=8013, help="Port to run the FastAPI application on")
    args = parser.parse_args()

    port = int(os.getenv('LINE_BOT_PORT', args.port)) # 預設使用與原版相同的端口
    uvicorn.run(app, host="0.0.0.0", port=port)