"""
AI 研究助理 Agent — RAG 工具
整合 MarkItDown 與 ChromaDB 建立向量知識庫
"""
import os
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai

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


from chromadb.api.types import Documents, Embeddings, EmbeddingFunction

class GeminiEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        self.api_key = api_key
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        import google.generativeai as genai
        if self.api_key:
            genai.configure(api_key=self.api_key)
        embeddings_list = []
        for text in input:
            embedding_result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            embeddings_list.append(embedding_result["embedding"])
        return embeddings_list


# ─── ChromaDB 向量儲存 ────────────────────────────────────────────────
class CustomGeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        import google.generativeai as genai
        res = genai.embed_content(
            model=self.model_name,
            content=input,
            task_type="retrieval_document"
        )
        return res["embedding"]

class RAGStore:
    """管理論文向量索引與語意檢索"""

    COLLECTION_NAME = "papers"

    def __init__(self, db_path: str = "./data/chroma"):
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=db_path)
        from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
        import google.generativeai as genai

        class CustomGoogleEmbeddingFunction(EmbeddingFunction):
            def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
                genai.configure(api_key=api_key)
                self.model_name = model_name

            def __call__(self, input: Documents) -> Embeddings:
                result = genai.embed_content(
                    model=self.model_name,
                    content=input,
                    task_type="retrieval_document"
                )
                return result['embedding']

        api_key = os.getenv("GEMINI_API_KEY", "")
        ef = CustomGoogleEmbeddingFunction(api_key=api_key)
        
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME, embedding_function=ef
        )

    def add_document(
        self,
        paper_id: str,
        content: str,
        metadata: Optional[dict] = None,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> int:
        """將文件切分後存入向量庫，回傳切分數量"""
        chunks = self._chunk_text(content, chunk_size, overlap)
        ids = [f"{paper_id}_chunk_{i}" for i in range(len(chunks))]
        metas = [{**(metadata or {}), "paper_id": paper_id, "chunk_index": i} for i in range(len(chunks))]
        self._collection.add(documents=chunks, ids=ids, metadatas=metas)
        return len(chunks)

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """語意搜尋，回傳相關段落清單"""
        results = self._collection.query(query_texts=[query_text], n_results=n_results)
        output = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            output.append({"content": doc, "metadata": meta})
        return output

    @staticmethod
    def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
        chunks, start = [], 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start += size - overlap
        return chunks
