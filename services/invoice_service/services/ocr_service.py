from pydantic import BaseModel
import base64
from typing import Tuple, Dict

try:
    from ..config.settings import (
        OPENAI_API_KEY, MODEL_NAME, GOOGLE_API_KEY, GOOGLE_MODEL_NAME,
        OCR_PROVIDER, TEMPERATURE, OCR_SYSTEM_PROMPT, COMPANYNO
    )
except ImportError:
    # 當從其他服務導入時，使用絕對導入
    from services.invoice_service.config import (
        OPENAI_API_KEY, MODEL_NAME, GOOGLE_API_KEY, GOOGLE_MODEL_NAME,
        OCR_PROVIDER, TEMPERATURE, OCR_SYSTEM_PROMPT, COMPANYNO
    )
from ..utils.file_utils import convert_pdf_to_image
from .ocr_providers import InvoiceData, OpenAICRProvider, GoogleOCRProvider, OpenRouterOCRProvider, OCRProvider, MODEL_SERVICE_AVAILABLE


class OCRService:
    def __init__(self):
        self.ocr_provider: OCRProvider = self._initialize_ocr_provider()

    def _initialize_ocr_provider(self) -> OCRProvider:
        if OCR_PROVIDER == 'openrouter':
            if not MODEL_SERVICE_AVAILABLE:
                raise ValueError("Model service is not available. Cannot use 'openrouter' provider.")
            return OpenRouterOCRProvider()
        elif OCR_PROVIDER == 'openai':
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set in environment variables.")
            return OpenAICRProvider(api_key=OPENAI_API_KEY, model_name=MODEL_NAME)
        elif OCR_PROVIDER == 'google':
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is not set in environment variables.")
            return GoogleOCRProvider(api_key=GOOGLE_API_KEY, model_name=GOOGLE_MODEL_NAME)
        else:
            raise ValueError(f"Unsupported OCR_PROVIDER: {OCR_PROVIDER}. Must be 'openrouter', 'openai', or 'google'.")

    async def extract_invoice_data(self, file_data: bytes, media_type: str) -> Tuple[InvoiceData, Dict]:
        """
        從檔案的二進位資料中提取結構化的發票資訊，並回傳 usage 資訊。
        """
        try:
            processed_file_data = file_data
            processed_media_type = media_type

            if media_type == 'application/pdf':
                # convert_pdf_to_image 是同步函數，如果執行時間長，應考慮使用 run_in_executor
                processed_file_data = convert_pdf_to_image(file_data)
                processed_media_type = 'image/jpeg' # 轉換後固定為 JPEG
            
            invoice_data, usage_data = await self.ocr_provider.extract_data( # 使用 await
                processed_file_data=processed_file_data,
                processed_media_type=processed_media_type,
                system_prompt=OCR_SYSTEM_PROMPT,
                temperature=TEMPERATURE
            )
            return invoice_data, usage_data
            
        except Exception as e:
            raise Exception(f"OCR 處理失敗: {e}")

    def define_trancsaction_type(self, ocr_output: InvoiceData) -> str:
        """根據賣方統編判斷是收入還是支出"""
        if ocr_output.seller_id == COMPANYNO:
            return '收入'
        else:
            return '支出'