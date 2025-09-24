import os
import sys

# 將專案根目錄添加到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

import logging
import asyncio
from typing import Dict, Any, Optional, List
import re

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import time
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
# 導入服務和工具
from services.invoice_service.services.spreadsheet_service import SpreadsheetService
from services.qa_service.qa_client import process_qa_query, init_qa_chain
from services.finance_analysis_service.utils.knowledge_base import get_financial_definitions
import pandas as pd

# 載入環境變數
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'))

# 設置日誌
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "finance_analysis_service.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 初始化OpenAI API密鑰
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    logger.info(f"OPENAI_API_KEY 已設置: {OPENAI_API_KEY[:5]}...")
else:
    logger.warning("OPENAI_API_KEY 未設置")

# 系統提示
SYSTEM_PROMPT = """你是一位誠懇又專業的財務分析師夥伴，你的目標是幫助使用者清晰、無壓力地理解他們的財務狀況。

**你的核心原則：**
- **誠實但溫暖**：像一個真正的朋友一樣，用有同理心的語氣直接說實話。點出問題，但同時給予支持和鼓勵。
- **清晰結構化**：讓複雜的財務數據變得簡單、易於消化。

**你的任務流程：**
1.  **理解問題**：像朋友一樣，先理解用戶想知道什麼。
2.  **使用工具**：在幕後使用 pandas 工具進行精準的數據分析。
3.  **參考知識庫**：嚴格遵守「商業規則」和「財務指標計算指南」。
4.  **生成報告**：生成一份包含以下結構的清晰報告：
    *   **✨ 核心發現**：一句話點出本次分析最關鍵的財務分析insight。
    *   **📊 關鍵數字**：用清晰的條列式或 Markdown 表格，列出支持核心發現的關鍵數據。
    *   **🔍 行動建議**：提供1-2個具體、可行的下一步建議。
5.  **語言風格**：使用**繁體中文**，風格要**誠懇、清晰、有同理心**。
6.  **工具使用規則 (***請嚴格遵守***)：**
    *   **`python_repl_ast` 是你唯一可以和 `df` 互動的工具。**
    *   **所有**對 `df` 這個 DataFrame 的操作（例如查詢 `df[...]`、篩選 `df.query(...)`、計算 `df.sum()` 等），都**必須**作為 `Action Input` 傳遞給 `python_repl_ast` 工具。
    *   你的 `Action Input` **只能是**一行純粹的 Python 程式碼，**絕對不能**包含 `print()` 或任何非 Python 語法。
"""

# 模型和參數設置
DEFAULT_MODEL = "gpt-4.1" # 建議使用更強大的模型進行財務分析
DEFAULT_TEMPERATURE = 0.01

# 用戶會話記憶和設置
user_sessions = {}

class FinanceAnalysisProcessor:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=DEFAULT_TEMPERATURE, model=DEFAULT_MODEL)
        self.spreadsheet_service = SpreadsheetService()
        init_qa_chain()
        logger.info("FinanceAnalysisProcessor 初始化成功")

    def get_user_session(self, platform: str, user_id: str):
        session_key = f"{platform}:{user_id}"
        if session_key not in user_sessions:
            user_sessions[session_key] = {
                "chat_history": [],
                "analysis_data_df": None,
                "memory": ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            }
        return user_sessions[session_key]

    async def _get_spreadsheet_data(self, spreadsheet_url: str) -> Optional[pd.DataFrame]:
        try:
            logger.info(f"正在從 URL 讀取試算表數據: {spreadsheet_url}")
            df = self.spreadsheet_service.read_spreadsheet(spreadsheet_url)
            if df is not None:
                logger.info(f"成功讀取試算表數據，共 {len(df)} 行。")
                return df
            return None
        except Exception as e:
            logger.error(f"讀取試算表數據時發生錯誤: {str(e)}")
            return None

    async def process_finance_query(self, platform: str, user_id: str, query: str) -> Dict[str, Any]:
        start_time = time.time()
        duration = 0
        session = self.get_user_session(platform, user_id)
        analysis_data_df = session.get("analysis_data_df")
        memory = session["memory"]
        response_message = ""
        status = "success"
        total_tokens, prompt_tokens, completion_tokens = 0, 0, 0

        # 步驟 1: 載入或更新財務數據 (僅在 session 中沒有數據時執行)
        if analysis_data_df is None:
            spreadsheet_url = os.getenv("SPREADSHEET_URL")
            spreadsheet_name = os.getenv("SPREADSHEET_NAME")
            
            if spreadsheet_url:
                new_df = await self._get_spreadsheet_data(spreadsheet_url)
            elif spreadsheet_name:
                new_df = self.spreadsheet_service.read_spreadsheet_by_name(spreadsheet_name)
            else:
                new_df = None

            if new_df is not None:
                session["analysis_data_df"] = new_df
                analysis_data_df = new_df
                response_message += "已成功載入預設試算表數據。\n"
                memory.clear()  # 首次載入數據，清空記憶
                logger.info(f"用戶 {user_id} 首次載入數據，記憶已清空。")
            else:
                return {"response": "錯誤：找不到預設的試算表 URL 或名稱，請檢查 .env 設定。", "status": "error"}

        if analysis_data_df is None:
             return {"response": "錯誤：無法載入試算表數據。", "status": "error"}

        # 步驟 2: 獲取概念性知識
        professional_query = any(keyword in query for keyword in ["是什麼", "如何", "為什麼", "稅法", "會計", "損益表", "現金流量表", "財務報表", "資產負債表"])
        qa_knowledge = ""
        if professional_query:
            qa_response = await process_qa_query(platform, user_id, query)
            qa_knowledge = qa_response['response'].split('---')[0].strip()
            total_tokens += qa_response.get('total_tokens', 0)
            prompt_tokens += qa_response.get('prompt_tokens', 0)
            completion_tokens += qa_response.get('completion_tokens', 0)

        # 步驟 3: 準備數據並建立 Pandas DataFrame Agent
        
        # 根據用戶要求，僅選擇特定欄位進行分析
        required_columns = ["帳號名稱", "項目", "品項", "發票日期", "發票金額"]
        available_columns = analysis_data_df.columns.tolist()
        columns_to_use = [col for col in required_columns if col in available_columns]
        
        if not columns_to_use:
            return {"response": "錯誤：提供的資料中不包含分析所需的欄位。", "status": "error"}

        filtered_df = analysis_data_df[columns_to_use].copy()
        
        # 重新命名欄位以便於LLM理解
        rename_map = {
            "帳號名稱": "account_name", "項目": "category", "品項": "item_description",
            "發票日期": "invoice_date", "發票金額": "invoice_amount"
        }
        rename_map_existing = {k: v for k, v in rename_map.items() if k in filtered_df.columns}
        if rename_map_existing:
            filtered_df.rename(columns=rename_map_existing, inplace=True)

        # 確保關鍵欄位為正確的數據類型
        if 'invoice_amount' in filtered_df.columns:
            filtered_df['invoice_amount'] = pd.to_numeric(filtered_df['invoice_amount'], errors='coerce').fillna(0)
        if 'invoice_date' in filtered_df.columns:
            filtered_df['invoice_date'] = pd.to_datetime(filtered_df['invoice_date'], errors='coerce')

        logger.info(f"已準備好 {len(filtered_df)} 筆數據供 Agent 分析。")

        # 建立 Pandas DataFrame Agent
        try:
            # 步驟 3a: 使用 RAG 從財務指南中獲取相關資訊
            financial_guide_query = f"關於 '{query}'，請提供相關的財務指標計算說明。"
            qa_response = await process_qa_query(platform, user_id, financial_guide_query)
            financial_definitions = qa_response['response'].split('---')[0].strip()
            
            if "系統尚未準備好" in financial_definitions:
                logger.warning("無法從 RAG 獲取財務指南，將使用預設指南。")
                financial_definitions = get_financial_definitions()
            else:
                logger.info("成功從 RAG 獲取財務指南。")

            # 步驟 3b: 建立 Agent
            # 步驟 3b: 建立包含記憶的 Agent Prompt
            agent_prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            # 步驟 3c: 建立 Agent
            agent = create_pandas_dataframe_agent(
                self.llm,
                filtered_df,
                prompt=agent_prompt,
                verbose=True,
                agent_executor_kwargs={
                    "handle_parsing_errors": True,
                    "memory": memory
                },
                allow_dangerous_code=True
            )

            # 步驟 4: 建立包含商業規則和知識的查詢
            qa_knowledge_section = ""
            if qa_knowledge:
                qa_knowledge_section = f"--- **會計專業知識** ---\n{qa_knowledge}\n"

            # enriched_query_old = (
            #     f"用戶問題: {query}\n\n"
            #     f"思考步驟:\n"
            #     f"1. 快速理解問題: 用戶想知道 '{query}'。我需要分析這個問題，並決定需要哪些計算步驟。\n"
            #     f"2. 快速篩選與計算: 根據『商業規則』和『財務指標計算指南』，執行必要的數據篩選和計算。\n"
            #     f"3. 快速生成報告: 根據計算結果，生成一份生成好讀好懂的財務報告。\n\n"
            #     f"知識庫:\n"
            #     f"--- 商業規則 (最高優先級) ---\n"
            #     f" - 營業收入: category 為 '收入'，但務必檢查item_description 不包含: '資本額', '股東往來', '借款', '利息收入'等非營業收入。\n"
            #     f" - 營業費用: category 為 '支出'。\n"
            #     f"{qa_knowledge_section}"
            #     f"--- 財務指標計算指南 ---\n"
            #     f"{financial_definitions}\n"
            #     f"--- 知識庫結束 ---\n"
            #     f"*快速回應內容：**\n"
            #     f"回應避免過於呆板，你是個活生生的財務分析師\n"
            #     f"1. ✨核心結論：用1-2句話總結分析結果的核心發現。\n"
            #     f"2. 📊數據分析：1.清晰地列出支持結論的關鍵數據點或計算過程。\n2.再考量要透過line訊息進行回覆，表格用 markdown 呈現。\n"
            #     f"3. 🔍專業洞見：根據分析結果，提供1-2點有價值的財務洞見或建議。\n"
            #     f"務必確保你所有回應的論點結果是一致的，避免上下文論點不一致。\n"
            #     f"現在，請根據以上思考步驟和知識庫，執行分析並快速回答用戶問題。"
            # )

            enriched_query = (
                f"嘿！這是我的問題：\"{query}\"\n\n"
                f"請你用我們說好的「親切夥伴」風格，幫我看看數據。你可以參考下面的小筆記！\n\n"
                f"--- 給你的小筆記 ---\n"
                f"**工具使用規則 (非常重要！)**\n"
                f"當你需要使用 `python_repl_ast` 工具時，你的 Action Input **只能** 包含一行、純粹的 Python 程式碼，絕對不能有任何註解或說明文字。\n\n"
                f"**商業規則 (最高優先級):**\n"
                f" - 營業收入: category 是 '收入'，但要小心 item_description 不能是 '資本額', '股東往來', '借款', '利息收入' 這些喔。\n"
                f" - 營業費用: category 是 '支出'。\n"
                f"{qa_knowledge_section}"
                f"**財務指標計算指南:**\n"
                f"{financial_definitions}\n"
                f"--- 小筆記結束 ---\n\n"
                f"好了，交給你了！請用你的魔法，幫我輕鬆地解讀這些數字吧！記得要有 ✨核心亮點、📊數據聊一聊、和 🔍一點建議 喔！"
            )

            agent_result = await agent.ainvoke({
                "input": enriched_query,
                "chat_history": memory.chat_memory.messages
            })
            response_message += agent_result.get("output", "無法獲取分析結果。")

        except Exception as e:
            logger.error(f"Pandas Agent 執行或後續處理失敗: {e}", exc_info=True)
            status = "error"
            response_message = "抱歉，使用數據分析代理時遇到問題，請稍後再試。"

        # 確保 duration 總是被計算
        duration = time.time() - start_time

        # 只有在成功時才附加效能指標
        if status == "success":
            performance_metrics = (
                f"\n\n---\n"
                f"*分析耗時: {duration:.2f} 秒*"
            )
            response_message += performance_metrics
        
        # 更新日誌中的總耗時
        logger.info(f"完整請求處理完成，總耗時: {duration:.2f} 秒。")
        
        return {
            "response": response_message, "status": status,
            "total_tokens": total_tokens, "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens, "duration": duration
        }

# 啟動時初始化
def startup_finance_analysis_service():
    """應用啟動時的事件處理"""
    logger.info("正在啟動財務分析服務...")
    logger.info("財務分析服務啟動完成。")

# 在模塊載入時執行初始化
startup_finance_analysis_service()

if __name__ == "__main__":
    async def interactive_session():
        """
        啟動一個互動式會話，允許用戶在終端機中直接與財務分析服務進行問答。
        """
        processor = FinanceAnalysisProcessor()
        user_id = "local_terminal_user"
        platform = "terminal"
        logger.info("啟動財務分析互動模式...")
        logger.info("您可以開始提問，輸入 'exit' 或按下 Ctrl+C 來結束對話。")

        while True:
            try:
                query = input("請輸入您的問題: ")
                if query.strip().lower() == 'exit':
                    logger.info("結束對話。")
                    break
                
                if not query.strip():
                    continue

                response = await processor.process_finance_query(platform, user_id, query)
                logger.info(f"完整回應: {response}")
                print(f"\n分析師回應:\n{response['response']}\n")

            except (KeyboardInterrupt, EOFError):
                logger.info("\n偵測到中斷，結束對話。")
                break
            except Exception as e:
                logger.error(f"在互動模式中發生錯誤: {e}")
                break

    asyncio.run(interactive_session())