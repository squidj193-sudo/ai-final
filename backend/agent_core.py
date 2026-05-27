"""
AI 研究助理 Agent — Agent Core
主協調器：解讀使用者意圖並分派至對應的技能
"""
import os
import asyncio
import json
import google.generativeai as genai

from skills.state_skill import StateSkill, RoleState
from skills.search_skill import SearchSkill
from skills.analysis_skill import AnalysisSkill, PaperSummary
from skills.matrix_skill import MatrixSkill
from skills.direction_skill import DirectionSkill
from tools.rag import RAGStore, parse_pdf_to_markdown


SYSTEM_PROMPT = """你是一位 AI 研究助理 Agent，專門協助學術研究人員進行文獻探索與分析。

你的能力包括：
1. 根據關鍵字搜尋學術論文
2. 分析上傳的論文並生成結構化摘要
3. 建立多篇論文的比較矩陣
4. 根據文獻分析提出可行的研究方向

使用者的研究方向：{role_context}

請永遠使用繁體中文回覆。當使用者的意圖符合你的能力時，請明確告知你正在執行哪個步驟。"""

INTENT_PROMPT = """分析以下使用者訊息，判斷其意圖類型，回傳以下其中一個 JSON 值：

訊息：{message}

回傳格式（只回傳 JSON，不要其他文字）：
{{
  "intent": "search" | "analyze" | "matrix" | "direction" | "set_direction" | "chat",
  "query": "提取的關鍵字或主題（若有）"
}}"""


class AgentCore:
    """Agent Core：協調所有技能的主協調器"""

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._chat_model = genai.GenerativeModel(self.MODEL_NAME)
        self._intent_model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=256),
        )

        self.state_skill = StateSkill()
        self.search_skill = SearchSkill(api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
        self.analysis_skill = AnalysisSkill()
        self.matrix_skill = MatrixSkill()
        self.direction_skill = DirectionSkill()
        self.rag_store = RAGStore(db_path=os.getenv("CHROMA_DB_PATH", "./data/chroma"))

        # 儲存各 session 的摘要快取
        self._summaries: dict[str, list[PaperSummary]] = {}
        self._matrix_cache: dict[str, str] = {}
        self._chat_sessions: dict[str, list] = {}

    async def detect_intent(self, message: str) -> dict:
        prompt = INTENT_PROMPT.format(message=message)
        response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        try:
            return json.loads(raw)
        except Exception:
            return {"intent": "chat", "query": message}

    async def chat(self, session_id: str, message: str) -> dict:
        """主要對話入口，回傳結構化回應"""
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        intent_data = await self.detect_intent(message)
        intent = intent_data.get("intent", "chat")
        query = intent_data.get("query", message)

        if intent == "search":
            papers = await self.search_skill.search(query, context=role_context)
            result_text = f"已找到 {len(papers)} 篇相關論文：\n\n"
            for p in papers:
                authors = "、".join(p.authors[:3]) + ("..." if len(p.authors) > 3 else "")
                result_text += f"📄 **{p.title}**\n"
                result_text += f"   - 作者：{authors}｜年份：{p.year or '未知'}\n"
                if p.abstract:
                    result_text += f"   - 摘要：{p.abstract[:150]}...\n"
                result_text += "\n"
            return {"type": "search", "content": result_text, "papers": [p.model_dump() for p in papers]}

        elif intent == "matrix":
            summaries = self._summaries.get(session_id, [])
            if len(summaries) < 2:
                return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
            matrix = await self.matrix_skill.build_matrix(summaries)
            self._matrix_cache[session_id] = matrix
            return {"type": "matrix", "content": matrix}

        elif intent == "direction":
            matrix = self._matrix_cache.get(session_id)
            if not matrix:
                return {"type": "chat", "content": "請先生成文獻比較矩陣，再要求分析研究方向。"}
            report = await self.direction_skill.analyze(matrix, role_context=role_context)
            return {"type": "direction", "content": report}

        else:
            # 一般對話
            sys_prompt = SYSTEM_PROMPT.format(role_context=role_context or "尚未設定")
            history = self._chat_sessions.get(session_id, [])
            history.append({"role": "user", "parts": [message]})
            response = await asyncio.to_thread(
                self._chat_model.generate_content,
                [{"role": "user", "parts": [sys_prompt]}, *history],
            )
            reply = response.text
            history.append({"role": "model", "parts": [reply]})
            self._chat_sessions[session_id] = history[-20:]  # 保留最近 20 則
            return {"type": "chat", "content": reply}

    async def upload_paper(self, session_id: str, file_path: str, title: str, authors: list[str], year=None) -> dict:
        """處理上傳的 PDF 論文"""
        import uuid
        paper_id = str(uuid.uuid4())[:8]

        # 1. 解析 PDF
        content = parse_pdf_to_markdown(file_path)

        # 2. 存入 RAG
        chunks = self.rag_store.add_document(paper_id, content, {"title": title, "year": year})

        # 3. 生成摘要
        summary = await self.analysis_skill.summarize(paper_id, title, authors, year, content)

        # 4. 儲存摘要
        if session_id not in self._summaries:
            self._summaries[session_id] = []
        self._summaries[session_id].append(summary)

        return {
            "paper_id": paper_id,
            "chunks": chunks,
            "summary": summary.model_dump(),
            "message": f"論文「{title}」已解析完成，共切分為 {chunks} 個段落並存入知識庫。",
        }

    def get_summaries(self, session_id: str) -> list[dict]:
        return [s.model_dump() for s in self._summaries.get(session_id, [])]

    def update_role_state(self, session_id: str, **kwargs) -> dict:
        state = self.state_skill.update_state(session_id, **kwargs)
        return state.model_dump()
