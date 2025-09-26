"""
LINE API 客戶端封裝 - 消除重複的API調用代碼
"""

import logging
from typing import List, Dict, Optional
import aiohttp

from linebot.v3.messaging import (
    AsyncApiClient, AsyncMessagingApi, ReplyMessageRequest, PushMessageRequest,
    TextMessage, TemplateMessage
)
from linebot.v3.messaging.models import (
    QuickReply, QuickReplyItem, MessageAction, PostbackAction, ConfirmTemplate
)

logger = logging.getLogger(__name__)

class LineClient:
    """LINE API 客戶端 - 統一的回應接口"""

    def __init__(self, api_client: AsyncApiClient, access_token: str):
        self.api_client = api_client
        self.messaging_api = AsyncMessagingApi(api_client)
        self.access_token = access_token

    async def reply_text(
        self,
        reply_token: str,
        text: str,
        quick_replies: Optional[List[Dict[str, str]]] = None
    ):
        """回覆文字訊息 - 統一接口"""
        message = TextMessage(text=text)

        if quick_replies:
            quick_reply_items = [
                QuickReplyItem(action=MessageAction(
                    label=item["label"],
                    text=item["text"]
                ))
                for item in quick_replies
            ]
            message.quick_reply = QuickReply(items=quick_reply_items)

        try:
            await self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[message]
                )
            )
        except Exception as e:
            logger.error(f"回覆訊息失敗: {e}")
            raise

    async def push_text(
        self,
        user_id: str,
        text: str,
        quick_replies: Optional[List[Dict[str, str]]] = None
    ):
        """推送文字訊息"""
        message = TextMessage(text=text)

        if quick_replies:
            quick_reply_items = [
                QuickReplyItem(action=MessageAction(
                    label=item["label"],
                    text=item["text"]
                ))
                for item in quick_replies
            ]
            message.quick_reply = QuickReply(items=quick_reply_items)

        try:
            await self.messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[message]
                )
            )
        except Exception as e:
            logger.error(f"推送訊息失敗: {e}")
            raise

    async def send_loading_animation(self, user_id: str, seconds: int = 30):
        """發送載入動畫"""
        url = "https://api.line.me/v2/bot/chat/loading/start"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        data = {
            "chatId": user_id,
            "loadingSeconds": seconds
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as resp:
                    if resp.status not in [200, 202]:
                        logger.warning(f"載入動畫發送失敗: {resp.status}")
        except Exception as e:
            logger.error(f"發送載入動畫失敗: {e}")

    async def reply_confirm_template(
        self,
        reply_token: str,
        text: str,
        confirm_label: str,
        confirm_data: str,
        cancel_label: str,
        cancel_data: str,
        alt_text: str = "確認訊息"
    ):
        """回覆確認卡片"""
        confirm_template = ConfirmTemplate(
            text=text,
            actions=[
                PostbackAction(label=confirm_label, data=confirm_data),
                PostbackAction(label=cancel_label, data=cancel_data)
            ]
        )

        try:
            await self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TemplateMessage(alt_text=alt_text, template=confirm_template)]
                )
            )
        except Exception as e:
            logger.error(f"回覆確認卡片失敗: {e}")
            raise

    async def reply_main_menu(self, reply_token: str):
        """回覆主選單 - 4個核心服務"""
        quick_replies = [
            {"label": "QA問答", "text": "QA問答"},
            {"label": "照片記帳", "text": "照片記帳"},
            {"label": "財務分析", "text": "財務分析"},
            {"label": "記事提醒", "text": "記事提醒"}
        ]

        await self.reply_text(
            reply_token=reply_token,
            text="您好！請問需要什麼服務？",
            quick_replies=quick_replies
        )