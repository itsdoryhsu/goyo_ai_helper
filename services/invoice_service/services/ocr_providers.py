from pydantic import BaseModel
import base64
import httpx
import json
import sys
import os
from typing import Tuple, Dict
from abc import ABC, abstractmethod

# 添加專案根目錄到路徑以便導入模型服務
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
import openai
import google.generativeai as genai

from typing import Optional

# 導入新的模型服務
try:
    from services.model_service import ocr_completion
    from services.model_service import create_user_message, create_system_message, extract_text_content
    MODEL_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Model service not available: {e}")
    MODEL_SERVICE_AVAILABLE = False

class InvoiceData(BaseModel):
    seller_id: str
    invoice_number: str
    invoice_date: str
    account: int
    invoice_type: str
    invoice_description: str
    category: Optional[str] = None  # AI 判斷的支出類別
    expense_category: Optional[str] = None # 新增的推斷欄位

class OCRProvider(ABC):
    @abstractmethod
    async def extract_data(self, processed_file_data: bytes, processed_media_type: str, system_prompt: str, temperature: float) -> Tuple[InvoiceData, Dict]:
        pass

class OpenAICRProvider(OCRProvider):
    def __init__(self, api_key: str, model_name: str):
        openai.api_key = api_key
        self.model_name = model_name

    async def extract_data(self, processed_file_data: bytes, processed_media_type: str, system_prompt: str, temperature: float) -> Tuple[InvoiceData, Dict]:
        base64_image = base64.b64encode(processed_file_data).decode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "請辨識這張發票的資訊，並以 JSON 格式回傳。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{processed_media_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            response_json = response.json()
            
            usage = response_json.get('usage', {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0})
            
            # 從回傳的 content 中解析 JSON 字串
            content_str = response_json['choices'][0]['message']['content']
            try:
                invoice_data_dict = json.loads(content_str)
                invoice_data = InvoiceData(**invoice_data_dict)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"OpenAI 回傳的不是有效的 JSON: {content_str}. 錯誤: {e}")

            return invoice_data, usage

class GoogleOCRProvider(OCRProvider):
    def __init__(self, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def extract_data(self, processed_file_data: bytes, processed_media_type: str, system_prompt: str, temperature: float) -> Tuple[InvoiceData, Dict]:
        image_part = {
            "mime_type": processed_media_type,
            "data": processed_file_data
        }
        
        prompt_parts = [
            system_prompt,
            "請辨識這張發票的資訊，並以 JSON 格式回傳。",
            image_part,
        ]
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": 2000,
            "response_mime_type": "application/json", # 確保回傳 JSON
        }
        
        response = await self.model.generate_content_async(
            prompt_parts,
            generation_config=generation_config
        )
        
        # 確保 response.text 是有效的 JSON 字符串
        try:
            invoice_data_dict = json.loads(response.text)
            invoice_data = InvoiceData(**invoice_data_dict)
        except json.JSONDecodeError as e:
            raise ValueError(f"Google Gemini 回傳的不是有效的 JSON: {response.text}. 錯誤: {e}")
        
        # Gemini API 的 usage 資訊獲取方式可能不同，這裡先給一個預設值
        usage = {
            'prompt_tokens': response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            'completion_tokens': response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            'total_tokens': (response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count) if response.usage_metadata else 0
        }
        
        return invoice_data, usage

class OpenRouterOCRProvider(OCRProvider):
    """使用 OpenRouter 統一模型服務的 OCR 提供者"""

    def __init__(self):
        if not MODEL_SERVICE_AVAILABLE:
            raise ValueError("Model service is not available. Cannot use OpenRouter OCR provider.")

    async def extract_data(self, processed_file_data: bytes, processed_media_type: str, system_prompt: str, temperature: float) -> Tuple[InvoiceData, Dict]:
        """使用統一模型服務進行 OCR 處理"""
        try:
            # 將圖片數據編碼為 base64
            base64_image = base64.b64encode(processed_file_data).decode('utf-8')

            # 準備消息
            messages = [
                create_system_message(system_prompt),
                create_user_message("請辨識這張發票的資訊，並以 JSON 格式回傳。")
            ]

            # 使用統一模型服務的 OCR 功能
            response = await ocr_completion(
                messages=messages,
                images=[base64_image],
                temperature=temperature,
                max_tokens=2000
            )

            # 提取文字內容
            content_str = extract_text_content(response)

            # 解析 JSON 響應
            try:
                invoice_data_dict = json.loads(content_str)
                invoice_data = InvoiceData(**invoice_data_dict)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"模型回傳的不是有效的 JSON: {content_str}. 錯誤: {e}")

            # 提取使用量資訊
            usage = response.get('usage', {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            })

            return invoice_data, usage

        except Exception as e:
            raise Exception(f"OpenRouter OCR 處理失敗: {e}")