# -*- coding: utf-8 -*-
import os
import sys
import time
import asyncio
from pathlib import Path

# Force UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Load env variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

async def run_e2e_test():
    from agent_core import AgentCore
    print("============================================================")
    print("        🏇 AI 研究助理 — 賽馬主題 E2E 全流程整合測試 🏇")
    print("============================================================\n")

    session_id = f"e2e_horseracing_{int(time.time())}"
    print(f"測試 Session ID: {session_id}")
    
    print("\n[1/5] 初始化 Agent 核心系統...")
    start_init = time.time()
    agent = AgentCore()
    print(f"--> 初始化成功，耗時: {time.time() - start_init:.4f}s")

    # 步驟一：設定研究方向
    print("\n[2/5] 步驟一：設定研究方向...")
    direction_msg = "我想研究結合機器學習與動態賠率的賽馬預測模型"
    print(f"對話輸入: \"{direction_msg}\"")
    start = time.time()
    res1 = await agent.chat(session_id=session_id, message=direction_msg)
    print(f"--> 方向設定完成，耗時: {time.time() - start:.4f}s")
    print(f"    目前研究方向: {agent.state_skill.get_state(session_id).large_direction}")

    # 步驟二：學術文獻搜尋與自動摘要
    print("\n[3/5] 步驟二：學術文獻搜尋與自動摘要 (Zero-Turn)...")
    search_msg = "幫我搜尋賽馬預測模型的相關文獻"
    print(f"對話輸入: \"{search_msg}\"")
    start = time.time()
    res2 = await agent.chat(session_id=session_id, message=search_msg)
    print(f"--> 搜尋與分析完成，耗時: {time.time() - start:.4f}s")
    
    summaries = agent.get_summaries(session_id)
    print(f"    自動生成摘要論文數: {len(summaries)} 篇")
    for idx, s in enumerate(summaries):
        print(f"    📄 {idx+1}. {s['title']} ({s['year'] or '未知'})")

    if len(summaries) < 2:
        print("\n[!] 論文數量不足，手動注入第2篇賽馬論文以利後續矩陣分析...")
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
        summaries = agent.get_summaries(session_id)
        print(f"    [OK] 注入成功。目前論文數: {len(summaries)} 篇")

    # 步驟三：生成比較矩陣
    print("\n[4/5] 步驟三：生成文獻比較矩陣 (Zero-Turn)...")
    matrix_msg = "生成比較矩陣表格"
    print(f"對話輸入: \"{matrix_msg}\"")
    start = time.time()
    res3 = await agent.chat(session_id=session_id, message=matrix_msg)
    print(f"--> 比較矩陣生成完成，耗時: {time.time() - start:.4f}s")
    print(f"\n--- 比較矩陣 Preview ---\n{res3.get('content')[:500]}...\n----------------------")

    # 步驟四：研究方向建議與終期報告產出
    print("\n[5/5] 步驟四：缺口分析與研究方向建議報告 (Zero-Turn)...")
    report_msg = "分析文獻並給出可行的研究方向與題目建議"
    print(f"對話輸入: \"{report_msg}\"")
    start = time.time()
    res4 = await agent.chat(session_id=session_id, message=report_msg)
    print(f"--> 研究建議報告生成完成，耗時: {time.time() - start:.4f}s")
    
    print("\n================== 🎯 最終研究建議報告 🎯 ==================")
    print(res4.get("content"))
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
