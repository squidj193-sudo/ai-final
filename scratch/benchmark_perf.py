# -*- coding: utf-8 -*-
import os
import sys
import time
from pathlib import Path

# Force stdout to write UTF-8 to prevent console CP950 decoding/encoding crashes on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Load .env variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

print("=" * 60)
print("  AI Research Assistant -- Performance Benchmark (Real API - UTF-8)")
print("=" * 60)

# 1. Benchmark Loading AgentCore
print("\n[1/5] Benchmarking Backend Core Initialization...")
start_time = time.time()
try:
    from agent_core import AgentCore
    agent = AgentCore()
    init_time = time.time() - start_time
    print(f"  --> AgentCore initialized in: {init_time:.4f}s [OK]")
except Exception as e:
    print(f"  [X] Failed to initialize AgentCore: {e}")
    sys.exit(1)

# 2. Benchmark Intent Detection (Gemini Call)
print("\n[2/5] Benchmarking Intent Detection (Real Gemini 26B Latency)...")
# Send clean UTF-8 strings directly as variables to avoid subprocess standard input conversion issues
test_messages = [
    u"我想做關於鈣鈦礦太陽能電池元件效能的研究",
    u"幫我搜尋 Quantum Computing 相關的文獻",
    u"生成已儲存論文的比較矩陣表格"
]
for idx, msg in enumerate(test_messages):
    start = time.time()
    try:
        import asyncio
        res = asyncio.run(agent.detect_intent(msg))
        duration = time.time() - start
        print(f"  Test {idx+1}: Success!")
        print(f"    --> Intent: {res.get('intent')} | Query: {res.get('query')}")
        print(f"    --> Duration: {duration:.4f}s")
    except Exception as e:
        print(f"    [X] Failed intent detection: {e}")

# 3. Benchmark Knowledge Graph Calculation (NetworkX & TF-IDF)
print("\n[3/5] Benchmarking Session Graph Calculation...")
from skills.graph_skill import SessionGraphSkill
g_skill = SessionGraphSkill()

# Generate mock paper summaries to test scaling
def make_mock_summaries(count):
    return [
        {
            "paper_id": f"p_{i}",
            "title": f"Paper Title of Carbon Nanotubes and Semiconductor Device {i}",
            "authors": [f"Author {i}A", f"Author {i}B"],
            "year": 2020 + (i % 5),
            "research_goal": f"To optimize the energy conversion efficiency of perovskite solar cells using novel additive materials {i}.",
            "main_findings": f"We discovered that semiconductor polymers improve film stability and charge extraction rate {i}.",
            "limitations": f"High manufacturing cost and degradation under high moisture conditions {i}.",
            "keywords": ["perovskite", "solar cell", "semiconductor", "stability"]
        }
        for i in range(count)
    ]

sizes = [2, 5, 15]
for size in sizes:
    summaries = make_mock_summaries(size)
    start = time.time()
    data = g_skill.get_graph_data(summaries)
    duration = time.time() - start
    print(f"  Size: {size:2d} papers | Nodes: {len(data['nodes'])} | Edges: {len(data['edges'])} | Time: {duration:.4f}s")

# 4. Benchmark Academic Search Cache & Real API
print("\n[4/5] Benchmarking Academic Search (Real API Query)...")
start = time.time()
try:
    async def run_search_test():
        # Clear specific key cache in memory to force real API call (or use a unique query)
        unique_query = f"perovskite efficiency novel cell {int(time.time())}"
        return await agent.search_skill.search(unique_query, limit=3)
    papers = asyncio.run(run_search_test())
    duration = time.time() - start
    print(f"  --> Real API Search returned {len(papers)} papers in: {duration:.4f}s")
except Exception as e:
    duration = time.time() - start
    print(f"  [!] Real API Search execution details (took {duration:.4f}s): {e}")

# 5. Benchmark RAG Store Querying (Local Text Similarity Search)
print("\n[5/5] Benchmarking Local RAG Query (TF-IDF Match)...")
start = time.time()
try:
    # Query something
    rag_results = agent.rag_store.query("perovskite solar cell stability", n_results=3)
    duration = time.time() - start
    print(f"  --> RAG Query matched {len(rag_results)} chunks in: {duration:.4f}s")
except Exception as e:
    print(f"  [X] RAG query failed: {e}")

print("\n" + "=" * 60)
print("  Benchmark Run Complete!")
print("=" * 60)
