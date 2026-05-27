"""
AI 研究助理 Agent — RAG 工具
無 Embedding 版本：以 Markdown 檔案直接儲存並利用關鍵字比對檢索段落
"""
import os
import json
import re
from pathlib import Path
from typing import Optional

# ─── MarkItDown 解析器 ───────────────────────────────────────────────
try:
    from markitdown import MarkItDown
    _md_parser = MarkItDown()
except ImportError:
    _md_parser = None


def parse_pdf_to_markdown(file_path: str) -> str:
    """將 PDF 解析為 Markdown 格式字串"""
    if _md_parser is None:
        raise RuntimeError("markitdown 套件未安裝，請執行 pip install markitdown")
    result = _md_parser.convert(file_path)
    return result.text_content


# ─── RAGStore (檔案系統 + 關鍵字比對) ──────────────────────────────────
class RAGStore:
    """管理論文 Markdown 本地檔案儲存與無 Embedding 語意/關鍵字檢索"""

    def __init__(self, db_path: str = "./data/papers"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

    def add_document(
        self,
        paper_id: str,
        content: str,
        metadata: Optional[dict] = None,
        chunk_size: int = 1500,
        overlap: int = 300,
    ) -> int:
        """將文件與元資料直接寫入本地 Markdown 與 JSON 檔案"""
        # 1. 寫入 Markdown 檔案
        md_file = self.db_path / f"{paper_id}.md"
        md_file.write_text(content, encoding="utf-8")

        # 2. 寫入 Metadata 檔案
        meta_file = self.db_path / f"{paper_id}.json"
        meta_data = metadata or {}
        meta_data["paper_id"] = paper_id
        meta_file.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 3. 回傳切分的段落數
        chunks = self._chunk_text(content, chunk_size, overlap)
        return len(chunks)

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """基於關鍵字/詞頻匹配的本地文件檢索"""
        query_words = [w.lower() for w in re.findall(r'\w+', query_text) if len(w) > 1]
        if not query_words:
            # 如果沒有有效關鍵字，回傳空清單
            return []

        all_candidates = []

        # 遍歷所有已儲存的論文檔案
        for md_file in self.db_path.glob("*.md"):
            paper_id = md_file.stem
            meta_file = self.db_path / f"{paper_id}.json"
            
            # 讀取 Metadata
            metadata = {}
            if meta_file.exists():
                try:
                    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            content = md_file.read_text(encoding="utf-8")
            # 將內文切分為 chunks (使用與 add 相同的 chunk 策略)
            chunks = self._chunk_text(content, size=1500, overlap=300)

            for i, chunk in enumerate(chunks):
                # 簡單計算詞頻得分
                chunk_lower = chunk.lower()
                score = 0
                for word in query_words:
                    # 給予精確匹配更高的分數，也支持部分匹配
                    count = chunk_lower.count(word)
                    if count > 0:
                        score += count * 1.0
                
                if score > 0:
                    chunk_meta = {**metadata, "paper_id": paper_id, "chunk_index": i}
                    all_candidates.append({
                        "score": score,
                        "content": chunk,
                        "metadata": chunk_meta
                    })

        # 依分數排序，回傳前 n_results 個結果
        all_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        output = []
        for cand in all_candidates[:n_results]:
            output.append({
                "content": cand["content"],
                "metadata": cand["metadata"]
            })
        return output

    @staticmethod
    def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
        chunks, start = [], 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start += size - overlap
        return chunks

