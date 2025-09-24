#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import threading
import httpx
import requests
import time
import asyncio # 導入 asyncio
from typing import Dict, Any
from functools import partial # 導入 partial
from concurrent.futures import ThreadPoolExecutor # 導入 ThreadPoolExecutor
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 匯入發票處理器
from invoice_processor.main import InvoiceProcessor

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

# --- 初始化與設定 ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.error("LINE Bot 憑證未設定！")
    exit(1)

# MCP 服務器設定 (用於QA)
MCP_SERVER_URL = f"http://{os.getenv('MCP_SERVER_HOST', '127.0.0.1')}:{os.getenv('MCP_SERVER_PORT', '8000')}"

# FastAPI, LINE Bot SDK, and Invoice Processor 初始化
app = FastAPI(title="財務稅法顧問 LINE Bot")
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 將 invoice_processor 聲明為全局變數，以便在需要時重新初始化
invoice_processor = None

def _initialize_invoice_processor():
    """初始化或重新初始化 InvoiceProcessor 實例"""
    global invoice_processor
    try:
        invoice_processor = InvoiceProcessor()
        logger.info(f"InvoiceProcessor 已初始化，當前 OCR 提供者: {os.getenv('OCR_PROVIDER')}")
    except Exception as e:
        logger.error(f"初始化 InvoiceProcessor 失敗: {e}")
        invoice_processor = None

# 首次啟動時初始化
_initialize_invoice_processor()

# 狀態與暫存管理
user_states: Dict[str, str] = {}
invoice_cache: Dict[str, Dict] = {}

# 初始化一個線程池執行器，用於執行同步的耗時操作
executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 1)

def send_loading_animation(user_id: str, seconds: int = 30):
    """發送 LINE 加載動畫請求"""
    url = "https://api.line.me/v2/bot/chat/loading/start"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    data = {
        "chatId": user_id,
        "loadingSeconds": seconds
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        logger.info(f"成功為 user_id: {user_id} 啟動載入動畫。")
    except requests.exceptions.RequestException as e:
        logger.error(f"為 user_id: {user_id} 啟動載入動畫失敗: {e}")

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

async def reply_main_menu(api_client: AsyncApiClient, reply_token: str): # 將函數改為 async，並使用 AsyncApiClient
    """回覆主選單"""
    await AsyncMessagingApi(api_client).reply_message( # 使用 await 和 AsyncMessagingApi
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(
                text="您好！請問需要什麼服務？",
                quick_reply=QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="財稅QA", text="財稅QA")),
                    QuickReplyItem(action=MessageAction(label="發票記帳", text="發票記帳")),
                ])
            )]
        )
    )

async def process_qa_in_background(user_id: str, text: str): # 將函數改為 async
    """背景處理財稅QA"""
    try:
        async with httpx.AsyncClient() as client: # 使用 AsyncClient
            response = await client.post(f"{MCP_SERVER_URL}/tools/chat", json={"platform": "LINE", "user_id": user_id, "message": text}, timeout=120) # 使用 await
        reply_text = response.json().get("result", {}).get("response", "抱歉，我無法處理您的請求。")
    except Exception as e:
        logger.error(f"QA請求失敗: {e}")
        reply_text = "抱歉，服務暫時無法回應。"
    
    async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
        await AsyncMessagingApi(api_client).push_message( # 使用 await 和 AsyncMessagingApi
            PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text, quick_reply=QuickReply(items=[QuickReplyItem(action=MessageAction(label="離開QA模式", text="離開"))]))])
        )

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

    async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
        line_bot_api = AsyncMessagingApi(api_client) # 使用 AsyncMessagingApi
        if text == "財稅QA":
            user_states[user_id] = 'qa_mode'
            await line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="已進入財稅問答模式，請直接提出您的問題。")])) # 使用 await
        elif text == "發票記帳":
            user_states[user_id] = 'awaiting_invoice'
            await line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="已進入發票記帳模式，請傳送您的發票圖片或PDF。")])) # 使用 await
        elif text == "更換模型":
            await line_bot_api.reply_message( # 使用 await
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
        elif text in ["取消", "離開", "返回主選單"]:
            if user_id in user_states: del user_states[user_id]
            if user_id in invoice_cache: del invoice_cache[user_id]
            await reply_main_menu(api_client, event.reply_token) # 使用 await
        elif current_state == 'qa_mode':
            # 改為發送載入動畫，取代原本的 "正在思考中" 訊息
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(executor, partial(send_loading_animation, user_id))
            # 啟動背景任務處理QA，它將會用 push_message 回覆
            asyncio.create_task(process_qa_in_background(user_id, text))
        elif current_state and current_state.startswith('editing_field_'):
            field_to_edit = current_state.replace('editing_field_', '')
            if user_id in invoice_cache:
                invoice_cache[user_id][field_to_edit] = text
                user_states[user_id] = 'awaiting_invoice' # 返回等待發票狀態
                
                # 重新發送確認卡片
                await _send_confirm_card(user_id, invoice_cache[user_id])
            else:
                await line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text="抱歉，找不到您的發票資料，可能已逾時，請重新操作。")]))
        elif current_state == 'awaiting_invoice':
            await line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請傳送發票檔案，或輸入「離開」以返回主選單。")])) # 使用 await
        else:
            await reply_main_menu(api_client, event.reply_token) # 使用 await

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
    
    async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
        line_bot_api = AsyncMessagingApi(api_client) # 使用 AsyncMessagingApi
        if not invoice_processor:
            await line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text="抱歉，發票處理服務目前無法使用。")]))
            return

        try:
            # 使用 push_message 來避免 reply token 逾時或重複使用的問題
            # 改為發送載入動畫，取代原本的 "辨識中" 訊息
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(executor, partial(send_loading_animation, user_id))
            
            line_bot_blob_api = AsyncMessagingApiBlob(api_client) # 使用 AsyncMessagingApiBlob
            message_content_bytes = await line_bot_blob_api.get_message_content(message_id=event.message.id) # 使用 await
            
            media_type = 'image/jpeg' if isinstance(event.message, ImageMessageContent) else 'application/pdf'
            invoice_data, usage = await invoice_processor.process_invoice_from_data(message_content_bytes, media_type) # 使用 await
            
            # 取得使用者資訊
            profile = await line_bot_api.get_profile(user_id) # 使用 await
            
            # 將 user_id 和 user_display_name 直接添加到 invoice_data 中
            invoice_data['user_id'] = user_id
            invoice_data['user_display_name'] = getattr(profile, 'display_name', '未知使用者')

            invoice_cache[user_id] = invoice_data
            # 將 file_data 和 media_type 儲存為單獨的鍵，以便稍後儲存
            invoice_cache[user_id]['file_data_for_save'] = message_content_bytes
            invoice_cache[user_id]['media_type_for_save'] = media_type
            
            # 確保 usage 字典有這些鍵，避免 KeyError
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)

            input_cost = (prompt_tokens / 1_000_000) * 5.0
            output_cost = (completion_tokens / 1_000_000) * 15.0
            total_cost_usd = input_cost + output_cost
            total_cost_twd = total_cost_usd * 32
            cost_text = f"\n(本次辨識成本約 NT$ {total_cost_twd:.4f})"

            confirm_text = (f"發票辨識結果如下，請確認：\n"
                            f"項目: {invoice_data['transaction_type']}\n"
                            f"賣方統編: {invoice_data['seller_id']}\n"
                            f"發票號碼: {invoice_data['invoice_number']}\n"
                            f"日期: {invoice_data['invoice_date']}\n"
                            f"金額: {invoice_data['account']}\n"
                            f"格式: {invoice_data['invoice_type']}\n" # 新增格式欄位
                            f"品項: {invoice_data['invoice_description'][:60]}"
                            f"{cost_text}")

            confirm_template = ConfirmTemplate(text=confirm_text, actions=[
                PostbackAction(label='確認儲存', data=f'action=save_invoice&user_id={user_id}'),
                PostbackAction(label='編輯發票', data=f'action=edit_invoice&user_id={user_id}') # 將取消改為編輯發票
            ])
            await _send_confirm_card(user_id, invoice_data)
        except Exception as e:
            logger.error(f"發票處理流程出錯: {e}")
            await line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text='抱歉，辨識發票時發生錯誤。')])) # 使用 await
        finally:
            if user_id in user_states: del user_states[user_id]

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
                # Send "好的正在儲存" message
                # 改為發送載入動畫，取代原本的 "正在儲存" 訊息
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(executor, partial(send_loading_animation, user_id))
                try:
                    # Retrieve file_data and media_type from cache
                    file_data_for_save = invoice_cache[user_id].get('file_data_for_save')
                    media_type_for_save = invoice_cache[user_id].get('media_type_for_save')

                    if file_data_for_save and media_type_for_save:
                        # 將同步的 save_invoice_data 放入線程池中執行，避免阻塞事件循環
                        loop = asyncio.get_running_loop()
                        spreadsheet_url = await loop.run_in_executor(
                            executor,
                            partial(invoice_processor.save_invoice_data,
                                    invoice_cache[user_id], file_data_for_save, media_type_for_save)
                        )
                        reply_text = f"✅ 發票已成功儲存！\n🔗試算表連結: {spreadsheet_url}"
                    else:
                        reply_text = "❌ 儲存發票資料失敗：缺少檔案資料。"
                        logger.error("儲存發票資料失敗：invoice_cache 中缺少檔案資料。")
                    
                except Exception as save_e:
                    logger.error(f"儲存發票資料時發生錯誤: {save_e}")
                    reply_text = "❌ 儲存發票資料失敗。"
                finally:
                    del invoice_cache[user_id] # Always clear cache after attempt
            else:
                reply_text = "抱歉，找不到您的發票資料，可能已逾時，請重新操作。"
            
            # Clear user state and return to main menu after save attempt
            if user_id in user_states: del user_states[user_id]
            # Use push_message to send final reply and quick reply for main menu
            async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
                await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[ # 使用 await 和 AsyncMessagingApi
                    TextMessage(text=reply_text, quick_reply=QuickReply(items=[
                        QuickReplyItem(action=MessageAction(label="財稅QA", text="財稅QA")),
                        QuickReplyItem(action=MessageAction(label="發票記帳", text="發票記帳")),
                    ]))
                ]))
            return # 確保沒有其他訊息被發送
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
            async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
                await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[ # 使用 await 和 AsyncMessagingApi
                    TextMessage(text=reply_text, quick_reply=QuickReply(items=[
                        QuickReplyItem(action=MessageAction(label="財稅QA", text="財稅QA")),
                        QuickReplyItem(action=MessageAction(label="發票記帳", text="發票記帳")),
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
                    'invoice_description': '品項'
                }
                quick_reply_items = []
                for key, label in field_mapping.items():
                    quick_reply_items.append(
                        QuickReplyItem(action=PostbackAction(label=label, data=f'action=select_field&user_id={user_id}&field={key}'))
                    )
                
                async with AsyncApiClient(configuration) as api_client:
                    await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[
                        TextMessage(text=reply_text, quick_reply=QuickReply(items=quick_reply_items))
                    ]))
                user_states[user_id] = 'editing_invoice' # 設置使用者狀態為編輯中
            else:
                reply_text = "抱歉，找不到您的發票資料，可能已逾時，請重新操作。"
                async with AsyncApiClient(configuration) as api_client:
                    await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)]))
            return # 確保沒有其他訊息被發送
        elif action == 'select_field':
            field_to_edit = params.get('field')
            if user_id in invoice_cache and field_to_edit:
                user_states[user_id] = f'editing_field_{field_to_edit}'
                reply_text = f"請輸入新的「{field_to_edit}」資訊："
                async with AsyncApiClient(configuration) as api_client:
                    await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)]))
            else:
                reply_text = "抱歉，找不到您的發票資料或欄位資訊，可能已逾時，請重新操作。"
                async with AsyncApiClient(configuration) as api_client:
                    await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)]))
            return # 確保沒有其他訊息被發送
        elif action == 'cancel_invoice':
            reply_text = "操作已取消。"
            if user_id in invoice_cache: del invoice_cache[user_id]
        if user_id in user_states: del user_states[user_id]
    except Exception as e:
        logger.error(f"Postback 處理失敗: {e}")
        reply_text = "處理您的請求時發生錯誤。"

    if reply_text: # This block should now only be hit for 'edit_invoice' or 'select_field' failures, or general exceptions
        async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
            await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])) # 使用 await 和 AsyncMessagingApi

@handler.add(FollowEvent)
async def handle_follow(event: FollowEvent): # 將函數改為 async
    async with AsyncApiClient(configuration) as api_client: # 使用 AsyncApiClient
        await reply_main_menu(api_client, event.reply_token) # 使用 await

async def _send_confirm_card(user_id: str, invoice_data: Dict):
    """發送包含發票資訊的確認卡片"""
    # 確保 usage 字典有這些鍵，避免 KeyError
    prompt_tokens = invoice_data.get('usage', {}).get('prompt_tokens', 0)
    completion_tokens = invoice_data.get('usage', {}).get('completion_tokens', 0)

    input_cost = (prompt_tokens / 1_000_000) * 5.0
    output_cost = (completion_tokens / 1_000_000) * 15.0
    total_cost_usd = input_cost + output_cost
    total_cost_twd = total_cost_usd * 32
    cost_text = f"\n(本次辨識成本約 NT$ {total_cost_twd:.4f})"

    confirm_text = (f"發票辨識結果如下，請確認：\n"
                    f"項目: {invoice_data['transaction_type']}\n"
                    f"賣方統編: {invoice_data['seller_id']}\n"
                    f"發票號碼: {invoice_data['invoice_number']}\n"
                    f"日期: {invoice_data['invoice_date']}\n"
                    f"金額: {invoice_data['account']}\n"
                    f"格式: {invoice_data['invoice_type']}\n"
                    f"品項: {invoice_data['invoice_description'][:60]}"
                    f"{cost_text}")

    confirm_template = ConfirmTemplate(text=confirm_text, actions=[
        PostbackAction(label='確認儲存', data=f'action=save_invoice&user_id={user_id}'),
        PostbackAction(label='編輯發票', data=f'action=edit_invoice&user_id={user_id}')
    ])
    
    async with AsyncApiClient(configuration) as api_client:
        await AsyncMessagingApi(api_client).push_message(PushMessageRequest(to=user_id, messages=[TemplateMessage(alt_text='發票辨識結果確認', template=confirm_template)]))

# --- 主程式啟動 ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('LINE_BOT_PORT', '8013'))
    uvicorn.run(app, host="0.0.0.0", port=port)