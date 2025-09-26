import os
import sys
import logging
import asyncio
import time
from typing import Dict, Any, Optional
import pandas as pd

# 設置項目根目錄路徑
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# 載入環境變數
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'))

# 導入核心組件
from .core.data_loader import DataLoader
from .core.calculator import FinancialCalculator
from .core.ai_analyzer import AIAnalyzer
from .core.config import FinanceConfig, QuestionType
from .core.exceptions import FinanceServiceError

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleFinanceService:
    """簡化版財務分析服務 - 替代複雜的舊main.py"""

    def __init__(self):
        """初始化三個核心組件"""
        try:
            self.data_loader = DataLoader()
            self.calculator = FinancialCalculator()
            self.ai_analyzer = AIAnalyzer()
            self._cached_data: Optional[pd.DataFrame] = None
            logger.info("SimpleFinanceService 初始化成功")
        except Exception as e:
            logger.error(f"服務初始化失敗: {e}")
            raise

    async def ask(self, question: str) -> Dict[str, Any]:
        """核心方法 - 處理財務問題"""
        start_time = time.time()

        try:
            # 步驟1：加載數據（有緩存就不重複讀取）
            if self._cached_data is None:
                logger.info("首次加載財務數據...")
                self._cached_data = self.data_loader.load_from_env()
                logger.info(f"成功載入 {len(self._cached_data)} 筆數據")

            # 步驟2：分析問題類型
            question_type = self.calculator.analyze_question(question)
            logger.info(f"問題類型：{question_type.value}")

            # 步驟3：計算財務指標
            metrics = self.calculator.calculate_metrics(self._cached_data, question_type)

            # 步驟4：生成AI回答
            answer = await self.ai_analyzer.answer(question, metrics, question_type)

            duration = time.time() - start_time

            return {
                "answer": answer,
                "question_type": question_type.value,
                "metrics": metrics,
                "duration": round(duration, 2),
                "status": "success"
            }

        except FinanceServiceError as e:
            logger.error(f"財務服務錯誤: {e}")
            return {
                "answer": f"抱歉，處理您的問題時發生錯誤：{str(e)}",
                "status": "error",
                "duration": round(time.time() - start_time, 2)
            }

        except Exception as e:
            logger.error(f"未預期錯誤: {e}", exc_info=True)
            return {
                "answer": "抱歉，系統暫時無法處理您的問題，請稍後再試。",
                "status": "error",
                "duration": round(time.time() - start_time, 2)
            }

    def get_data_summary(self) -> Dict[str, Any]:
        """獲取數據概覽 - 用於健康檢查"""
        try:
            if self._cached_data is None:
                self._cached_data = self.data_loader.load_from_env()

            return {
                "total_records": len(self._cached_data),
                "date_range": f"{self._cached_data['invoice_date'].min()} 到 {self._cached_data['invoice_date'].max()}",
                "total_amount": float(self._cached_data['invoice_amount'].sum()),
                "categories": list(self._cached_data['category'].unique()),
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"獲取數據概覽失敗: {e}")
            return {"status": "error", "error": str(e)}

    def clear_cache(self) -> None:
        """清除數據緩存 - 強制重新載入數據"""
        self._cached_data = None
        logger.info("數據緩存已清除")

# 兼容性接口 - 保持與舊系統的API一致
class FinanceAnalysisProcessor:
    """兼容舊API的包裝器"""

    def __init__(self):
        self.service = SimpleFinanceService()

    async def process_finance_query(self, platform: str, user_id: str, query: str) -> Dict[str, Any]:
        """兼容舊版本的API接口"""
        result = await self.service.ask(query)

        # 轉換為舊格式
        return {
            "response": result["answer"],
            "status": result["status"],
            "duration": result["duration"],
            "total_tokens": 0,  # 新版本不統計token
            "prompt_tokens": 0,
            "completion_tokens": 0
        }

# 獨立運行模式
if __name__ == "__main__":
    async def interactive_session():
        """互動式會話"""
        try:
            service = SimpleFinanceService()
            logger.info("🚀 SimplifiedFinanceService 啟動成功！")
            logger.info("輸入 'exit' 結束對話，輸入 'summary' 查看數據概覽")

            while True:
                try:
                    question = input("\n💰 請輸入財務問題: ").strip()

                    if question.lower() == 'exit':
                        logger.info("👋 再見！")
                        break

                    if question.lower() == 'summary':
                        summary = service.get_data_summary()
                        print(f"\n📊 數據概覽:\n{summary}\n")
                        continue

                    if not question:
                        continue

                    print("\n🔄 分析中...")
                    result = await service.ask(question)

                    print(f"\n✅ 分析完成 ({result['duration']}秒)")
                    print(f"📋 問題類型: {result.get('question_type', 'N/A')}")
                    print(f"\n💡 **分析結果**:\n{result['answer']}\n")

                except KeyboardInterrupt:
                    logger.info("\n👋 檢測到中斷，再見！")
                    break
                except Exception as e:
                    logger.error(f"❌ 處理問題時發生錯誤: {e}")

        except Exception as e:
            logger.error(f"❌ 服務啟動失敗: {e}")

    asyncio.run(interactive_session())