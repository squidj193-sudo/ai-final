"""
AI 研究助理 Agent — Agent Core
主協調器：解讀使用者意圖並分派至對應的技能
"""
import os
import asyncio
import json
import re
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

INTENT_PROMPT = """分析以下使用者訊息，判斷其意圖類型。
意圖類型選項說明：
- "set_direction"：當使用者說明自己的研究領域、想做的題目、設定或更改研究方向時（例如：「我想研究鈣鈦礦太陽能電池」、「我的題目是機器學習在醫學的應用」等）。
- "search"：當使用者明確要求搜尋或查找文獻時。
- "analyze"：當使用者要求分析或摘要某篇特定論文或主題時。
- "matrix"：當使用者要求生成文獻比較矩陣或比較表格時。
- "direction"：當使用者要求針對目前的文獻提出具體的研究方向或題目建議時。
- "chat"：一般的對話、問候或無特定學術分析意圖時。

訊息：{message}

請以繁體中文處理，只回傳以下 JSON 格式，不要包含任何額外文字或 Markdown 區塊：
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

    async def _generate_suggestions(self, intent: str, content: str, role_context: str, user_message: str) -> list[str]:
        """基於目前產出的內容與上下文，生成 3 個相關的建議追問問題"""
        prompt = f"""你是一位學術研究助手。請針對目前的對話與產出結果，為使用者生成 3 個可能想要點選的後續追問問題（例如：要求深入解釋、延伸搜尋、分析限制等）。

研究方向背景：{role_context or "未設定"}
目前使用者意圖：{intent}
使用者輸入：{user_message}
助理回覆摘要或內容：
{content[:1000]}

請只回傳一個包含 3 個字串元素之 JSON 陣列，例如 ["問題 1", "問題 2", "問題 3"]。不要包含任何額外文字、引導說明或 Markdown 區塊。"""
        try:
            response = await asyncio.to_thread(
                self._intent_model.generate_content,
                prompt
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:-1])
            suggestions = json.loads(raw)
            if isinstance(suggestions, list) and len(suggestions) > 0:
                return [str(s) for s in suggestions[:3]]
        except Exception:
            pass

        # 後備建議
        if intent == "search":
            return ["請幫我分析第一篇論文的摘要", "幫我使用這些論文生成比較矩陣", "搜尋其他年份的相關文獻"]
        elif intent == "analyze":
            return ["這篇論文有什麼具體的研究限制？", "它使用了哪些研究方法？", "基於這篇論文，有什麼推薦的研究方向？"]
        elif intent == "matrix":
            return ["請基於此比較矩陣，分析目前的研究缺口", "針對這些研究限制提出一些未來改善建議", "生成可行的研究課題與方向建議"]
        elif intent == "direction":
            return ["請為第一個研究方向設計具體的實驗方法", "哪一個方向以目前技術來說最容易實現？", "幫我搜尋這些方向的前導研究論文"]
        elif intent == "set_direction":
            return ["幫我對剛剛自動搜尋到的論文進行詳細分析", "在此研究方向下，目前最熱門的子題是什麼？", "生成這個方向的文獻比較矩陣"]
        else:
            return ["你能推薦這個領域的經典論文嗎？", "這項技術目前的主要應用場景是什麼？", "這個研究大方向下有哪些關鍵的技術瓶頸？"]

    async def _translate_query_to_english(self, query: str) -> str:
        """將中文搜尋詞翻譯/轉換成適合學術搜尋的英文關鍵字"""
        if not query or not query.strip():
            return ""
        # 如果已經全是英文/數字/常見標點符號，就不需要翻譯
        if re.match(r'^[a-zA-Z0-9\s\-_,\.\'\(\)]+$', query):
            return query.strip()

        prompt = f"""你是一個學術論文檢索助手。請將以下中文學術關鍵字或句子翻譯並優化成適合在英文論文數據庫（如 Semantic Scholar）檢索的英文關鍵字（通常是 2-5 個單字組成的片語）。
請只返回翻譯優化後的英文關鍵字，不要有任何標點符號、額外說明、引號或 Markdown 格式。

中文關鍵字：{query}
英文關鍵字："""
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
            translated = response.text.strip()
            # 移除常見的包裝引號
            translated = translated.strip('"\'`')
            return translated if translated else query
        except Exception:
            return query

    async def chat(self, session_id: str, message: str) -> dict:
        """主要對話入口，回傳結構化回應"""
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        intent_data = await self.detect_intent(message)
        intent = intent_data.get("intent", "chat")
        query = intent_data.get("query", message)

        if intent == "search":
            translated_query = await self._translate_query_to_english(query)
            translated_context = await self._translate_query_to_english(role_context) if role_context else ""
            papers = await self.search_skill.search(translated_query, context=translated_context)
            result_text = f"已找到 {len(papers)} 篇相關論文：\n\n"
            for p in papers:
                authors = "、".join(p.authors[:3]) + ("..." if len(p.authors) > 3 else "")
                result_text += f"📄 **{p.title}**\n"
                result_text += f"   - 作者：{authors}｜年份：{p.year or '未知'}\n"
                if p.abstract:
                    result_text += f"   - 摘要：{p.abstract[:150]}...\n"
                result_text += "\n"
            
            suggestions = await self._generate_suggestions(intent, result_text, role_context, message)
            return {"type": "search", "content": result_text, "papers": [p.model_dump() for p in papers], "suggestions": suggestions}

        elif intent == "analyze":
            import uuid
            translated_query = await self._translate_query_to_english(query)
            translated_context = await self._translate_query_to_english(role_context) if role_context else ""
            papers = await self.search_skill.search(translated_query, context=translated_context, limit=1)
            if not papers:
                return {"type": "chat", "content": f"找不到與「{query}」相關的論文可供分析。"}
            
            p = papers[0]
            content = p.abstract or "無摘要"
            paper_id = p.paper_id or str(uuid.uuid4())[:8]
            
            summary = await self.analysis_skill.summarize(
                paper_id=paper_id,
                title=p.title,
                authors=p.authors,
                year=p.year,
                content=content,
            )
            
            if session_id not in self._summaries:
                self._summaries[session_id] = []
            self._summaries[session_id].append(summary)
            
            result_text = f"✅ 已為您分析論文：**{p.title}**\n\n"
            result_text += f"**研究目的：** {summary.research_goal}\n\n"
            result_text += f"**主要發現：** {summary.main_findings}\n\n"
            result_text += "*(摘要已自動存入「論文摘要」區)*"
            
            suggestions = await self._generate_suggestions(intent, result_text, role_context, message)
            return {"type": "analyze", "content": result_text, "suggestions": suggestions}

        elif intent == "matrix":
            summaries = self._summaries.get(session_id, [])
            if len(summaries) < 2:
                return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
            matrix = await self.matrix_skill.build_matrix(summaries)
            self._matrix_cache[session_id] = matrix
            
            suggestions = await self._generate_suggestions(intent, matrix, role_context, message)
            return {"type": "matrix", "content": matrix, "suggestions": suggestions}

        elif intent == "direction":
            matrix = self._matrix_cache.get(session_id)
            if not matrix:
                return {"type": "chat", "content": "請先生成文獻比較矩陣，再要求分析研究方向。"}
            report = await self.direction_skill.analyze(matrix, role_context=role_context)
            
            suggestions = await self._generate_suggestions(intent, report, role_context, message)
            return {"type": "direction", "content": report, "suggestions": suggestions}

        elif intent == "set_direction":
            import uuid
            # 1. 提取大中小方向
            extract_prompt = f"""請從以下使用者訊息中提取其研究範疇的大方向、中方向與小方向。
訊息：{message}

請以下列 JSON 格式回覆，只回傳 JSON，不要有其他文字：
{{
  "large_direction": "最上層領域，例如：生醫、半導體、光電、人工智慧、永續發展",
  "medium_direction": "中層次研究技術或子領域，例如：基因工程、第三代半導體、太陽能電池、深度學習、碳捕集",
  "small_direction": "具體研究主題或材料，例如：CRISPR 基因編輯、碳化矽元件、鈣鈦礦材料、物件偵測、直接空氣捕集"
}}
如果訊息中沒有提及某層次，請回傳空字串。"""
            
            response = await asyncio.to_thread(self._intent_model.generate_content, extract_prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:-1])
            
            try:
                extracted = json.loads(raw)
            except Exception:
                extracted = {}
                
            large = extracted.get("large_direction") or ""
            medium = extracted.get("medium_direction") or ""
            small = extracted.get("small_direction") or ""
            
            # 更新角色狀態
            self.state_skill.update_state(
                session_id,
                large_direction=large if large else None,
                medium_direction=medium if medium else None,
                small_direction=small if small else None
            )
            
            # 取得最新上下文並搜尋
            role_state = self.state_skill.get_state(session_id)
            role_context = role_state.get_search_context()
            
            # 自動搜尋論文
            search_query = query if query else (small or medium or large or message)
            translated_query = await self._translate_query_to_english(search_query)
            translated_context = await self._translate_query_to_english(role_context) if role_context else ""
            papers = await self.search_skill.search(translated_query, context=translated_context, limit=2)
            
            result_text = f"🎯 **已為您設定並儲存研究方向：**\n"
            if large: result_text += f"- **大方向**：{large}\n"
            if medium: result_text += f"- **中方向**：{medium}\n"
            if small: result_text += f"- **小方向**：{small}\n"
            
            result_text += f"\n🔍 **已自動為您檢索並分析相關論文：**\n\n"
            
            if papers:
                for idx, p in enumerate(papers):
                    content = p.abstract or "無摘要"
                    paper_id = p.paper_id or str(uuid.uuid4())[:8]
                    
                    # 自動為這幾篇論文生成摘要
                    summary = await self.analysis_skill.summarize(
                        paper_id=paper_id,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        content=content
                    )
                    
                    if session_id not in self._summaries:
                        self._summaries[session_id] = []
                    self._summaries[session_id].append(summary)
                    
                    authors = "、".join(p.authors[:2]) + ("..." if len(p.authors) > 2 else "")
                    result_text += f"{idx+1}. 📄 **{p.title}** ({p.year or '未知'})\n"
                    result_text += f"   - 作者：{authors}\n"
                    result_text += f"   - **研究目的**：{summary.research_goal}\n"
                    result_text += f"   - **主要發現**：{summary.main_findings}\n\n"
                result_text += "*(以上論文摘要已自動存入「論文摘要」記錄頁中，您可以切換分頁查看)*"
            else:
                result_text += "（未尋找到相關論文）\n"
            
            suggestions = await self._generate_suggestions(intent, result_text, role_context, message)
            return {
                "type": "analyze",
                "content": result_text,
                "papers": [p.model_dump() for p in papers],
                "suggestions": suggestions
            }

        else:
            # 一般對話
            sys_prompt = SYSTEM_PROMPT.format(role_context=role_context or "尚未設定")
            history = self._chat_sessions.get(session_id, [])
            history.append({"role": "user", "parts": [message]})
            
            chat_model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                system_instruction=sys_prompt
            )
            response = await asyncio.to_thread(
                chat_model.generate_content,
                history,
            )
            reply = response.text
            history.append({"role": "model", "parts": [reply]})
            self._chat_sessions[session_id] = history[-20:]  # 保留最近 20 則
            
            suggestions = await self._generate_suggestions(intent, reply, role_context, message)
            return {"type": "chat", "content": reply, "suggestions": suggestions}

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
