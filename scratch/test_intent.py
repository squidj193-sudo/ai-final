import os
import sys
import asyncio
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from agent_core import AgentCore

async def test():
    # Make sure we load the env variables
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / "backend" / ".env")
    
    agent = AgentCore()
    
    queries = [
        "貓的論文可以做甚麼",
        "貓咪有論文可以做嗎",
        "分析研究方向",
        "生成研究方向建議",
        "我想做寵物相關論文"
    ]
    
    print("Testing intent classification...")
    for q in queries:
        res = await agent.detect_intent(q)
        print(f"Query: '{q}' -> Detected Intent: {res.get('intent')} | Query parameter: {res.get('query')}")

if __name__ == "__main__":
    asyncio.run(test())
