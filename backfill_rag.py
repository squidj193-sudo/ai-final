"""
補丁腳本：將 session_data.json 中現有的搜尋論文摘要補寫到 RAG store
"""
import json
import sys
sys.path.insert(0, './backend')

from tools.rag import RAGStore
from pathlib import Path

# 初始化 RAG store
rag = RAGStore(db_path="./backend/data/papers")

# 讀取 session_data.json
data = json.load(open('./backend/data/session_data.json', 'r', encoding='utf-8'))

total = 0
for sid, summaries in data.get('summaries', {}).items():
    for s in summaries:
        pid = s.get('paper_id', '')
        title = s.get('title', '（無標題）')
        year = s.get('year')
        
        # 使用安全的檔名格式來判斷是否已存在
        safe_id = RAGStore.sanitize_paper_id(pid)
        md_file = Path(f"./backend/data/papers/{safe_id}.md")
        if md_file.exists():
            print(f"  [SKIP] {title[:60]} (already in RAG: {safe_id}.md)")
            continue

        
        # 組裝 Markdown 內容
        content = f"# {title}\n\n"
        authors = s.get('authors', [])
        if authors:
            content += f"**作者：** {', '.join(authors[:5])}\n\n"
        if year:
            content += f"**年份：** {year}\n\n"
        
        research_goal = s.get('research_goal', '')
        main_findings = s.get('main_findings', '')
        limitations = s.get('limitations', '')
        keywords = s.get('keywords', [])
        
        if research_goal:
            content += f"**研究目的：** {research_goal}\n\n"
        if main_findings:
            content += f"**主要發現：** {main_findings}\n\n"
        if limitations:
            content += f"**研究限制：** {limitations}\n\n"
        if keywords:
            content += f"**關鍵字：** {', '.join(keywords)}\n"
        
        metadata = {
            "title": title,
            "year": year,
            "source": "search"
        }
        
        chunks = rag.add_document(pid, content, metadata)
        print(f"  [OK] {title[:60]} -> {chunks} chunks written")
        total += 1

print(f"\n完成！共補寫 {total} 篇論文至 RAG 索引。")
