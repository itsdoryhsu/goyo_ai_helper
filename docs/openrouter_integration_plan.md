# OpenRouter 模型集成計畫

## 概述
將現有的 AI 模型調用從直接使用 OpenAI/Google 改為使用 OpenRouter，實現統一的模型管理和自由切換功能。

## 目標
1. **統一模型接口**：創建通用的模型服務層
2. **自由切換模型**：支援多種 AI 模型動態切換
3. **降低耦合度**：各服務模組與具體模型提供商解耦
4. **易於維護**：集中化的模型配置和管理
5. **向後兼容**：保持現有功能不變

## 系統現狀分析

### 當前模型使用情況
1. **QA 服務** (`services/qa_service/qa_client.py`)
   - 模型：`gpt-3.5-turbo-16k`
   - 用途：財稅法問答，RAG 檢索增強生成
   - 特點：使用 LangChain ConversationalRetrievalChain

2. **財務分析服務** (`services/finance_analysis_service/main.py`)
   - 模型：`gpt-4.1`
   - 用途：財務數據分析，報告生成
   - 特點：使用 LangChain ChatOpenAI

3. **發票服務** (`services/invoice_service/services/ocr_providers.py`)
   - 模型：可選 `gpt-4o` (OpenAI) 或 `gemini-2.5-flash` (Google)
   - 用途：發票 OCR 識別和結構化數據提取
   - 特點：直接 API 調用，支援多提供商

## 架構設計

### 1. 核心模型服務層
創建統一的模型服務接口，位於 `services/model_service/`

```
services/model_service/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── models.py          # 模型配置定義
│   └── settings.py        # 環境變數配置
├── providers/
│   ├── __init__.py
│   ├── base.py           # 抽象基類
│   ├── openrouter.py     # OpenRouter 提供商
│   ├── openai.py         # OpenAI 直連提供商（向後兼容）
│   └── google.py         # Google 直連提供商（向後兼容）
├── factory.py            # 模型工廠
├── manager.py            # 模型管理器
└── utils.py              # 通用工具
```

### 2. 模型配置體系

#### 環境變數配置 (.env)
```bash
# OpenRouter 配置
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# 服務專用模型配置（可獨立設定）
QA_SERVICE_MODEL=anthropic/claude-3.5-sonnet
QA_SERVICE_TEMPERATURE=0.7
QA_SERVICE_MAX_TOKENS=4096

FINANCE_SERVICE_MODEL=openai/gpt-4-turbo
FINANCE_SERVICE_TEMPERATURE=0.3
FINANCE_SERVICE_MAX_TOKENS=8192

OCR_SERVICE_MODEL=openai/gpt-4o
OCR_SERVICE_TEMPERATURE=0.1
OCR_SERVICE_MAX_TOKENS=2048

# 全域預設配置（當服務專用配置未設定時使用）
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=4096

# 模型提供商選擇
MODEL_PROVIDER=openrouter  # 主要使用 openrouter

# 向後兼容的現有配置（fallback 使用）
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
```

#### 模型定義 (models.py)
```python
from enum import Enum
from typing import Dict, Any

class ModelProvider(Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    GOOGLE = "google"

class ModelConfig:
    def __init__(self, name: str, provider: ModelProvider,
                 max_tokens: int = 4096, temperature: float = 0.7,
                 supports_vision: bool = False, **kwargs):
        self.name = name
        self.provider = provider
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.supports_vision = supports_vision
        self.extra_params = kwargs

# 支援的模型清單
AVAILABLE_MODELS = {
    # OpenRouter 模型
    "claude-3.5-sonnet": ModelConfig(
        name="anthropic/claude-3.5-sonnet",
        provider=ModelProvider.OPENROUTER,
        max_tokens=8192,
        supports_vision=True
    ),
    "gpt-4o": ModelConfig(
        name="openai/gpt-4o",
        provider=ModelProvider.OPENROUTER,
        max_tokens=4096,
        supports_vision=True
    ),
    "gemini-pro": ModelConfig(
        name="google/gemini-pro",
        provider=ModelProvider.OPENROUTER,
        max_tokens=2048,
        supports_vision=True
    ),
    # 直連模型（向後兼容）
    "gpt-3.5-turbo": ModelConfig(
        name="gpt-3.5-turbo",
        provider=ModelProvider.OPENAI,
        max_tokens=4096
    ),
}
```

### 3. 實現階段

#### Phase 1: 基礎架構搭建
1. 創建模型服務基礎架構
2. 實現 OpenRouter 提供商
3. 建立模型工廠和管理器
4. 單元測試

#### Phase 2: 發票服務整合（優先）
1. 修改 `invoice_service` 使用新的模型服務
2. 保持向後兼容性
3. 添加模型切換功能
4. 測試 OCR 功能

#### Phase 3: QA 服務整合
1. 整合 LangChain 與新模型服務
2. 確保 RAG 功能正常
3. 性能優化

#### Phase 4: 財務分析服務整合
1. 修改財務分析服務
2. 測試數據分析功能
3. 性能調優

#### Phase 5: LINE Bot 模型切換功能
1. 添加模型選擇 UI
2. 用戶偏好設定儲存
3. 即時模型切換

## 技術實現細節

### 1. 統一接口設計
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator

class ModelProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """同步聊天完成"""
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        pass

    @abstractmethod
    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        images: List[str],  # base64 encoded
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """視覺理解完成"""
        pass
```

### 2. OpenRouter 實現
```python
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator

class OpenRouterProvider(ModelProvider):
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://your-app.com",
                "X-Title": "財務助手"
            }
        )

    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> Dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": model,
                "messages": messages,
                **kwargs
            }
        )
        return response.json()
```

### 3. 服務專用模型管理器
```python
from enum import Enum
from typing import Dict, Any, Optional
import os

class ServiceType(Enum):
    QA = "qa"
    FINANCE = "finance"
    OCR = "ocr"

class ServiceModelManager:
    """管理每個服務的專用模型配置"""

    def __init__(self):
        self.openrouter_provider = OpenRouterProvider(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        )

    def get_service_config(self, service_type: ServiceType) -> Dict[str, Any]:
        """獲取特定服務的模型配置"""
        service_prefix = f"{service_type.value.upper()}_SERVICE"

        return {
            "model": os.getenv(f"{service_prefix}_MODEL", os.getenv("DEFAULT_MODEL")),
            "temperature": float(os.getenv(f"{service_prefix}_TEMPERATURE", os.getenv("DEFAULT_TEMPERATURE", "0.7"))),
            "max_tokens": int(os.getenv(f"{service_prefix}_MAX_TOKENS", os.getenv("DEFAULT_MAX_TOKENS", "4096"))),
        }

    async def chat_completion(
        self,
        service_type: ServiceType,
        messages: List[Dict[str, str]],
        **override_params
    ) -> Dict[str, Any]:
        """為特定服務執行聊天完成"""
        config = self.get_service_config(service_type)
        config.update(override_params)  # 允許臨時覆蓋參數

        return await self.openrouter_provider.chat_completion(
            messages=messages,
            **config
        )

    async def vision_completion(
        self,
        service_type: ServiceType,
        messages: List[Dict[str, str]],
        images: List[str],
        **override_params
    ) -> Dict[str, Any]:
        """為特定服務執行視覺理解（OCR 專用）"""
        config = self.get_service_config(service_type)
        config.update(override_params)

        return await self.openrouter_provider.vision_completion(
            messages=messages,
            images=images,
            **config
        )

# 全域服務模型管理器實例
model_manager = ServiceModelManager()

# 便利函數
async def qa_completion(messages: List[Dict], **kwargs) -> Dict[str, Any]:
    """QA 服務專用的模型調用"""
    return await model_manager.chat_completion(ServiceType.QA, messages, **kwargs)

async def finance_completion(messages: List[Dict], **kwargs) -> Dict[str, Any]:
    """財務分析服務專用的模型調用"""
    return await model_manager.chat_completion(ServiceType.FINANCE, messages, **kwargs)

async def ocr_completion(messages: List[Dict], images: List[str] = None, **kwargs) -> Dict[str, Any]:
    """OCR 服務專用的模型調用"""
    if images:
        return await model_manager.vision_completion(ServiceType.OCR, messages, images, **kwargs)
    else:
        return await model_manager.chat_completion(ServiceType.OCR, messages, **kwargs)
```

## 使用範例

### 1. 發票服務中的使用
```python
# 原本的代碼
async def extract_data(self, processed_file_data: bytes, ...):
    # 舊的 OpenAI 直連代碼
    payload = {
        "model": self.model_name,  # 固定模型
        "messages": [...],
        "temperature": temperature
    }

# 新的代碼 - 使用服務專用模型
from services.model_service.manager import ocr_completion

async def extract_data(self, processed_file_data: bytes, ...):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": "請分析這張發票"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]}
    ]

    # 自動使用 OCR_SERVICE_MODEL 設定的模型
    response = await ocr_completion(
        messages=messages,
        temperature=0.1,  # 可以臨時覆蓋預設值
    )
    return response
```

### 2. QA 服務中的使用
```python
# 原本的 LangChain 整合
from services.model_service.manager import qa_completion

class CustomChatOpenAI:
    """包裝器，讓 LangChain 使用我們的服務專用模型"""

    async def agenerate(self, messages, **kwargs):
        # 轉換 LangChain 格式到標準格式
        standard_messages = self._convert_langchain_messages(messages)

        # 使用 QA 服務專用模型
        response = await qa_completion(
            messages=standard_messages,
            **kwargs
        )

        return self._convert_to_langchain_response(response)
```

### 3. 配置範例
```bash
# .env 文件 - 不同服務使用不同模型
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# QA 服務：使用 Claude，重視理解能力
QA_SERVICE_MODEL=anthropic/claude-3.5-sonnet
QA_SERVICE_TEMPERATURE=0.7
QA_SERVICE_MAX_TOKENS=4096

# 財務分析：使用 GPT-4，重視數據分析
FINANCE_SERVICE_MODEL=openai/gpt-4-turbo
FINANCE_SERVICE_TEMPERATURE=0.3
FINANCE_SERVICE_MAX_TOKENS=8192

# OCR 識別：使用視覺模型，重視準確性
OCR_SERVICE_MODEL=openai/gpt-4o
OCR_SERVICE_TEMPERATURE=0.1
OCR_SERVICE_MAX_TOKENS=2048
```

### 4. 動態模型切換
```python
# 支援運行時切換模型
from services.model_service.manager import model_manager, ServiceType

# 臨時使用不同模型處理特殊請求
special_response = await model_manager.chat_completion(
    service_type=ServiceType.QA,
    messages=messages,
    model="openai/gpt-4o",  # 臨時覆蓋預設模型
    temperature=0.2
)

# 或者為特定用戶使用premium模型
if user.is_premium:
    response = await qa_completion(
        messages=messages,
        model="anthropic/claude-3.5-sonnet",
        max_tokens=8192
    )
else:
    response = await qa_completion(messages=messages)  # 使用預設配置
```

## 遷移策略

### 1. 向後兼容
- 保留現有的直連模型提供商
- 通過環境變數控制使用哪種提供商
- 舊代碼無需立即修改

### 2. 漸進式遷移
- 每個服務獨立遷移
- 充分測試後再上線
- 提供降級方案

### 3. 配置管理
- 集中化的模型配置
- 環境變數覆蓋機制
- 運行時動態切換

## 優勢

1. **靈活性**：可以輕鬆切換不同的 AI 模型
2. **成本優化**：根據任務選擇性價比最高的模型
3. **風險分散**：不依賴單一提供商
4. **統一管理**：集中化的模型配置和監控
5. **易於擴展**：新增模型提供商只需實現接口

## 風險與對策

### 風險
1. **API 差異**：不同提供商的 API 格式可能不同
2. **性能變化**：模型切換可能影響響應質量
3. **成本控制**：需要監控不同模型的使用成本

### 對策
1. **統一適配**：通過適配器模式處理 API 差異
2. **充分測試**：每個模型在生產環境前都要充分測試
3. **監控機制**：建立使用統計和成本監控

## 時程規劃

- **Week 1**: 基礎架構設計和實現
- **Week 2**: 發票服務整合和測試
- **Week 3**: QA 服務整合
- **Week 4**: 財務分析服務整合
- **Week 5**: LINE Bot 功能整合和測試
- **Week 6**: 上線部署和監控

## 成功指標

1. **功能完整性**：所有現有功能正常運作
2. **性能穩定**：響應時間和準確度不下降
3. **易用性**：模型切換操作簡單直觀
4. **可維護性**：代碼結構清晰，易於擴展
5. **成本效益**：總體 AI 服務成本降低或持平