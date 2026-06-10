# -*- coding: utf-8 -*-
import json
import shutil
from pathlib import Path

def main():
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 重設 session_data.json 為全新空的結構
    session_data = {
        "summaries": {},
        "matrix_cache": {},
        "direction_cache": {},
        "conversations": [],
        "chat_history": {},
        "role_states": {}
    }
    with open(data_dir / "session_data.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    # 2. 清空 role_state.json
    with open(data_dir / "role_state.json", "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

    # 3. 清空 search_cache.json
    with open(data_dir / "search_cache.json", "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

    # 4. 清理本機上傳論文儲存庫
    papers_dir = data_dir / "papers"
    if papers_dir.exists():
        shutil.rmtree(papers_dir)
    papers_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("  [OK] 系統資料已成功重設為「完全空白」狀態！")
    print("  - 已清除所有對話紀錄與 Session 歷史")
    print("  - 已清空所有上傳之論文與 RAG 資料")
    print("  - 已重設所有研究領域範疇狀態")
    print("  - 現在您可以進行全新的乾淨人工測試。")
    print("==================================================")

if __name__ == "__main__":
    main()
