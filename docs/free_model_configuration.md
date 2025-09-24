# 免費模型配置方案

## 推薦配置

### 服務專用免費模型分配

```bash
# OpenRouter 配置
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# === 免費模型配置 ===

# QA 服務：Grok-4 Fast（快速響應對話）
QA_SERVICE_MODEL=x-ai/grok-4-fast:free
QA_SERVICE_TEMPERATURE=0.7
QA_SERVICE_MAX_TOKENS=4096

# 財務分析服務：DeepSeek R1（推理專精）
FINANCE_SERVICE_MODEL=deepseek/deepseek-r1-0528:free
FINANCE_SERVICE_TEMPERATURE=0.3
FINANCE_SERVICE_MAX_TOKENS=8192

# OCR 服務：Gemini 2.0 Flash（視覺能力）
OCR_SERVICE_MODEL=google/gemini-2.0-flash-exp:free
OCR_SERVICE_TEMPERATURE=0.1
OCR_SERVICE_MAX_TOKENS=2048

# === 備選模型配置 ===
# 如果主要模型達到免費限額，可切換使用

# 備選對話模型
BACKUP_CHAT_MODEL=deepseek/deepseek-chat-v3.1:free
# 備選分析模型
BACKUP_ANALYSIS_MODEL=google/gemini-2.0-flash-exp:free
# 備選視覺模型（付費，但OCR必需）
BACKUP_VISION_MODEL=openai/gpt-4o

# === 全域預設配置 ===
DEFAULT_MODEL=x-ai/grok-4-fast:free
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=4096
```

## 詳細分析

### 1. QA 服務 - Grok-4 Fast

**為什麼選擇：**
- ⚡ **Fast 響應**：專為快速回答設計，適合即時問答
- 💬 **對話優化**：xAI 專注於對話體驗
- 🌐 **知識更新**：相對新的模型，知識較為時新
- 🔄 **上下文處理**：適合多輪對話和 RAG 場景
- 🆓 **免費額度**：通常有較寬鬆的免費使用限制

**配置說明：**
- `temperature=0.7`：保持適度創意，避免過於死板
- `max_tokens=4096`：足夠長的回答空間

### 2. 財務分析服務 - DeepSeek R1

**為什麼選擇：**
- 🧠 **推理導向**：R1 版本強調邏輯推理
- 📊 **數據分析**：對結構化數據處理能力強
- 🔢 **數學計算**：相對準確的數值計算
- 📋 **格式化輸出**：能產生結構化的分析報告

**配置說明：**
- `temperature=0.3`：低溫度確保分析準確性
- `max_tokens=8192`：支援詳細的分析報告

### 3. OCR 服務 - Gemini 2.0 Flash

**為什麼選擇：**
- 👁️ **視覺能力**：支援圖像理解（免費選項中唯一）
- ⚡ **Flash 速度**：快速響應，適合 OCR 場景
- 🆕 **實驗性功能**：可能包含最新的視覺理解技術
- 🏢 **Google 品質**：OCR 技術相對成熟

**配置說明：**
- `temperature=0.1`：極低溫度確保識別準確性
- `max_tokens=2048`：OCR 輸出通常不需要很長

## 成本效益分析

### 免費額度預估（基於一般免費模型限制）

| 服務 | 模型 | 預估免費額度/日 | 實際使用量預估 |
|------|------|----------------|----------------|
| QA | DeepSeek Chat | ~1000 requests | 50-100 requests |
| 財務 | DeepSeek R1 | ~500 requests | 10-20 requests |
| OCR | Gemini Flash | ~100 requests | 20-50 requests |

### 備選策略

當主要免費模型達到限額時：

1. **QA 服務備選**：
   ```bash
   # 切換到 DeepSeek
   QA_SERVICE_MODEL=deepseek/deepseek-chat-v3.1:free
   ```

2. **財務分析備選**：
   ```bash
   # 切換到 Gemini
   FINANCE_SERVICE_MODEL=google/gemini-2.0-flash-exp:free
   ```

3. **OCR 服務備選**：
   ```bash
   # 切換到付費但必要的視覺模型
   OCR_SERVICE_MODEL=openai/gpt-4o
   ```

## 風險與對策

### 潛在風險

1. **免費限額**：可能很快達到每日限制
2. **功能限制**：免費版可能有功能限制
3. **穩定性**：免費服務可能不如付費穩定

### 對策

1. **多模型輪替**：
   ```python
   # 實現自動fallback機制
   async def qa_completion_with_fallback(messages, **kwargs):
       models = [
           "x-ai/grok-4-fast:free",
           "deepseek/deepseek-chat-v3.1:free",
           "google/gemini-2.0-flash-exp:free"
       ]

       for model in models:
           try:
               return await qa_completion(messages, model=model, **kwargs)
           except QuotaExceededError:
               continue

       raise Exception("All free models exhausted")
   ```

2. **使用量監控**：
   ```python
   # 追蹤每日使用量
   daily_usage = {
       "qa": 0,
       "finance": 0,
       "ocr": 0
   }
   ```

3. **智能降級**：
   - 非關鍵請求使用免費模型
   - 重要請求保留付費模型
   - 用戶等級區分（VIP 用戶優先付費模型）

## 實施順序

1. **Phase 1**：建立基礎架構，支援免費模型
2. **Phase 2**：實施 OCR 服務（優先，因為視覺功能選擇有限）
3. **Phase 3**：實施 QA 服務（使用量大，節省成本效果明顯）
4. **Phase 4**：實施財務分析（最後，因為使用頻率較低）
5. **Phase 5**：加入智能切換和監控機制

## 預期效果

- **成本節省**：預估節省 80-90% AI 調用成本
- **功能保持**：核心功能基本不受影響
- **靈活性增加**：可根據實際使用情況動態調整
- **風險分散**：不依賴單一模型供應商