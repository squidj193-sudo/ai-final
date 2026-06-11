# -*- coding: utf-8 -*-
import os
import sys
import shutil
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent / "backend"))

def run_test():
    print("=== [5/6] 執行 RAG 檢索管線測試 ===")
    from tools.rag import RAGStore
    
    # 建立測試目錄
    test_db_dir = "data/test_rag_db"
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    try:
        rag = RAGStore(db_path=test_db_dir)
        
        # 1. 測試加入文獻與自動切片
        doc1_content = "This is a paper about perovskite solar cell stability. Perovskite materials have high efficiency."
        doc2_content = "This paper talks about quantum computing algorithms. Quantum gates can run faster than classical gates."
        
        chunks1 = rag.add_document("p1", doc1_content, {"title": "Perovskite Stability", "year": 2025})
        chunks2 = rag.add_document("p2", doc2_content, {"title": "Quantum Algorithms", "year": 2026})
        
        assert chunks1 > 0, "應回傳切片數量"
        assert os.path.exists(os.path.join(test_db_dir, "p1.md")), "Markdown 檔案應寫入"
        assert os.path.exists(os.path.join(test_db_dir, "p1.json")), "Metadata JSON 檔案應寫入"
        print("   -> 文件寫入與 JSON 序列化成功！")
        
        # 2. 測試關鍵字檢索與評分排序
        print("2. 測試詞頻評分檢索...")
        results = rag.query("perovskite solar cell stability")
        assert len(results) >= 1, "應該能檢索出結果"
        # 第一筆結果應該是 p1（因為包含 perovskite, solar, cell, stability，得分高）
        assert results[0]["metadata"]["paper_id"] == "p1", "得分排序錯誤"
        assert "stability" in results[0]["content"], "內容檢索不符"
        print("   -> Perovskite 相關詞頻評分排序成功！")
        
        # 3. 測試無相符字詞的回傳
        print("3. 測試無關鍵字匹配...")
        results_empty = rag.query("supercalifragilisticexpialidocious")
        assert len(results_empty) == 0, "無匹配時應回傳空清單"
        print("   -> 空匹配處理成功！")
        
        print("\n✅ [OK] RAG 檢索管線測試全部通過！")
        
    finally:
        if os.path.exists(test_db_dir):
            shutil.rmtree(test_db_dir)

if __name__ == "__main__":
    run_test()
