#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google 授權服務主程式
處理 Google OAuth 和 Calendar 功能
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple

# 將專案根目錄添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .services.oauth_service import GoogleOAuthService
from .services.calendar_service import CalendarService

logger = logging.getLogger(__name__)

class GoogleAuthProcessor:
    """Google 授權處理器 - 主要的對外介面"""

    def __init__(self, client_secrets_path: str = None, base_url: str = None):
        """
        初始化處理器

        Args:
            client_secrets_path: Google OAuth client secrets 檔案路徑
            base_url: 服務的基礎 URL
        """
        # 設定預設路徑
        if not client_secrets_path:
            client_secrets_path = os.path.join(
                os.path.dirname(__file__), '..', '..',
                'config', 'gmail_accounts', 'itsdoryhsu',
                'client_secret_865894595003-1tp7pt3rdn0ku3cb1sd8dac9gjdt8qu3.apps.googleusercontent.com.json'
            )

        if not base_url:
            # 從環境變數取得或使用預設值
            base_url = os.getenv('GOOGLE_AUTH_BASE_URL', 'http://localhost:8080')

        # 初始化服務
        self.oauth_service = GoogleOAuthService(client_secrets_path, base_url)
        self.calendar_service = CalendarService(self.oauth_service)

        logger.info(f"GoogleAuthProcessor 已初始化，base_url: {base_url}")

    def start_oauth_flow(self, line_user_id: str) -> str:
        """
        啟動 OAuth 流程

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            OAuth 授權 URL
        """
        return self.oauth_service.start_oauth_flow(line_user_id)

    def handle_oauth_callback(self, code: str, state: str) -> Tuple[bool, str, Optional[str]]:
        """
        處理 OAuth callback

        Args:
            code: 授權碼
            state: state 參數

        Returns:
            (success, message, line_user_id)
        """
        return self.oauth_service.handle_oauth_callback(code, state)

    def is_user_bound(self, line_user_id: str) -> bool:
        """檢查用戶是否已綁定 Google 帳號"""
        return self.oauth_service.is_user_bound(line_user_id)

    def get_user_email(self, line_user_id: str) -> Optional[str]:
        """取得用戶的 Google Email"""
        return self.oauth_service.get_user_email(line_user_id)

    def unbind_user(self, line_user_id: str) -> bool:
        """解除用戶綁定"""
        return self.oauth_service.unbind_user(line_user_id)

    def test_calendar_access(self, line_user_id: str) -> Tuple[bool, str]:
        """測試行事曆存取權限"""
        return self.calendar_service.test_calendar_access(line_user_id)

    def get_calendar_list(self, line_user_id: str) -> List[Dict]:
        """取得用戶的行事曆列表"""
        return self.calendar_service.get_calendar_list(line_user_id)

    def get_today_events(self, line_user_id: str) -> List[Dict]:
        """取得今天的事件"""
        return self.calendar_service.get_today_events(line_user_id)

    def get_upcoming_events(self, line_user_id: str, limit: int = 10) -> List[Dict]:
        """取得即將到來的事件"""
        return self.calendar_service.get_upcoming_events(line_user_id, limit)

    def get_events_by_days(self, line_user_id: str, days_ahead: int = 7) -> List[Dict]:
        """取得未來指定天數的事件"""
        return self.calendar_service.get_events(line_user_id, 'primary', days_ahead)

    def format_events_for_line(self, events: List[Dict]) -> str:
        """
        將事件格式化為適合 LINE 顯示的文字

        Args:
            events: 事件列表

        Returns:
            格式化後的文字
        """
        if not events:
            return "沒有找到任何事件。"

        text_lines = []
        current_date = None

        for event in events:
            try:
                start_dt = event['start_datetime']
                event_date = start_dt.strftime('%Y-%m-%d')

                # 如果是新的日期，加入日期標題
                if event_date != current_date:
                    current_date = event_date
                    date_str = start_dt.strftime('%m/%d (%a)')
                    text_lines.append(f"\n📅 {date_str}")

                # 事件時間和標題
                time_str = event['time_str']
                summary = event['summary']

                # 地點資訊
                location = event.get('location', '')
                location_str = f" @ {location}" if location else ""

                text_lines.append(f"⏰ {time_str} - {summary}{location_str}")

            except Exception as e:
                logger.error(f"Failed to format event: {e}")
                continue

        return '\n'.join(text_lines)

    def get_user_binding_status(self, line_user_id: str) -> Dict:
        """
        取得用戶綁定狀態的詳細資訊

        Returns:
            包含綁定狀態的字典
        """
        is_bound = self.is_user_bound(line_user_id)

        if not is_bound:
            return {
                'is_bound': False,
                'email': None,
                'calendar_access': False,
                'message': '尚未綁定 Google 帳號'
            }

        email = self.get_user_email(line_user_id)
        calendar_success, calendar_message = self.test_calendar_access(line_user_id)
        selected_calendars = self.oauth_service.get_selected_calendars(line_user_id)

        return {
            'is_bound': True,
            'email': email,
            'calendar_access': calendar_success,
            'selected_calendars': selected_calendars,
            'message': f'已綁定帳號：{email}' if email else '已綁定但無法取得 email'
        }

    def save_calendar_selection(self, line_user_id: str, calendar_ids: List[str]) -> bool:
        """儲存用戶選擇的行事曆"""
        return self.oauth_service.save_selected_calendars(line_user_id, calendar_ids)

    def get_available_calendars(self, line_user_id: str) -> List[Dict]:
        """取得可用的行事曆列表供用戶選擇"""
        return self.calendar_service.get_calendar_list(line_user_id)


def create_fastapi_routes():
    """建立 FastAPI 路由 (供外部使用)"""
    from .services.web_routes import create_oauth_routes

    # 初始化服務
    processor = GoogleAuthProcessor()

    # 建立路由
    return create_oauth_routes(processor.oauth_service)


if __name__ == "__main__":
    # 用於測試
    import asyncio

    async def test_flow():
        processor = GoogleAuthProcessor()

        # 測試用戶 ID
        test_user_id = "test_user_123"

        print("=== Google Auth Service 測試 ===")

        # 檢查綁定狀態
        status = processor.get_user_binding_status(test_user_id)
        print(f"綁定狀態: {status}")

        if not status['is_bound']:
            # 啟動 OAuth 流程
            auth_url = processor.start_oauth_flow(test_user_id)
            print(f"請在瀏覽器中開啟以下 URL 進行授權:")
            print(auth_url)
        else:
            # 測試行事曆功能
            print("\n=== 測試行事曆功能 ===")

            # 取得今天的事件
            today_events = processor.get_today_events(test_user_id)
            print(f"今天的事件數量: {len(today_events)}")

            if today_events:
                formatted_text = processor.format_events_for_line(today_events)
                print("格式化後的事件:")
                print(formatted_text)

    asyncio.run(test_flow())