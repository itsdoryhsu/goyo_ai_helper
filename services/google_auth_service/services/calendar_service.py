import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from .oauth_service import GoogleOAuthService

logger = logging.getLogger(__name__)

class CalendarService:
    """Google Calendar 服務"""

    def __init__(self, oauth_service: GoogleOAuthService):
        self.oauth_service = oauth_service

    def get_calendar_list(self, line_user_id: str) -> List[Dict]:
        """取得用戶的行事曆列表"""
        service = self.oauth_service.get_calendar_service(line_user_id)
        if not service:
            return []

        try:
            calendars = service.calendarList().list().execute()
            calendar_list = []

            for calendar in calendars.get('items', []):
                calendar_list.append({
                    'id': calendar['id'],
                    'summary': calendar['summary'],
                    'primary': calendar.get('primary', False),
                    'access_role': calendar.get('accessRole', 'reader')
                })

            return calendar_list
        except Exception as e:
            logger.error(f"Failed to get calendar list for {line_user_id}: {e}")
            return []

    def get_events(self, line_user_id: str, calendar_id: str = 'primary',
                   days_ahead: int = 7) -> List[Dict]:
        """
        取得行事曆事件

        Args:
            line_user_id: LINE 用戶 ID
            calendar_id: 行事曆 ID，預設為主要行事曆
            days_ahead: 取得未來幾天的事件
        """
        service = self.oauth_service.get_calendar_service(line_user_id)
        if not service:
            return []

        try:
            # 計算時間範圍
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            event_list = []

            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                event_list.append({
                    'id': event['id'],
                    'summary': event.get('summary', '無標題'),
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': event.get('attendees', [])
                })

            return event_list
        except Exception as e:
            logger.error(f"Failed to get events for {line_user_id}: {e}")
            return []

    def get_today_events(self, line_user_id: str) -> List[Dict]:
        """取得今天的事件"""
        service = self.oauth_service.get_calendar_service(line_user_id)
        if not service:
            return []

        try:
            # 今天的開始和結束時間
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            time_min = today_start.isoformat() + 'Z'
            time_max = today_end.isoformat() + 'Z'

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            return self._format_events(events)

        except Exception as e:
            logger.error(f"Failed to get today's events for {line_user_id}: {e}")
            return []

    def get_upcoming_events(self, line_user_id: str, limit: int = 10, days_ahead: int = 7) -> List[Dict]:
        """
        取得即將到來的事件（從選擇的行事曆）

        Args:
            line_user_id: LINE 用戶 ID
            limit: 最多回傳的事件數量
            days_ahead: 取得未來幾天的事件（預設7天）
        """
        service = self.oauth_service.get_calendar_service(line_user_id)
        if not service:
            return []

        # 取得用戶選擇的行事曆
        selected_calendars = self.oauth_service.get_selected_calendars(line_user_id)
        if not selected_calendars:
            selected_calendars = ['primary']  # 預設使用主要行事曆

        try:
            # 設定時間範圍：從現在開始到未來指定天數
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

            all_events = []

            # 從每個選擇的行事曆讀取事件
            for calendar_id in selected_calendars:
                try:
                    events_result = service.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,  # 新增時間上限
                        maxResults=50,  # 增加最大數量以確保在時間範圍內取得足夠事件
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()

                    events = events_result.get('items', [])
                    all_events.extend(events)
                except Exception as e:
                    logger.warning(f"Failed to get events from calendar {calendar_id}: {e}")
                    continue

            # 依時間排序並限制數量
            all_events.sort(key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
            return self._format_events(all_events[:limit])

        except Exception as e:
            logger.error(f"Failed to get upcoming events for {line_user_id}: {e}")
            return []

    def _format_events(self, events: List[Dict]) -> List[Dict]:
        """格式化事件資料"""
        formatted_events = []

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            # 解析時間
            try:
                if 'T' in start:  # 有時間的事件
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    time_str = start_dt.strftime('%H:%M')
                    is_all_day = False
                else:  # 全天事件
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                    time_str = '全天'
                    is_all_day = True

                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', '無標題'),
                    'start': start,
                    'end': end,
                    'start_datetime': start_dt,
                    'end_datetime': end_dt,
                    'time_str': time_str,
                    'is_all_day': is_all_day,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': event.get('attendees', [])
                })
            except Exception as e:
                logger.error(f"Failed to parse event time: {e}")
                continue

        return formatted_events

    def test_calendar_access(self, line_user_id: str) -> tuple[bool, str]:
        """測試行事曆存取權限"""
        service = self.oauth_service.get_calendar_service(line_user_id)
        if not service:
            return False, "無法取得 Google 憑證"

        try:
            # 嘗試列出行事曆
            calendars = service.calendarList().list(maxResults=5).execute()
            calendar_count = len(calendars.get('items', []))
            return True, f"成功存取行事曆，找到 {calendar_count} 個行事曆"
        except Exception as e:
            logger.error(f"Calendar access test failed for {line_user_id}: {e}")
            return False, f"行事曆存取失敗：{str(e)}"