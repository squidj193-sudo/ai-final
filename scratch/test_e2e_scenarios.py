# -*- coding: utf-8 -*-
import os
import sys
import shutil
import asyncio
from pathlib import Path
import google.generativeai as genai

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Load env variables just in case
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

# Detailed mock classes matching Gemini response structure
class MockFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args

class MockPart:
    def __init__(self, text=None, function_call=None):
        self.text = text
        self.function_call = function_call

class MockContent:
    def __init__(self, parts):
        self.parts = parts

class MockCandidate:
    def __init__(self, content):
        self.content = content

class MockResponse:
    def __init__(self, text=None, function_call=None):
        self.text = text
        parts = []
        if text:
            parts.append(MockPart(text=text))
        if function_call:
            parts.append(MockPart(function_call=function_call))
        self.candidates = [MockCandidate(MockContent(parts))]

# Global mock response router
def model_response_generator(prompt):
    prompt_str = str(prompt)
    
    # 1. 意圖判定 (INTENT_PROMPT)
    if "分析以下使用者訊息，判斷其意圖類型" in prompt_str:
        if "我想研究" in prompt_str or "研究方向" in prompt_str:
            return MockResponse(text='{"intent": "set_direction", "query": "機器學習 賽馬預測"}')
        elif "搜尋" in prompt_str or "尋找" in prompt_str:
            return MockResponse(text='{"intent": "search", "query": "horse racing prediction"}')
        elif "對比" in prompt_str or "矩陣" in prompt_str:
            return MockResponse(text='{"intent": "matrix", "query": ""}')
        elif "缺口" in prompt_str or "方向建議" in prompt_str:
            return MockResponse(text='{"intent": "direction", "query": ""}')
    
    # 2. 方向特徵提取 (_extract_directions_from_message)
    if "大方向" in prompt_str and "中方向" in prompt_str:
        return MockResponse(text='{"large_direction": "人工智慧", "medium_direction": "機器學習", "small_direction": "賽馬預測"}')
        
    # 3. 論文摘要生成 (SUMMARY_PROMPT)
    if "你是一位學術研究助理。請根據以下論文內容" in prompt_str:
        return MockResponse(text="""
        {
          "title": "Machine Learning for Horse Racing",
          "authors": ["John Doe", "Jane Smith"],
          "year": 2024,
          "research_goal": "To predict horse racing outcomes using machine learning.",
          "methodology": "Neural networks and logistic regression.",
          "main_findings": "Achieved 72% prediction accuracy.",
          "limitations": "Does not account for real-time odds fluctuations.",
          "keywords": ["horse racing", "machine learning", "prediction"]
        }
        """)
        
    # 4. 關鍵字翻譯 (_translate_query_to_english)
    if "翻譯並優化成適合在英文論文數據庫" in prompt_str:
        return MockResponse(text="horse racing prediction machine learning")
        
    # 5. 建議追問 (_generate_suggestions)
    if "為使用者生成 3 個可能想要點選的後續追問問題" in prompt_str:
        return MockResponse(text='["分析第一篇論文", "生成比較表格", "提出進一步方向"]')
        
    # 6. 核心對話：當用戶想要設定研究方向時，觸發 Native Function Calling
    if "我想研究結合機器學習與賠率的賽馬模型" in prompt_str:
        fc = MockFunctionCall(
            name="set_research_direction",
            args={"research_direction": "結合機器學習與賠率的賽馬模型"}
        )
        return MockResponse(function_call=fc)
        
    return MockResponse(text="對話回覆偏好設定：已收到。")

# Global mock of GenerativeModel class
class MockGenerativeModel:
    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
    def generate_content(self, prompt, *args, **kwargs):
        return model_response_generator(prompt)

# Override the SDK class globally
genai.GenerativeModel = MockGenerativeModel

async def run_test():
    print("=== [6/6] 執行端對端 (E2E) 整合鏈路測試 ===")
    
    # 備份原有 session 檔案
    orig_session_path = Path("data/session_data.json")
    backup_session_path = Path("data/session_data.json.bak")
    if orig_session_path.exists():
        shutil.copy(orig_session_path, backup_session_path)
        
    try:
        from agent_core import AgentCore
        agent = AgentCore()
        
        session_id = "e2e_test_session_999"
        
        # 步驟一：設定方向
        print("\n步驟一：設定方向「我想研究結合機器學習與賠率的賽馬模型」...")
        
        # 為了讓搜尋不會真的對外打請求，我們 mock 掉搜尋
        async def mock_search(query, context="", limit=10):
            from skills.search_skill import PaperResult
            return [
                PaperResult(
                    paper_id="paper_999_001",
                    title="Machine Learning for Horse Racing",
                    authors=["John Doe", "Jane Smith"],
                    year=2024,
                    abstract="To predict horse racing outcomes using machine learning.",
                    url="http://example.com/racing",
                    doi="10.1000/racing"
                )
            ]
        agent.search_skill.search = mock_search
        
        res1 = await agent.chat(session_id, "我想研究結合機器學習與賠率的賽馬模型")
        if res1.get("type") == "error":
            print(f"Error detail: {res1.get('content')}")
        assert res1["type"] == "analyze", f"應回傳分析型內容，但回傳: {res1.get('type')}"
        assert agent.state_skill.get_state(session_id).research_direction == "結合機器學習與賠率的賽馬模型"
        print(f"   -> 設定方向成功！目前方向: {agent.state_skill.get_state(session_id).research_direction}")
        
        # 步驟二：學術搜尋與自動摘要
        print("\n步驟二：搜尋文獻「搜尋賽馬預測論文」...")
        res2 = await agent.chat(session_id, "搜尋賽馬預測論文")
        assert res2["type"] == "search"
        assert len(agent._summaries[session_id]) == 1
        print("   -> 搜尋與自動摘要成功！已儲存摘要。")
        
        # 步驟三：生成比較矩陣
        print("\n步驟三：生成比較矩陣...")
        # 手動多加入一篇摘要以通過 2 篇限制
        from skills.analysis_skill import PaperSummary
        mock_summary2 = PaperSummary(
            paper_id="paper_999_002",
            title="Real-time Odds for Prediction",
            authors=["Bob Brown"],
            year=2025,
            research_goal="Incorporate odds.",
            methodology="XGBoost.",
            main_findings="Improved ROI.",
            limitations="No historical jockey data.",
            keywords=["odds", "racing"]
        )
        agent._summaries[session_id].append(mock_summary2)
        
        # Mock 矩陣生成
        async def mock_build_matrix(*args, **kwargs):
            return "| 論文 | 目的 | 方法 | 主要發現 | 限制 |\n| --- | --- | --- | --- | --- |\n| ML for Horse Racing | 預測賽馬結果 | 神經網路 | 72% 準確率 | 缺乏即時賠率 |"
        agent.matrix_skill.build_matrix = mock_build_matrix
        
        res3 = await agent.chat(session_id, "生成比較矩陣表格")
        assert res3["type"] == "matrix"
        print("   -> 比較矩陣生成成功！")
        
        # 步驟四：研究方向建議報告
        print("\n步驟四：生成課題方向建議...")
        # Mock 方向建議報告
        async def mock_analyze_report(*args, **kwargs):
            return "建議方向：1. 結合即時賠率；2. 融合騎師歷史數據。"
        agent.direction_skill.analyze = mock_analyze_report
        
        res4 = await agent.chat(session_id, "分析文獻並給出可行的研究方向與題目建議")
        assert res4["type"] == "direction"
        print("   -> 建議課題報告生成成功！")
        
        print("\n✅ [OK] 端對端 (E2E) 整合鏈路測試全部通過！")
        
    except Exception as e:
        print(f"\n❌ [ERROR] E2E 整合鏈路測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # 還原 Session 檔案
        if backup_session_path.exists():
            if orig_session_path.exists():
                os.remove(orig_session_path)
            shutil.move(backup_session_path, orig_session_path)

if __name__ == "__main__":
    asyncio.run(run_test())
