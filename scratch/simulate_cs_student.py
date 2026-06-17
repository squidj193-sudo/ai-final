# -*- coding: utf-8 -*-
import os
import sys
import time
import asyncio
from pathlib import Path

# Force UTF-8 stdout to prevent Windows console encoding crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Load .env variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

async def run_simulation():
    from agent_core import AgentCore
    print("=" * 60)
    # Persona: 逢甲大學資訊工程學系 大三學生
    print("  資工系學生專題探索模擬測試 (真實 API 呼叫)")
    print("=" * 60)
    
    session_id = f"cs_student_sim_{int(time.time())}"
    print(f"模擬 Session ID: {session_id}")
    
    # 1. 初始化
    print("\n[1/5] 正在初始化 Agent 核心...")
    start_time = time.time()
    agent = AgentCore()
    print(f"--> AgentCore 初始化完成，耗時: {time.time() - start_time:.4f}s")
    
    # 2. 鎖定主題
    query_direction = "我想研究結合機器學習與賠率的賽馬預測模型，做為我的資工畢業專題"
    print(f"\n[2/5] 階段一：輸入模糊想法以鎖定研究主題...")
    print(f"使用者輸入: \"{query_direction}\"")
    start = time.time()
    res1 = await agent.chat(session_id, query_direction)
    print(f"--> 耗時: {time.time() - start:.4f}s")
    print(f"回覆類型: {res1.get('type')}")
    print(f"回覆內容:\n{res1.get('content')}\n")
    
    # 3. 搜尋論文
    query_search = "幫我搜尋賽馬預測與動態賠率的英文學術文獻"
    print(f"\n[3/5] 階段二：進行文獻檢索與自動摘要 (Zero-Turn)...")
    print(f"使用者輸入: \"{query_search}\"")
    start = time.time()
    res2 = await agent.chat(session_id, query_search)
    print(f"--> 耗時: {time.time() - start:.4f}s")
    print(f"回覆類型: {res2.get('type')}")
    print(f"找到論文數: {len(res2.get('papers', []))}")
    
    summaries = agent.get_summaries(session_id)
    print(f"目前已儲存的論文摘要數: {len(summaries)}")
    for idx, s in enumerate(summaries):
        print(f"  📄 {idx+1}. {s['title']} ({s['year'] or '未知'})")
        print(f"     * 目的: {s['research_goal']}")
        print(f"     * 限制: {s['limitations']}")

    # 4. 生成比較矩陣
    print(f"\n[4/5] 階段三：生成文獻比較矩陣 (Zero-Turn)...")
    
    # 確保有至少兩篇文獻供矩陣生成。若不足，則手動注入一篇做測試
    if len(summaries) < 2:
        print("   [!] 論文數量不足 2 篇，手動注入第二篇賽馬論文以利測試比較矩陣...")
        from skills.analysis_skill import PaperSummary
        mock_summary = PaperSummary(
            paper_id="mock_paper_02",
            title="An Ensemble Model for Horse Racing Prediction Using Odds Movements",
            authors=["Smith, J.", "Brown, T."],
            year=2024,
            research_goal="To improve horse racing prediction by leveraging real-time odds fluctuations.",
            methodology="Ensemble gradient boosting (XGBoost) combined with betting volume analysis.",
            main_findings="Real-time odds movements carry significant predictive power, yielding 12% higher ROI than static models.",
            limitations="Sensitive to sudden betting volume anomalies.",
            keywords=["odds movements", "horse racing", "prediction", "XGBoost"]
        )
        if session_id not in agent._summaries:
            agent._summaries[session_id] = []
        agent._summaries[session_id].append(mock_summary)
        agent._save_session_data()
        
    print("發送指令: \"請幫我把這些文獻生成比較矩陣表格\"")
    start = time.time()
    res3 = await agent.chat(session_id, "請幫我把這些文獻生成比較矩陣表格")
    print(f"--> 耗時: {time.time() - start:.4f}s")
    print(f"回覆類型: {res3.get('type')}")
    print(f"比較矩陣內容 Preview:\n{res3.get('content')[:800]}\n...")

    # 5. 分析方向並產出題目建議
    query_report = "分析這些文獻的研究缺口，並給出具體的資工專題題目與研究方向建議"
    print(f"\n[5/5] 階段四：研究缺口分析與專題題目產出 (Zero-Turn)...")
    print(f"使用者輸入: \"{query_report}\"")
    start = time.time()
    res4 = await agent.chat(session_id, query_report)
    print(f"--> 耗時: {time.time() - start:.4f}s")
    print(f"回覆類型: {res4.get('type')}")
    print(f"\n================== 🎯 AI 專題題目建議報告 🎯 ==================")
    print(res4.get("content"))
    print("==============================================================")
    
    print("\n[OK] 模擬測試結束！")

if __name__ == "__main__":
    asyncio.run(run_simulation())
