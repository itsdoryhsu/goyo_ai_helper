import os
import json
import uuid
import sqlite3
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

class GoogleOAuthService:
    """Google OAuth 服務，處理用戶授權與帳號綁定"""

    # Scopes for reading calendar and events (Google may add additional scopes automatically)
    SCOPES = [
        'openid',  # Google 自動添加的 OpenID Connect scope
        'https://www.googleapis.com/auth/calendar.readonly',        # 讀取行事曆（包含 calendarList）
        'https://www.googleapis.com/auth/calendar.events.readonly', # Google 可能自動添加
        'https://www.googleapis.com/auth/userinfo.email'            # 取得用戶 email 用於識別
    ]

    def __init__(self, client_secrets_path: str, base_url: str):
        """
        初始化 OAuth 服務

        Args:
            client_secrets_path: Google OAuth client secrets 檔案路徑
            base_url: 服務的基礎 URL
        """
        self.client_secrets_path = client_secrets_path
        self.base_url = base_url
        self.redirect_uri = f"{base_url}/oauth/callback"
        self.db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'user_bindings.sqlite')
        self._init_database()

    def _init_database(self):
        """初始化資料庫"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # 建立主表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_bindings (
                    line_user_id TEXT PRIMARY KEY,
                    google_email TEXT,
                    google_credentials TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 檢查並添加 selected_calendars 欄位（如果不存在）
            cursor = conn.execute("PRAGMA table_info(user_bindings)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'selected_calendars' not in columns:
                conn.execute("""
                    ALTER TABLE user_bindings
                    ADD COLUMN selected_calendars TEXT
                """)
                logger.info("Added selected_calendars column to user_bindings table")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    line_user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            conn.commit()

    def start_oauth_flow(self, line_user_id: str) -> str:
        """
        啟動 OAuth 流程，返回授權 URL

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            OAuth 授權 URL
        """
        try:
            # 建立 OAuth flow
            flow = Flow.from_client_secrets_file(
                self.client_secrets_path,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )

            # 產生 state 參數
            state = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=10)

            # 儲存 state 與 LINE user ID 的關聯
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO oauth_states
                    (state, line_user_id, expires_at)
                    VALUES (?, ?, ?)
                """, (state, line_user_id, expires_at))
                conn.commit()

            # 產生授權 URL
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'
            )

            logger.info(f"OAuth flow started for LINE user {line_user_id}")
            return authorization_url

        except Exception as e:
            logger.error(f"Failed to start OAuth flow: {e}")
            raise

    def handle_oauth_callback(self, code: str, state: str) -> Tuple[bool, str, Optional[str]]:
        """
        處理 OAuth callback

        Args:
            code: 授權碼
            state: state 參數

        Returns:
            (success, message, line_user_id)
        """
        try:
            # 驗證 state
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT line_user_id, expires_at FROM oauth_states
                    WHERE state = ?
                """, (state,))
                result = cursor.fetchone()

                if not result:
                    return False, "無效的授權狀態", None

                line_user_id, expires_at_str = result
                expires_at = datetime.fromisoformat(expires_at_str)

                if datetime.now() > expires_at:
                    return False, "授權已過期，請重新嘗試", None

                # 清除已使用的 state
                conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
                conn.commit()

            # 使用授權碼換取 token
            flow = Flow.from_client_secrets_file(
                self.client_secrets_path,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri,
                state=state
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            # 取得用戶資訊
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            user_email = user_info.get('email')

            # 儲存綁定資料
            self._save_user_binding(line_user_id, user_email, credentials)

            logger.info(f"OAuth successful for LINE user {line_user_id}, Google email: {user_email}")
            return True, f"成功綁定 Google 帳號：{user_email}", line_user_id

        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")
            return False, "授權過程發生錯誤", None

    def _save_user_binding(self, line_user_id: str, google_email: str, credentials: Credentials, selected_calendars: List[str] = None):
        """儲存用戶綁定資料"""
        import json
        calendars_json = json.dumps(selected_calendars) if selected_calendars else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_bindings
                (line_user_id, google_email, google_credentials, selected_calendars, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (line_user_id, google_email, credentials.to_json(), calendars_json))
            conn.commit()

    def save_selected_calendars(self, line_user_id: str, calendar_ids: List[str]) -> bool:
        """儲存用戶選擇的行事曆"""
        import json
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE user_bindings
                    SET selected_calendars = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE line_user_id = ?
                """, (json.dumps(calendar_ids), line_user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save selected calendars for {line_user_id}: {e}")
            return False

    def get_selected_calendars(self, line_user_id: str) -> List[str]:
        """取得用戶選擇的行事曆 IDs"""
        import json
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT selected_calendars FROM user_bindings
                    WHERE line_user_id = ?
                """, (line_user_id,))
                result = cursor.fetchone()

                if result and result[0]:
                    return json.loads(result[0])
                return []
        except Exception as e:
            logger.error(f"Failed to get selected calendars for {line_user_id}: {e}")
            return []

    def get_user_credentials(self, line_user_id: str) -> Optional[Credentials]:
        """取得用戶的 Google 憑證"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT google_credentials FROM user_bindings
                    WHERE line_user_id = ?
                """, (line_user_id,))
                result = cursor.fetchone()

                if not result:
                    return None

                credentials = Credentials.from_authorized_user_info(
                    json.loads(result[0])
                )

                # 檢查並刷新憑證
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(GoogleAuthRequest())
                    self._save_user_binding(line_user_id,
                                          self.get_user_email(line_user_id),
                                          credentials)

                return credentials

        except Exception as e:
            logger.error(f"Failed to get credentials for {line_user_id}: {e}")
            return None

    def get_user_email(self, line_user_id: str) -> Optional[str]:
        """取得用戶的 Google Email"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT google_email FROM user_bindings
                    WHERE line_user_id = ?
                """, (line_user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get user email for {line_user_id}: {e}")
            return None

    def is_user_bound(self, line_user_id: str) -> bool:
        """檢查用戶是否已綁定"""
        return self.get_user_email(line_user_id) is not None

    def unbind_user(self, line_user_id: str) -> bool:
        """解除用戶綁定"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM user_bindings WHERE line_user_id = ?
                """, (line_user_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Failed to unbind user {line_user_id}: {e}")
            return False

    def get_calendar_service(self, line_user_id: str):
        """取得 Google Calendar 服務"""
        credentials = self.get_user_credentials(line_user_id)
        if not credentials:
            return None

        try:
            return build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to build calendar service: {e}")
            return None