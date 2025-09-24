import json

class AgentResponseProcessor:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        # 可以從 system_prompt 中解析出計算說明等資訊，或者直接傳入
        self.calculation_guide = self._parse_calculation_guide(system_prompt)

    def _parse_calculation_guide(self, prompt: str) -> dict:
        """
        從 SYSTEM_PROMPT 中解析計算說明。
        這是一個簡化的範例，實際應用中可能需要更複雜的解析邏輯。
        """
        guide_start = prompt.find("計算說明")
        if guide_start == -1:
            return {}
        
        guide_content = prompt[guide_start:]
        # 這裡可以根據實際的 prompt 格式來提取數據來源、計算方法、計算過程等
        # 為了簡化，我們假設這裡只是一個佔位符
        return {
            "數據來源": "env. 連結的spread_sheet",
            "計算方法": "Pandas DataFrame Agent 進行數據分析",
            "計算過程": "參考計算指南，確保正確理解各項財務指標意義，並嚴格按照指南中的公式判斷'category'、'item_description'，再進行分析。"
        }

    def process_response(self, user_query: str, analysis_result: str) -> str:
        """
        處理數據分析工具提供的結果，並生成專業的財務分析報告。
        """
        # 1. 判斷用戶語意 (簡化處理，實際應更複雜)
        if not self._is_financial_query(user_query):
            return self._generate_casual_chat_response()

        # 2. 解析數據分析結果 (假設 analysis_result 是 JSON 字符串或可解析的文本)
        try:
            # 這裡假設 analysis_result 是一個 JSON 字符串，包含 'core_conclusion', 'data_support', 'table_data', 'insights', 'follow_up_suggestions'
            # 實際情況可能需要更靈活的解析，例如從純文本中提取信息
            parsed_data = json.loads(analysis_result)
        except json.JSONDecodeError:
            # 如果不是 JSON，嘗試作為純文本處理，但功能會受限
            parsed_data = self._parse_text_analysis_result(analysis_result)

        # 3. 組織和美化報告
        report = self._format_financial_report(parsed_data)

        return report

    def _is_financial_query(self, query: str) -> bool:
        """
        判斷用戶查詢是否為財務相關問題。
        這是一個非常簡化的範例，實際應用中需要更強大的 NLU 能力。
        """
        financial_keywords = ["財務", "收入", "支出", "利潤", "成本", "分析", "報表", "損益", "現金流", "資產", "負債", "股東權益"]
        return any(keyword in query for keyword in financial_words)

    def _generate_casual_chat_response(self) -> str:
        """
        生成隨意聊聊的回應，帶點幽默感。
        """
        responses = [
            "哈囉！今天天氣真好，不過我只懂數字，對天氣預報可不在行呢！有什麼財務上的疑難雜症需要我幫忙嗎？",
            "嗯... 這個問題好像不在我的「財務雷達」範圍內耶！不過，如果你想聊聊怎麼讓錢包變胖，我可就來勁了！",
            "抱歉，我只對數字和報表情有獨鍾。如果你想知道你的錢都去哪兒了，我倒是可以給你一些「驚喜」！"
        ]
        import random
        return random.choice(responses)

    def _parse_text_analysis_result(self, result_text: str) -> dict:
        """
        從純文本分析結果中解析數據。
        這是一個非常基礎的範例，需要根據實際的文本格式進行調整。
        """
        data = {
            "核心結論": "根據初步分析，您的財務狀況呈現穩定趨勢。",
            "數據支持": "詳細數據請參考下方報告。",
            "表格數據": [],
            "專業洞見": "建議持續關注主要收入來源的穩定性。",
            "後續建議": "可以進一步分析各項支出的細節，找出潛在的節省空間。"
        }
        
        # 這裡可以加入更複雜的文本解析邏輯，例如使用正則表達式提取關鍵信息
        # 為了範例，我們假設一些預設值
        if "總收入" in result_text:
            import re
            match = re.search(r"總收入：(\d+)", result_text)
            if match:
                data["核心結論"] = f"您的總收入達到 **{match.group(1)}**，表現亮眼！"
                data["數據支持"] = f"總收入：**{match.group(1)}** 元。"
                data["表格數據"].append({"項目": "總收入", "金額": int(match.group(1))})
        
        if "總支出" in result_text:
            import re
            match = re.search(r"總支出：(\d+)", result_text)
            if match:
                data["數據支持"] += f" 總支出：**{match.group(1)}** 元。"
                data["表格數據"].append({"項目": "總支出", "金額": int(match.group(1))})

        return data

    def _format_financial_report(self, data: dict) -> str:
        """
        將解析後的數據格式化為專業的財務分析報告。
        """
        report_parts = []

        # 核心結論
        core_conclusion = data.get("核心結論", "抱歉，這次的分析結果有點害羞，沒能給出明確的核心結論。")
        report_parts.append(f"**核心結論**：{core_conclusion}\n")

        # 數據支持
        data_support = data.get("數據支持", "這次的數據有點神秘，沒有提供具體的支持點。")
        report_parts.append(f"**數據支持**：{data_support}\n")

        # 視覺化說明 (Markdown 表格)
        table_data = data.get("表格數據", [])
        if table_data:
            report_parts.append("**視覺化說明**：\n")
            report_parts.append("| 項目 | 金額 |")
            report_parts.append("|---|---|")
            for row in table_data:
                report_parts.append(f"| {row.get('項目', '')} | **{row.get('金額', '')}** |")
            report_parts.append("\n")
        else:
            report_parts.append("**視覺化說明**：這次的數據沒有適合用表格呈現的部分，不過別擔心，我會繼續努力挖掘！\n")

        # 專業洞見
        insights = data.get("專業洞見", "嗯... 這次的數據讓我陷入了沉思，暫時沒有特別的洞見。")
        report_parts.append(f"**專業洞見**：{insights}\n")

        # 後續建議
        follow_up_suggestions = data.get("後續建議", "目前看來一切安好，暫時沒有後續建議。")
        report_parts.append(f"**後續建議**：{follow_up_suggestions}\n")

        # 加入幽默結尾
        humorous_endings = [
            "記住，理財就像減肥，管住嘴（支出）邁開腿（收入），才能看到好身材（財富）！",
            "財務分析師的日常就是和數字談戀愛，雖然有時會被它們搞得頭暈眼花，但最終總能發現它們的美！",
            "希望這份報告能幫助您更了解您的財務狀況，如果還有其他數字想跟我聊聊，隨時找我喔！"
        ]
        import random
        report_parts.append(f"\n{random.choice(humorous_endings)}")

        return "\n".join(report_parts)

# 範例使用 (這部分不會在實際運行中執行，僅供參考)
if __name__ == "__main__":
    # 模擬 SYSTEM_PROMPT
    mock_system_prompt = """你是一位頂尖的財務分析師，回應風格幽默，你的任務是解讀由數據分析工具提供的結果，並以清晰、專業的格式呈現給用戶。

    **你的工作流程：**
    1.  先判斷用戶語意，是否為財務相關問題，如果不是，就直接隨便聊聊。
    2.  若是財務問題，你會收到一個包含數據分析結果的文字。
    3.  你的任務是將這個結果重新組織和美化，使其成為一份專業的財務分析報告。
    4.  **絕對不要重新計算任何數字**。你收到的結果已經是經過精確計算的，你的工作是呈現它。
    5.  **一定要參考計算說明**，這將幫助你理解數據的背景和意義。

    **回應內容：**
    1.  **核心結論**：用1-2句話總結分析結果的核心發現。
    2.  **數據支持**：清晰地列出支持結論的關鍵數據點或計算過程。
    3.  **視覺化說明**：如果分析結果包含表格或列表，請使用 Markdown 表格來美化它，使其更易於閱讀。
    4.  **專業洞見**：根據分析結果，提供1-2點有價值的財務洞見或建議。
    5.  **後續建議**：視情況提供可能的後續分析方向。

    **計算說明**
    1. **數據來源**：所有數據均來自env. 連結的spread_sheet，並理解用戶問題，篩選正確的數據範圍。
    2. **計算方法**：使用 Pandas DataFrame Agent 進行數據分析，並確保所有計算都基於用戶提供的數據。
    3. **計算過程**：務必參考計算指南，確保正確理解各項財務指標意義，並嚴格按照指南中的公式判斷'category'、'item_description'，再進行分析。
    請務必使用**繁體中文**回應，語言風格應專業且易於理解。使用**粗體**標記重要的數字和結論。
    """

    processor = AgentResponseProcessor(mock_system_prompt)

    # 模擬財務分析結果 (JSON 格式)
    mock_financial_result_json = json.dumps({
        "core_conclusion": "本月您的收入表現強勁，但餐飲支出略有超標。",
        "data_support": "總收入：**50,000** 元，總支出：**30,000** 元。其中餐飲支出佔總支出的 **40%**。",
        "table_data": [
            {"項目": "總收入", "金額": 50000},
            {"項目": "總支出", "金額": 30000},
            {"項目": "餐飲支出", "金額": 12000},
            {"項目": "交通支出", "金額": 5000}
        ],
        "insights": "餐飲支出是您本月最大的開銷，若能有效控制，將顯著提升儲蓄率。",
        "follow_up_suggestions": "建議您下個月設定餐飲預算，並追蹤每日花費，同時可以考慮增加被動收入來源。"
    })

    # 模擬財務分析結果 (純文本格式)
    mock_financial_result_text = """
    分析結果：
    總收入：55000
    總支出：32000
    淨利潤：23000
    本月餐飲支出較高，佔比約35%。
    """

    # 模擬非財務查詢
    mock_non_financial_query = "今天天氣怎麼樣？"

    print("--- 測試非財務查詢 ---")
    print(processor.process_response(mock_non_financial_query, ""))
    print("\n" + "="*50 + "\n")

    print("--- 測試財務查詢 (JSON 格式結果) ---")
    print(processor.process_response("請分析我本月的財務狀況", mock_financial_result_json))
    print("\n" + "="*50 + "\n")

    print("--- 測試財務查詢 (純文本格式結果) ---")
    print(processor.process_response("請給我一份財務報告", mock_financial_result_text))
    print("\n" + "="*50 + "\n")