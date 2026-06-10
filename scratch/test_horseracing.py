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

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

async def test_single_query():
    from agent_core import AgentCore
    print("正在初始化 AgentCore...")
    start_init = time.time()
    agent = AgentCore()
    print(f"AgentCore 初始化耗時: {time.time() - start_init:.4f}s")
    
    query = "我想做賽馬論文"
    print(f"\n對話輸入: \"{query}\"")
    
    # 測試對話處理速度與結果
    start_time = time.time()
    result = await agent.chat(session_id="benchmark_session", message=query)
    duration = time.time() - start_time
    
    print("\n================ 結果 ================")
    print(f"總耗時: {duration:.4f}s")
    print(f"回覆類型 (Type): {result.get('type')}")
    print(f"回覆內容 (Content):\n{result.get('content')}")
    print(f"建議追問 (Suggestions): {result.get('suggestions')}")
    print("======================================")

if __name__ == "__main__":
    asyncio.run(test_single_query())
