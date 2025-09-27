import os
import logging
import hashlib
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from .base import VectorStoreProvider
from ..core.models import QADocument
from ..core.config import QAConfig
from ..core.exceptions import VectorStoreError

logger = logging.getLogger(__name__)

class ChromaVectorStoreProvider(VectorStoreProvider):
    """ChromaDB向量存儲提供商"""

    def __init__(self, vectorstore_path: str = None, collection_name: str = None):
        self.vectorstore_path = vectorstore_path or QAConfig.VECTORSTORE_PATH
        self.collection_name = collection_name or QAConfig.COLLECTION_NAME
        self.vectorstore = None
        self.embeddings = None
        self._initialize_vectorstore()

    def _initialize_vectorstore(self):
        """初始化向量存儲"""
        try:
            # 檢查向量存儲目錄
            if not os.path.exists(self.vectorstore_path):
                logger.warning(f"向量存儲目錄不存在: {self.vectorstore_path}")
                return

            # 初始化嵌入模型
            self.embeddings = OpenAIEmbeddings()

            # 創建ChromaDB客戶端
            client = chromadb.PersistentClient(
                path=self.vectorstore_path,
                settings=Settings(anonymized_telemetry=False)
            )

            # 檢查集合是否存在
            collections = client.list_collections()
            collection_exists = any(col.name == self.collection_name for col in collections)

            if not collection_exists:
                logger.warning(f"集合 {self.collection_name} 不存在")
                return

            # 初始化向量存儲
            self.vectorstore = Chroma(
                client=client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.vectorstore_path
            )

            logger.info(f"ChromaDB向量存儲初始化成功: {self.vectorstore_path}")

        except Exception as e:
            logger.error(f"初始化ChromaDB向量存儲失敗: {e}")
            # 不要拋出異常，讓服務繼續運行

    async def search_documents(self, query: str, k: int = 5) -> List[QADocument]:
        """搜索相關文檔"""
        if not self.vectorstore:
            raise VectorStoreError("向量存儲未初始化")

        try:
            # 使用相似度搜索
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=k * 2)

            # 過濾低相似度文檔
            filtered_docs = [
                doc for doc, score in docs_with_scores
                if (1.0 - min(score, 1.0)) >= QAConfig.SIMILARITY_THRESHOLD
            ]

            # 去重處理
            unique_docs = self._deduplicate_documents(filtered_docs)

            # 轉換為QADocument
            qa_documents = []
            for doc in unique_docs[:k]:
                qa_doc = QADocument(
                    content=doc.page_content,
                    metadata=doc.metadata
                )
                qa_documents.append(qa_doc)

            return qa_documents

        except Exception as e:
            logger.error(f"文檔搜索失敗: {e}")
            raise VectorStoreError(f"文檔搜索失敗: {e}")

    def _deduplicate_documents(self, documents: List[Any]) -> List[Any]:
        """去重文檔 - 簡化邏輯"""
        seen_sources = set()
        seen_content_hashes = set()
        unique_docs = []

        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            content_hash = hashlib.md5(doc.page_content[:200].encode()).hexdigest()

            # 基於來源和內容哈希去重
            if source not in seen_sources and content_hash not in seen_content_hashes:
                seen_sources.add(source)
                seen_content_hashes.add(content_hash)
                unique_docs.append(doc)

        return unique_docs

    def is_available(self) -> bool:
        """檢查向量存儲是否可用"""
        return self.vectorstore is not None

    def get_stats(self) -> Dict[str, Any]:
        """獲取向量存儲統計信息"""
        if not self.vectorstore:
            return {"available": False}

        try:
            # 獲取集合統計信息
            collection = self.vectorstore._collection
            count = collection.count()

            return {
                "available": True,
                "document_count": count,
                "collection_name": self.collection_name,
                "vectorstore_path": self.vectorstore_path
            }
        except Exception as e:
            logger.error(f"獲取向量存儲統計失敗: {e}")
            return {"available": True, "error": str(e)}