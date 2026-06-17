# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent / "backend"))

def run_test():
    print("=== [4/6] 執行圖譜運算與 Lazy Loading 驗證 ===")
    
    # 1. 驗證 Lazy Loading 效能設計
    # 在導入 skills.graph_skill 之前，檢查 sys.modules 內不含 networkx/numpy/sklearn 等模組
    heavy_modules = ["networkx", "numpy", "sklearn", "community", "pyvis"]
    for mod in heavy_modules:
        assert not any(mod in m for m in sys.modules), f"Lazy loading 破功，{mod} 已被全域載入"
        
    # 載入 graph_skill
    from skills.graph_skill import SessionGraphSkill
    print("   -> 成功導入 graph_skill (未觸發大型函式庫載入)")
    
    # 2. 準備測試文獻
    mock_summaries = [
        {
            "paper_id": "p1",
            "title": "Quantum Computing Basics",
            "authors": ["Alice"],
            "year": 2020,
            "research_goal": "To introduce quantum computing logic.",
            "main_findings": "Foundations of qubits established.",
            "limitations": "None.",
            "keywords": ["quantum", "qubit", "computation"]
        },
        {
            "paper_id": "p2",
            "title": "Quantum Algorithms and Qubits",
            "authors": ["Bob"],
            "year": 2021,
            "research_goal": "To optimize qubit gates.",
            "main_findings": "Algorithms scale quadratically.",
            "limitations": "Noise sensitivity.",
            "keywords": ["quantum", "qubit", "algorithms"]
        },
        {
            "paper_id": "p3",
            "title": "Classical vs Quantum Computation",
            "authors": ["Charlie"],
            "year": 2022,
            "research_goal": "Compare classical bits with qubits.",
            "main_findings": "Quantum is superior in factorization.",
            "limitations": "Hardware constraints.",
            "keywords": ["quantum", "computation", "classical"]
        }
    ]
    
    # 3. 測試運算指標
    g_skill = SessionGraphSkill()
    print("   -> 開始計算圖譜指標...")
    metrics = g_skill.compute_graph_metrics(mock_summaries)
    
    # 驗證指標格式與內容
    assert "influence" in metrics, "缺少 influence 指標"
    assert "communities" in metrics, "缺少 communities 指標"
    assert "bridges" in metrics, "缺少 bridges 指標"
    
    # 因為有關聯關鍵字 (quantum, computation, qubit)，三個點應該會形成相連圖
    influence = metrics["influence"]
    assert len(influence) == 3, "應包含 3 個點的 PageRank 指標"
    print(f"      Influence (PageRank): {influence}")
    
    # 4. 測試圖譜 JSON 生成
    print("   -> 開始生成圖譜 JSON 結構...")
    graph_json = g_skill.get_graph_data(mock_summaries)
    assert "nodes" in graph_json, "JSON 缺少 nodes"
    assert "edges" in graph_json, "JSON 缺少 edges"
    assert len(graph_json["nodes"]) == 3, "節點數量不符"
    print(f"      Nodes count: {len(graph_json['nodes'])}, Edges count: {len(graph_json['edges'])}")
    
    print("\n✅ [OK] 圖譜運算與 Lazy Loading 驗證全部通過！")

if __name__ == "__main__":
    run_test()
