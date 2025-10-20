from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
import io
import os
import json
try:
    from ..config.settings import DRIVE_SCOPES, SUPPORTED_IMAGE_EXTENSIONS, FOLDER_ID, INVOICE_DRIVE_FOLDER_NAME
    from ..config.settings import GOOGLE_APPLICATION_CREDENTIALS
except ImportError:
    # 當從其他服務導入時，使用絕對導入
    from services.invoice_service.config import DRIVE_SCOPES, SUPPORTED_IMAGE_EXTENSIONS, FOLDER_ID, INVOICE_DRIVE_FOLDER_NAME
    from services.invoice_service.config import GOOGLE_APPLICATION_CREDENTIALS

class DriveService:
    def __init__(self):
        self.service = self._setup_service()
        # 優先使用 .env 中設定的 FOLDER_ID
        if FOLDER_ID:
            self.invoice_folder_id = FOLDER_ID
            print(f"使用來自 .env 的指定資料夾 ID: {self.invoice_folder_id}")
        else:
            # 如果 .env 中未設定，則退回原有邏輯
            print("在 .env 中未找到 FOLDER_ID，將嘗試尋找或建立 '發票檔案' 資料夾。")
            self.invoice_folder_id = self._get_or_create_folder(INVOICE_DRIVE_FOLDER_NAME)

    def _setup_service(self):
        """設定 Google Drive 服務"""
        # 支援 JSON 字符串和檔案路徑兩種認證方式
        creds_data = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', GOOGLE_APPLICATION_CREDENTIALS)

        try:
            # 嘗試解析為 JSON 字符串
            creds_dict = json.loads(creds_data)
            creds = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=DRIVE_SCOPES
            )
        except json.JSONDecodeError:
            # 如果不是 JSON，當作檔案路徑處理
            PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            credentials_path = os.path.join(PROJECT_ROOT, creds_data)
            creds = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=DRIVE_SCOPES
            )

        return build("drive", "v3", credentials=creds)

    def _get_or_create_folder(self, folder_name):
        """取得或建立指定名稱的資料夾，並回傳其 ID"""
        try:
            # 搜尋資料夾
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            folders = results.get("files", [])
            if folders:
                print(f"找到現有資料夾: {folder_name} (ID: {folders[0]['id']})")
                return folders[0]['id']
            else:
                # 建立資料夾
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                print(f"已建立新資料夾: {folder_name} (ID: {folder['id']})")
                return folder['id']
        except HttpError as error:
            print(f"取得或建立資料夾時發生錯誤: {error}")
            return None
    
    def get_invoice_files(self):
        """取得資料夾中的圖片和 PDF 檔案"""
        try:
            query = f"""'{FOLDER_ID}' in parents and trashed=false and (
                mimeType contains 'image/' or 
                name contains '.png' or 
                name contains '.jpg' or 
                name contains '.jpeg' or 
                name contains '.gif' or 
                name contains '.bmp' or
                mimeType='application/pdf' or 
                name contains '.pdf'
            )"""
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get("files", [])
            
            # 分類檔案類型
            image_files = []
            pdf_files = []
            
            for file in files:
                mime_type = file.get('mimeType', '')
                name = file.get('name', '').lower()
                
                if ('image/' in mime_type or 
                    any(ext in name for ext in SUPPORTED_IMAGE_EXTENSIONS)):
                    image_files.append(file)
                elif (mime_type == 'application/pdf' or '.pdf' in name):
                    pdf_files.append(file)
            
            print(f"找到 {len(image_files)} 個圖片檔案")
            print(f"找到 {len(pdf_files)} 個 PDF 檔案")
            print(f"總共 {len(files)} 個檔案")
            
            return image_files + pdf_files
            
        except HttpError as error:
            print(f"取得檔案時發生錯誤: {error}")
            return []
    
    def download_file(self, file_id):
        """下載檔案"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_io.seek(0)
            return file_io.read()
            
        except Exception as e:
            print(f"下載檔案時發生錯誤: {e}")
            return None

    def upload_file(self, file_data: bytes, file_name: str, mime_type: str):
        """上傳檔案到指定資料夾並回傳其網頁連結"""
        if not self.invoice_folder_id:
            print("錯誤: 無法取得發票資料夾 ID，無法上傳檔案。")
            return None

        try:
            file_metadata = {
                'name': file_name,
                'parents': [self.invoice_folder_id]
            }
            media = MediaIoBaseUpload(
                io.BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            print(f"成功上傳檔案: {file_name} (ID: {file['id']})")
            return file.get('webViewLink')
        except HttpError as error:
            print(f"上傳檔案時發生錯誤: {error}")
            return None