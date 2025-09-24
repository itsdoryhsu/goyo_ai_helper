import os
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

def get_financial_definitions() -> str:
    """
    讀取並返回 '給予LLM的財務指標計算指南.pdf' 的完整文字內容。

    這個函數會使用 PyMuPDF (fitz) 函式庫來打開指定的 PDF 檔案，
    逐頁提取文字，並將它們合併成一個單一的字串。

    Returns:
        str: PDF 文件的完整文字內容。如果文件不存在或讀取失敗，
             則返回一個錯誤訊息字串。
    """
    # 構建文件的絕對路徑
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    definitions_path = os.path.join(project_root, 'services', 'finance_analysis_service', 'documents', '財務分析AI的標準作業程序.pdf')
    
    try:
        doc = fitz.open(definitions_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        
        if not full_text.strip():
            logger.warning(f"PDF 文件 '{definitions_path}' 可能是空的或無法提取文字。")
            return "警告：財務指標定義文件是空的或無法讀取內容。"
            
        logger.info(f"成功從 '{definitions_path}' 讀取並提取了 {len(full_text)} 字元的內容。")
        return full_text
        
    except FileNotFoundError:
        logger.error(f"財務指標定義文件未找到於: {definitions_path}")
        return f"錯誤：找不到財務指標定義文件於 '{definitions_path}'。"
    except Exception as e:
        # 捕捉其他所有來自 fitz 或 I/O 的可能錯誤
        logger.error(f"讀取 PDF 文件 '{definitions_path}' 時發生未知錯誤: {e}", exc_info=True)
        return f"錯誤：讀取 PDF 文件時發生嚴重錯誤: {e}"

if __name__ == '__main__':
    # 用於直接測試此模組的功能
    print("--- 正在測試讀取財務指標定義 PDF ---")
    definitions = get_financial_definitions()
    print(f"--- 讀取完畢，共 {len(definitions)} 字元 ---")
    print(definitions[:500] + "..." if len(definitions) > 500 else definitions)
    print("---------------------------------")