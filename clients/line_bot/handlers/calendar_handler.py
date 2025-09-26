"""
記事提醒處理器
"""

import logging
from .base_handler import BaseHandler, HandlerResponse

logger = logging.getLogger(__name__)

class CalendarHandler(BaseHandler):
    """記事提醒處理器"""

    def __init__(self):
        super().__init__("記事提醒")
        self.calendar_service = None
        self._initialize_service()

    def _initialize_service(self):
        """初始化行事曆服務"""
        try:
            import os
            from services.google_auth_service.main import GoogleAuthProcessor
            base_url = os.getenv('GOOGLE_AUTH_BASE_URL', 'http://localhost:8080')
            self.calendar_service = GoogleAuthProcessor(base_url=base_url)
            logger.info("行事曆服務初始化成功")
        except Exception as e:
            logger.error(f"行事曆服務初始化失敗: {e}")
            self.calendar_service = None

    async def enter_mode(self, user_id: str) -> HandlerResponse:
        """進入記事提醒模式"""
        if not self.calendar_service:
            return HandlerResponse(
                text="記事提醒服務暫時無法使用，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

        # 檢查用戶是否已綁定Google帳號
        if self.calendar_service.is_user_bound(user_id):
            return HandlerResponse(
                text="記事提醒功能選單：",
                quick_replies=[
                    self.create_quick_reply("今天行程", "今天行程"),
                    self.create_quick_reply("本週行程", "本週行程"),
                    self.create_quick_reply("記事設定", "記事設定"),
                    self.create_quick_reply("解除綁定", "解除綁定"),
                    self.create_quick_reply("返回主選單", "返回主選單")
                ]
            )
        else:
            return HandlerResponse(
                text="您尚未綁定 Google 帳號。請點選「綁定 Google 帳號」開始設定，即可使用記事提醒功能。",
                quick_replies=[
                    self.create_quick_reply("綁定 Google 帳號", "綁定 Google 帳號"),
                    self.create_quick_reply("返回主選單", "返回主選單")
                ]
            )

    async def handle_message(self, user_id: str, message: str) -> HandlerResponse:
        """處理記事相關訊息"""
        if not self.calendar_service:
            return HandlerResponse(
                text="記事提醒服務暫時無法使用，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

        try:
            if message == "綁定 Google 帳號":
                return await self._handle_bind_google(user_id)

            elif message == "今天行程":
                return await self._handle_today_events(user_id)

            elif message == "本週行程":
                return await self._handle_weekly_events(user_id)

            elif message == "記事設定":
                return await self._handle_settings(user_id)

            elif message == "解除綁定":
                return await self._handle_unbind(user_id)

            else:
                return HandlerResponse(
                    text="請選擇記事提醒功能，或輸入「返回主選單」離開。",
                    quick_replies=self.create_exit_reply()
                )

        except Exception as e:
            logger.error(f"記事處理失敗: {e}")
            return HandlerResponse(
                text="處理記事功能時發生錯誤，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

    async def handle_file(self, user_id: str, file_data: bytes, media_type: str) -> HandlerResponse:
        """記事提醒不支持文件處理"""
        return HandlerResponse(
            text="記事提醒功能不支持文件上傳，請使用選單功能。",
            quick_replies=self.create_exit_reply()
        )

    async def _handle_bind_google(self, user_id: str) -> HandlerResponse:
        """處理Google帳號綁定"""
        try:
            auth_url = self.calendar_service.start_oauth_flow(user_id)
            return HandlerResponse(
                text=f"請點擊以下連結在瀏覽器中完成 Google 帳號授權：\n{auth_url}\n\n授權完成後，請輸入「檢查綁定狀態」確認設定。",
                quick_replies=[
                    self.create_quick_reply("檢查綁定狀態", "檢查綁定狀態"),
                    self.create_quick_reply("返回主選單", "返回主選單")
                ]
            )
        except Exception as e:
            logger.error(f"啟動Google授權失敗: {e}")
            return HandlerResponse(
                text="啟動授權過程失敗，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

    async def _handle_today_events(self, user_id: str) -> HandlerResponse:
        """處理今天行程查詢"""
        if not self.calendar_service.is_user_bound(user_id):
            return HandlerResponse(
                text="請先綁定 Google 帳號才能查看行程。",
                quick_replies=self.create_exit_reply()
            )

        try:
            today_events = self.calendar_service.get_today_events(user_id)
            if today_events:
                formatted_text = self.calendar_service.format_events_for_line(today_events)
                reply_text = f"📅 今天的行程：\n{formatted_text}"
            else:
                reply_text = "📅 今天沒有行程安排。"

            return HandlerResponse(
                text=reply_text,
                quick_replies=self.create_exit_reply(),
                needs_loading=True
            )
        except Exception as e:
            logger.error(f"取得今天行程失敗: {e}")
            return HandlerResponse(
                text="取得行程時發生錯誤，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

    async def _handle_weekly_events(self, user_id: str) -> HandlerResponse:
        """處理本週行程查詢"""
        if not self.calendar_service.is_user_bound(user_id):
            return HandlerResponse(
                text="請先綁定 Google 帳號才能查看行程。",
                quick_replies=self.create_exit_reply()
            )

        try:
            upcoming_events = self.calendar_service.get_upcoming_events(user_id, limit=20)
            if upcoming_events:
                formatted_text = self.calendar_service.format_events_for_line(upcoming_events)
                reply_text = f"📅 本週行程預覽：\n{formatted_text}"
            else:
                reply_text = "📅 本週沒有行程安排。"

            return HandlerResponse(
                text=reply_text,
                quick_replies=self.create_exit_reply(),
                needs_loading=True
            )
        except Exception as e:
            logger.error(f"取得本週行程失敗: {e}")
            return HandlerResponse(
                text="取得行程時發生錯誤，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )

    async def _handle_settings(self, user_id: str) -> HandlerResponse:
        """處理記事設定"""
        if not self.calendar_service.is_user_bound(user_id):
            return HandlerResponse(
                text="請先綁定 Google 帳號才能設定行事曆。",
                quick_replies=self.create_exit_reply()
            )

        status = self.calendar_service.get_user_binding_status(user_id)
        selected_count = len(status.get('selected_calendars', []))

        return HandlerResponse(
            text=f"📊 記事設定狀態：\n✅ Google 帳號：{status['email']}\n📅 已選擇行事曆：{selected_count} 個\n📱 行事曆存取：{'正常' if status['calendar_access'] else '異常'}",
            quick_replies=[
                self.create_quick_reply("重新選擇行事曆", "選擇行事曆"),
                self.create_quick_reply("解除綁定", "解除綁定"),
                self.create_quick_reply("返回主選單", "返回主選單")
            ]
        )

    async def _handle_unbind(self, user_id: str) -> HandlerResponse:
        """處理解除綁定"""
        if self.calendar_service.unbind_user(user_id):
            return HandlerResponse(
                text="✅ 已成功解除 Google 帳號綁定。",
                quick_replies=self.create_exit_reply()
            )
        else:
            return HandlerResponse(
                text="❌ 解除綁定失敗，請稍後再試。",
                quick_replies=self.create_exit_reply()
            )