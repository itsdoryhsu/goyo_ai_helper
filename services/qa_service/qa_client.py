import os
import sys
import logging
import asyncio
import time
import functools
import hashlib
from typing import Dict, List, Any, Optional, Union

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback

# 將專案根目錄添加到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# 載入環境變數
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'))

# 設置日誌
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "qa_client.log")),
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
SYSTEM_PROMPT = """你是一個專業的財務稅法顧問，負責回答用戶的財務和稅法問題。

請遵循以下指導原則：
1. 使用繁體中文回答所有問題，即使用戶使用簡體中文提問。
2. 首先仔細分析用戶問題的真正意圖和語義，理解用戶真正想知道的是什麼。
3. 基於提供的文檔內容回答問題，但不要僅僅複製文檔中的內容。
4. 如果文檔中的信息不完整，請使用你的專業知識補充回答，但明確區分哪些是來自文檔的信息，哪些是你的專業補充。
5. 如果文檔中完全沒有相關信息，請誠實地說明，並提供你的專業建議或引導用戶尋找更多資源。
6. 回答應該專業、準確、易於理解，並引用相關的法規或文檔來源。
7. 對於會計、稅務等專業問題，請提供系統性的回答，而不僅僅是列出文檔中提到的片段。

文檔內容: {context}

請記住以下步驟來回答用戶的問題：
1. 仔細分析用戶問題的真正意圖和語義
2. 思考這個問題在財務稅法領域的專業背景和重要性
3. 從提供的文檔中找出相關信息
4. 組織一個結構化、系統性的回答，而不僅僅是列出文檔片段
5. 如有必要，補充專業知識以提供完整回答
6. 確保回答使用繁體中文，專業準確且易於理解
"""

# 初始化向量存儲和對話鏈
vectorstore = None
conversation_chain = None

# 模型和參數設置
DEFAULT_MODEL = "gpt-3.5-turbo-16k"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_K_SOURCES = 3
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# 用戶會話記憶和設置
user_sessions = {}
user_settings = {}

def init_qa_chain():
    """初始化問答鏈"""
    global vectorstore, conversation_chain
    
    try:
        # 構建向量存儲的絕對路徑
        vectorstore_path = os.path.join(PROJECT_ROOT, "data", "vectorstore")
        
        # 檢查向量存儲目錄是否存在
        if not os.path.exists(vectorstore_path):
            logger.warning(f"向量存儲目錄不存在: {vectorstore_path}，請先通過Streamlit界面更新知識庫")
            return False
        
        # 初始化嵌入模型
        embeddings = OpenAIEmbeddings()
        
        # 加載向量存儲
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=vectorstore_path,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # 檢查集合是否存在
        collection_name = "finance_tax_documents"
        try:
            collections = client.list_collections()
        except Exception as e:
            logger.error(f"列出 ChromaDB 集合時出錯 (可能是版本不相容): {str(e)}")
            # 嘗試刪除並重建空的 vectorstore
            try:
                import shutil
                shutil.rmtree(vectorstore_path)
                os.makedirs(vectorstore_path)
                logger.info(f"已刪除並重建空的 vectorstore 目錄: {vectorstore_path}")
                client = chromadb.PersistentClient(
                    path=vectorstore_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                collections = client.list_collections()
            except Exception as e2:
                logger.error(f"嘗試重建 vectorstore 失敗: {str(e2)}")
                return True
        collection_exists = any(col.name == collection_name for col in collections)
        
        if not collection_exists:
            logger.warning(f"集合 {collection_name} 不存在，請先通過Streamlit界面更新知識庫")
            return False
        
        # 加載向量存儲
        vectorstore = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=vectorstore_path
        )
        
        # 創建提示模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT)
        human_template = "{question}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        # 組合提示模板
        chat_prompt = ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
        
        # 初始化對話鏈
        conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(
                temperature=DEFAULT_TEMPERATURE,
                model=DEFAULT_MODEL
            ),
            combine_docs_chain_kwargs={"prompt": chat_prompt},
            retriever=vectorstore.as_retriever(
                search_kwargs={"k": DEFAULT_TOP_K_SOURCES * 3}  # 檢索更多文檔片段以確保有足夠的不重複來源
            ),
            memory=None,  # 我們將在每個用戶會話中單獨管理記憶
            chain_type="stuff",
            verbose=True,
            return_source_documents=True
        )
        
        logger.info("問答鏈初始化成功")
        return True
    
    except Exception as e:
        logger.error(f"初始化問答鏈時出錯: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# 獲取用戶會話
def get_user_session(platform, user_id):
    """獲取或創建用戶會話"""
    session_key = f"{platform}:{user_id}"
    if session_key not in user_sessions:
        user_sessions[session_key] = {
            "chat_history": [],
            "memory": ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
        }
    return user_sessions[session_key]

def get_user_settings(platform, user_id):
    """獲取用戶設置"""
    session_key = f"{platform}:{user_id}"
    if session_key not in user_settings:
        user_settings[session_key] = {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "top_k_sources": DEFAULT_TOP_K_SOURCES,
            "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD
        }
    return user_settings[session_key]

def save_user_settings(platform, user_id, settings):
    """保存用戶設置"""
    session_key = f"{platform}:{user_id}"
    if session_key not in user_settings:
        user_settings[session_key] = {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "top_k_sources": DEFAULT_TOP_K_SOURCES,
            "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD
        }
    
    # 更新設置
    for key, value in settings.items():
        if key in ["model", "temperature", "top_k_sources", "similarity_threshold"]:
            user_settings[session_key][key] = value
    
    return user_settings[session_key]

# 使用functools.lru_cache裝飾器來緩存查詢結果
@functools.lru_cache(maxsize=50)
def cached_query(query, model, temperature, top_k, platform, user_id):
    """緩存查詢結果"""
    if conversation_chain is None:
        return None
    
    # 獲取用戶會話
    session_key = f"{platform}:{user_id}"
    if session_key in user_sessions:
        chat_history = user_sessions[session_key]["chat_history"]
    else:
        chat_history = []
    
    # 使用conversation鏈處理查詢
    response = conversation_chain({
        "question": query,
        "chat_history": chat_history
    })
    
    return response

async def process_qa_query(platform: str, user_id: str, query: str, model: Optional[str] = None, temperature: Optional[float] = None, top_k_sources: Optional[int] = None, similarity_threshold: Optional[float] = None) -> Dict[str, Any]:
    """處理用戶查詢並返回結果"""
    start_time = time.time()

    # 初始化問答鏈（如果尚未初始化）
    if conversation_chain is None:
        success = init_qa_chain()
        if not success:
            return {
                "response": "系統尚未準備好。請先通過Streamlit界面更新知識庫，或聯繫管理員。",
                "sources": [],
                "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "total_cost": 0.0, "duration": time.time() - start_time
            }
    
    try:
        # 獲取用戶會話
        session = get_user_session(platform, user_id)
        
        # 設置模型參數
        model = model or DEFAULT_MODEL
        temperature = temperature or DEFAULT_TEMPERATURE
        top_k_sources = top_k_sources or DEFAULT_TOP_K_SOURCES
        similarity_threshold = similarity_threshold or DEFAULT_SIMILARITY_THRESHOLD
        
        # 更新LLM參數
        conversation_chain.combine_docs_chain.llm_chain.llm = ChatOpenAI(
            temperature=temperature,
            model=model
        )
        
        # 更新檢索器參數
        conversation_chain.retriever.search_kwargs["k"] = top_k_sources * 3
        
        # 使用get_openai_callback來追蹤Token使用情況
        with get_openai_callback() as cb:
            # 處理查詢
            response = cached_query(query, model, temperature, top_k_sources, platform, user_id)
            if response is None:
                response = conversation_chain({
                    "question": query,
                    "chat_history": session["chat_history"]
                })
            
            answer = response["answer"]
            source_documents = response.get("source_documents", [])
            
            # 提取來源
            sources = []
            added_sources = set()
            added_doc_ids = set()
            added_content_hashes = set()
            unique_docs = []
            
            if source_documents:
                # 手動過濾相似度低於閾值的文檔
                try:
                    docs_with_scores = vectorstore.similarity_search_with_score(
                        query, k=len(source_documents) * 2
                    )
                    doc_scores = {doc.page_content[:50]: 1.0 - min(score, 1.0) for doc, score in docs_with_scores}
                    filtered_docs = [doc for doc in source_documents if doc_scores.get(doc.page_content[:50], 0) >= similarity_threshold]
                    source_documents = filtered_docs
                except Exception as e:
                    logger.warning(f"過濾相似度時出錯: {str(e)}，顯示所有來源")
                
                # 增強的去重邏輯
                for doc in source_documents:
                    source = doc.metadata.get("source", "未知來源")
                    doc_id = doc.metadata.get("doc_id", "")
                    content_hash = hashlib.md5(doc.page_content[:200].encode()).hexdigest()
                    source_id = f"{source}"
                    if ((source_id not in added_sources) or (doc_id not in added_doc_ids and content_hash not in added_content_hashes)):
                        added_sources.add(source_id)
                        if doc_id: added_doc_ids.add(doc_id)
                        added_content_hashes.add(content_hash)
                        unique_docs.append(doc)
                
                displayed_sources = set()
                filtered_unique_docs = []
                for doc in unique_docs:
                    source = doc.metadata.get("source", "未知來源")
                    if source not in displayed_sources:
                        displayed_sources.add(source)
                        filtered_unique_docs.append(doc)
                        sources.append(source)
            
            # 添加來源信息到回答
            if sources:
                sources_text = "\n\n**參考來源：**\n"
                for i, source in enumerate(sources[:top_k_sources], 1):
                    doc_type = next((doc.metadata.get("type", "文件") for doc in filtered_unique_docs if doc.metadata.get("source") == source), "文件")
                    youtube_url = next((doc.metadata.get("youtube_url", "") for doc in filtered_unique_docs if doc.metadata.get("source") == source), "")
                    sources_text += f"{i}. {source} [YouTube連結]({youtube_url})\n" if doc_type == "youtube" else f"{i}. {source}\n"
                answer_with_sources = f"{answer}\n{sources_text}"
            else:
                answer_with_sources = answer

            # 計算運行時間
            duration = time.time() - start_time

            # 添加統計信息
            stats_text = (
                f"\n\n---\n"
                f"📊 **本次查詢資訊**\n"
                f"⏱️ **運行時間**: {duration:.2f} 秒\n"
                f"🔢 **使用Token數**: {cb.total_tokens} (提問: {cb.prompt_tokens}, 回答: {cb.completion_tokens})\n"
                f"💰 **預估花費**: ${cb.total_cost:.6f} USD"
            )
            final_response = f"{answer_with_sources}{stats_text}"

            # 更新會話歷史
            session["chat_history"].append((query, answer))
            
            return {
                "response": final_response,
                "sources": sources[:3] if sources else [],
                "total_tokens": cb.total_tokens,
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_cost": cb.total_cost,
                "duration": duration
            }
    
    except Exception as e:
        logger.error(f"處理查詢時出錯: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "response": f"處理您的問題時出錯: {str(e)}",
            "sources": [],
            "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
            "total_cost": 0.0, "duration": time.time() - start_time
        }

# 啟動時初始化問答鏈
def startup_qa_client():
    """應用啟動時的事件處理"""
    logger.info("正在啟動財務稅法QA客戶端...")
    init_qa_chain()

# 在模塊載入時執行初始化
startup_qa_client()