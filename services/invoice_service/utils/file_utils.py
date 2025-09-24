def get_media_type(file_info):
    """根據檔案資訊決定 media type"""
    mime_type = file_info.get('mimeType', '')
    name = file_info.get('name', '').lower()
    
    # PDF 檔案
    if mime_type == 'application/pdf' or '.pdf' in name:
        return 'application/pdf'
    
    # 圖片檔案
    if 'image/' in mime_type:
        return mime_type
    
    # 根據副檔名判斷
    if '.png' in name:
        return 'image/png'
    elif '.jpg' in name or '.jpeg' in name:
        return 'image/jpeg'
    elif '.gif' in name:
        return 'image/gif'
    elif '.bmp' in name:
        return 'image/bmp'
    
    # 預設為 PNG
    return 'image/png'

def generate_drive_link(file_id):
    """產生 Google Drive 檔案連結"""
    return f"https://drive.google.com/file/d/{file_id}/view"

import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image
from ..config.settings import PDF_DPI # 導入 PDF_DPI

def convert_pdf_to_image(pdf_data: bytes) -> bytes:
    """
    將 PDF 檔案的二進位資料轉換為 JPEG 格式的圖片二進位資料。
    只處理 PDF 的第一頁。
    """
    try:
        # 開啟 PDF 文件
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        if not pdf_document:
            raise ValueError("無法開啟 PDF 文件。")

        # 取得第一頁
        page = pdf_document.load_page(0)  # 頁碼從 0 開始

        # 設定渲染參數，使用配置的 DPI
        pix = page.get_pixmap(matrix=fitz.Matrix(PDF_DPI/72, PDF_DPI/72))

        # 將 pixmap 轉換為 PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 將 PIL Image 儲存為 JPEG 格式的 BytesIO 物件
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG')
        
        pdf_document.close()
        return img_byte_arr.getvalue()
    except Exception as e:
        raise Exception(f"PDF 轉換圖片失敗: {e}")
