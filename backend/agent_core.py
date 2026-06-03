"""
AI 研究助理 Agent — Agent Core
主協調器：解讀使用者意圖並分派至對應的技能
"""
import os
import asyncio
import json
import re
import google.generativeai as genai

from typing import Optional
from skills.state_skill import StateSkill, RoleState
from skills.search_skill import SearchSkill
from skills.analysis_skill import AnalysisSkill, PaperSummary
from skills.matrix_skill import MatrixSkill
from skills.direction_skill import DirectionSkill
from tools.rag import RAGStore, parse_pdf_to_markdown

import logging
logger = logging.getLogger("agent")


SYSTEM_PROMPT = """你是一位專注於【{role_context}】領域的學術研究助理 Agent，專門協助研究人員進行文獻探索、分析與學術討論。

你必須：
1. 將自己定位為一位在【{role_context}】領域有深厚學術背景的研究專家。
2. 在所有一般對話、問答及分析中，始終緊扣【{role_context}】這個研究主題，以該領域的專業視角提供深入、具體的建議，避免給出偏離主題或無關的泛泛回答。
3. 協助使用者進行以下學術工作：
   - 根據關鍵字搜尋與篩選相關學術論文
   - 分析論文並生成結構化摘要與研究限制
   - 建立多篇論文的比較矩陣
   - 根據文獻分析提出具體、可行且具學術價值的研究課題

請永遠使用繁體中文回覆。"""

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
}}"""# ─── Gemini 原生工具定義 ───────────────────────────────────────────────
def search_academic_papers(query: str) -> str:
    """
    搜尋與學術主題或關鍵字相關的論文，並自動分析與儲存論文摘要。

    Args:
        query: 搜尋關鍵字或學術主題。
    """
    return "已觸發學術搜尋"

def generate_comparison_matrix() -> str:
    """
    為當前已搜尋、已上傳或已儲存的所有論文生成對比矩陣與表格。
    """
    return "已觸發生成比較矩陣"

def analyze_research_direction() -> str:
    """
    基於當前已生成的文獻比較矩陣，分析研究缺口並給出具體可行的研究方向與題目建議。
    """
    return "已觸發分析研究方向"

def set_research_direction(large_direction: str, medium_direction: str = "", small_direction: str = "") -> str:
    """
    設定或更改使用者的學術研究大方向、中方向或小方向範疇。

    Args:
        large_direction: 最上層領域範疇，例如：生醫、半導體、光電、人工智慧、永續發展。
        medium_direction: 中層次研究技術或子領域，例如：基因工程、第三代半導體、太陽能電池、深度學習。
        small_direction: 具體研究主題或材料，例如：CRISPR 基因編輯、碳化矽元件、鈣鈦礦材料、物件偵測。
    """
    return "已觸發設定研究方向"


class AgentCore:
    """Agent Core：協調所有技能的主協調器"""

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._chat_model = genai.GenerativeModel(
            self.MODEL_NAME,
            tools=[search_academic_papers, generate_comparison_matrix, analyze_research_direction, set_research_direction]
        )
        self._intent_model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=256),
        )

        self.state_skill = StateSkill()
        self.search_skill = SearchSkill(api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
        self.analysis_skill = AnalysisSkill()
        self.matrix_skill = MatrixSkill()
        self.direction_skill = DirectionSkill()
        self.rag_store = RAGStore(db_path=os.getenv("PAPERS_DB_PATH", "./data/papers"))

        # 儲存各 session 的摘要快取
        self._summaries: dict[str, list[PaperSummary]] = {}
        self._matrix_cache: dict[str, str] = {}
        self._direction_cache: dict[str, str] = {}
        self._chat_sessions: dict[str, list] = {}
        self._conversations: list[dict] = []
        self._chat_history: dict[str, list[dict]] = {}
        self._load_session_data()

    def _load_session_data(self):
        from pathlib import Path
        path = Path("./data/session_data.json")
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for k, v in data.get("summaries", {}).items():
                    self._summaries[k] = [PaperSummary(**p) for p in v]
                self._matrix_cache = data.get("matrix_cache", {})
                self._direction_cache = data.get("direction_cache", {})
                self._conversations = data.get("conversations", [])
                self._chat_history = data.get("chat_history", {})
                
                # 同步重建 _chat_sessions 作為 LLM 對話快取
                for sid, history in self._chat_history.items():
                    gemini_history = []
                    for msg in history:
                        role = msg.get("role")
                        content = msg.get("content")
                        if role in ("user", "assistant") and content:
                            gemini_role = "user" if role == "user" else "model"
                            gemini_history.append({"role": gemini_role, "parts": [content]})
                    self._chat_sessions[sid] = gemini_history[-20:]
            except Exception as e:
                logger.warning(f"Failed to load session data: {e}")

    def _save_session_data(self):
        from pathlib import Path
        path = Path("./data/session_data.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "summaries": {k: [p.model_dump() for p in v] for k, v in self._summaries.items()},
                "matrix_cache": self._matrix_cache,
                "direction_cache": self._direction_cache,
                "conversations": self._conversations,
                "chat_history": self._chat_history
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save session data: {e}")

    async def detect_intent(self, message: str) -> dict:
        prompt = INTENT_PROMPT.format(message=message)
        logger.info(f"Detecting intent for message: {message[:50]}...")
        response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        try:
            res = json.loads(raw)
            logger.info(f"Detected intent: {res.get('intent')} | Query: {res.get('query')}")
            return res
        except Exception as e:
            logger.warning(f"Failed to parse intent JSON, raw: {raw}. Error: {str(e)}")
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
        """包裝主要對話，將使用者訊息與助理回覆儲存至後端歷史紀錄"""
        import time
        if session_id not in self._chat_history:
            self._chat_history[session_id] = []
        
        user_msg = {
            "id": int(time.time() * 1000),
            "role": "user",
            "content": message,
            "type": "chat"
        }
        # 避免重複寫入最後一筆
        if not self._chat_history[session_id] or self._chat_history[session_id][-1].get("content") != message:
            self._chat_history[session_id].append(user_msg)
            if session_id not in self._chat_sessions:
                self._chat_sessions[session_id] = []
            self._chat_sessions[session_id].append({"role": "user", "parts": [message]})
            self._chat_sessions[session_id] = self._chat_sessions[session_id][-20:]
        
        # 呼叫原始對話邏輯
        res = await self._chat_internal(session_id, message)
        
        # 記錄助理回覆
        assistant_msg = {
            "id": int(time.time() * 1000) + 1,
            "role": "assistant",
            "content": res.get("content"),
            "type": res.get("type", "chat"),
            "suggestions": res.get("suggestions"),
            "papers": res.get("papers")
        }
        self._chat_history[session_id].append(assistant_msg)
        
        # 同步更新 self._chat_sessions 供 Gemini 使用
        if res.get("type") == "chat" and res.get("content"):
            if session_id not in self._chat_sessions:
                self._chat_sessions[session_id] = []
            self._chat_sessions[session_id].append({"role": "model", "parts": [res.get("content")]})
            self._chat_sessions[session_id] = self._chat_sessions[session_id][-20:]
            
        self._save_session_data()
        return res

    async def _chat_internal(self, session_id: str, message: str) -> dict:
        """主要對話內部實作邏輯"""
        import google.api_core.exceptions as g_exceptions
        logger.info(f"Chat request - Session ID: {session_id} | Message: {message[:100]}")
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        full_context = role_state.get_full_hierarchy_desc()
        
        try:
            # 優先檢測使用者輸入是否包含 URL 或 DOI
            import re
            # 排除 URL 中的空格（例如 https : // 轉為 https://）
            cleaned_message = re.sub(r'(https?)\s*:\s*/\s*/', r'\1://', message)
            
            url_match = re.search(r'(https?://[^\s]+)', cleaned_message)
            doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', cleaned_message)
            
            is_url_or_doi = False
            target_query = ""
            if doi_match:
                is_url_or_doi = True
                target_query = doi_match.group(1)
            elif url_match:
                is_url_or_doi = True
                target_query = url_match.group(1)
            
            # 若為 URL/DOI，直接進行特定文章抓取與摘要處理
            if is_url_or_doi:
                logger.info(f"Direct URL/DOI detected: {target_query}")
                paper = await self.search_skill.fetch_paper_by_id_or_url(target_query)
                if paper:
                    import uuid
                    paper_id = paper.paper_id or str(uuid.uuid4())[:8]
                    content = paper.abstract or "無摘要"
                    
                    # 使用 analysis_skill.summarize 生成摘要
                    summary = await self.analysis_skill.summarize(
                        paper_id=paper_id,
                        title=paper.title,
                        authors=paper.authors,
                        year=paper.year,
                        content=content,
                    )
                    
                    if session_id not in self._summaries:
                        self._summaries[session_id] = []
                    # 避免重複加入
                    if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                        self._summaries[session_id].append(summary)
                    self._save_session_data()
                    
                    # 同時將資訊寫入 RAG
                    try:
                        self.rag_store.add_document(paper_id, content, {"title": summary.title, "year": summary.year})
                    except Exception as ree:
                        logger.warning(f"Failed to add to RAG: {ree}")
                    
                    result_text = f"✅ 已成功抓取並分析您提供的論文：**{summary.title}**\n\n"
                    result_text += f"**研究目的：** {summary.research_goal}\n\n"
                    result_text += f"**主要發現：** {summary.main_findings}\n\n"
                    result_text += f"**研究限制：** {summary.limitations}\n\n"
                    result_text += "*(此論文結構化摘要已自動儲存至「論文摘要」分頁中)*"
                    
                    suggestions = await self._generate_suggestions("analyze", result_text, role_context, message)
                    return {"type": "analyze", "content": result_text, "suggestions": suggestions}
                else:
                    # 備用方案：如果無法從 Semantic Scholar 取得學術資料，嘗試直接爬取網頁內容進行摘要
                    if target_query.startswith("http://") or target_query.startswith("https://"):
                        try:
                            logger.info(f"Semantic Scholar lookup failed. Crawling URL directly: {target_query}")
                            import httpx
                            # 爬取網頁內容
                            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                                resp = await client.get(target_query, headers={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                                })
                                if resp.status_code == 200:
                                    html_content = resp.text
                                    # 簡單清理 HTML 標籤
                                    import re
                                    text_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
                                    text_content = re.sub(r'<style.*?</style>', '', text_content, flags=re.DOTALL)
                                    text_content = re.sub(r'<.*?>', '', text_content, flags=re.DOTALL)
                                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                                    
                                    # 提取網頁標題
                                    title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
                                    page_title = title_match.group(1).strip() if title_match else "網路文章"
                                    
                                    # 生成摘要
                                    import uuid
                                    paper_id = str(uuid.uuid4())[:8]
                                    summary = await self.analysis_skill.summarize(
                                        paper_id=paper_id,
                                        title=page_title,
                                        authors=["網路作者"],
                                        year=None,
                                        content=text_content[:8000],
                                    )
                                    
                                    if session_id not in self._summaries:
                                        self._summaries[session_id] = []
                                    if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                                        self._summaries[session_id].append(summary)
                                    self._save_session_data()
                                    
                                    result_text = f"✅ 已成功擷取並分析網頁文章：**{summary.title}**\n\n"
                                    result_text += f"**研究目的：** {summary.research_goal}\n\n"
                                    result_text += f"**主要發現：** {summary.main_findings}\n\n"
                                    result_text += f"**研究限制：** {summary.limitations}\n\n"
                                    result_text += "*(此文章結構化摘要已自動儲存至「論文摘要」分頁中)*"
                                    
                                    suggestions = await self._generate_suggestions("analyze", result_text, role_context, message)
                                    return {"type": "analyze", "content": result_text, "suggestions": suggestions}
                        except Exception as ce:
                            logger.warning(f"Failed to crawl URL fallback '{target_query}': {ce}")
                    
                    logger.warning(f"Could not fetch paper details by URL/DOI directly. Returning error message.")
                    if target_query.startswith("http://") or target_query.startswith("https://"):
                        error_desc = f"⚠️ 無法讀取該網頁或論文內容（可能因為該網站有防爬蟲機制，如 Medium / Cloudflare，或不屬於公開學術資料庫格式）。\n\n**建議您：**\n1. 直接使用 **「📎 上傳論文」** 功能上傳 PDF 檔案。\n2. 將論文摘要或內文複製並直接貼上到對話框中，讓我為您進行分析。"
                        return {"type": "error", "content": error_desc, "suggestions": ["直接搜尋相關文獻", "如何上傳 PDF 論文"]}
                    else:
                        error_desc = f"⚠️ 無法透過 DOI `{target_query}` 獲取論文資料（Semantic Scholar 資料庫中可能尚未收錄此 DOI）。\n\n**建議您：**\n1. 使用 **「📎 上傳論文」** 功能上傳 PDF 檔案。\n2. 直接輸入關鍵字讓我為您搜尋相似文獻。"
                        return {"type": "error", "content": error_desc, "suggestions": ["直接搜尋相關文獻", "如何上傳 PDF 論文"]}

            # 用 chat_model (配備 Tools) 進行對話，讓 Gemini 判斷是否需要 Function Call
            sys_prompt = SYSTEM_PROMPT.format(role_context=full_context)
            chat_model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                system_instruction=sys_prompt,
                tools=[search_academic_papers, generate_comparison_matrix, analyze_research_direction, set_research_direction]
            )
            
            history = self._chat_sessions.get(session_id, [])
            temp_history = list(history)
            temp_history.append({"role": "user", "parts": [message]})
            
            response = await asyncio.to_thread(
                chat_model.generate_content,
                temp_history,
            )
            
            # 檢查是否有 Function Call
            function_calls = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
            
            if function_calls:
                call = function_calls[0]
                name = call.name
                args = call.args
                logger.info(f"Gemini native Function Call triggered: {name} with args {args}")
                
                if name == "search_academic_papers":
                    query = args.get("query") or message
                    translated_query = await self._translate_query_to_english(query)
                    translated_context = await self._translate_query_to_english(role_context) if role_context else ""
                    papers = await self.search_skill.search(translated_query, context=translated_context)
                    import uuid
                    summary_tasks = [self.analysis_skill.summarize(paper_id=p.paper_id or str(uuid.uuid4())[:8], title=p.title, authors=p.authors, year=p.year, content=p.abstract or "無摘要") for p in papers]
                    if summary_tasks:
                        try:
                            summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)
                            if session_id not in self._summaries:
                                self._summaries[session_id] = []
                            for s in summaries:
                                if not isinstance(s, Exception) and not any(x.title.lower() == s.title.lower() for x in self._summaries[session_id]):
                                    self._summaries[session_id].append(s)
                            self._save_session_data()
                        except Exception as e:
                            logger.warning(f"Auto-summarizing failed: {e}")
                    result_text = f"已找到 {len(papers)} 篇相關論文：\n\n"
                    for p in papers:
                        authors = "、".join(p.authors[:3]) + ("..." if len(p.authors) > 3 else "")
                        result_text += f"📄 **{p.title}**\n"
                        result_text += f"   - 作者：{authors}｜年份：{p.year or '未知'}\n"
                        if p.abstract:
                            result_text += f"   - 摘要：{p.abstract[:150]}...\n"
                        result_text += "\n"
                    result_text += "*(以上搜尋到的論文已自動分析並存入「論文摘要」記錄頁中，您可以切換分頁查看)*"
                    
                    suggestions = await self._generate_suggestions("search", result_text, role_context, message)
                    return {"type": "search", "content": result_text, "papers": [p.model_dump() for p in papers], "suggestions": suggestions}
                
                elif name == "generate_comparison_matrix":
                    summaries = []
                    seen = set()
                    for sums in self._summaries.values():
                        for s in sums:
                            if s.title.lower() not in seen:
                                seen.add(s.title.lower())
                                summaries.append(s)
                    if len(summaries) < 2:
                        return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
                    matrix = await self.matrix_skill.build_matrix(summaries, role_context=full_context)
                    self._matrix_cache[session_id] = matrix
                    self._save_session_data()
                    
                    suggestions = await self._generate_suggestions("matrix", matrix, role_context, message)
                    return {"type": "matrix", "content": matrix, "suggestions": suggestions}
                
                elif name == "analyze_research_direction":
                    matrix = self._matrix_cache.get(session_id)
                    if not matrix:
                        return {"type": "chat", "content": "請先生成文獻比較矩陣，再要求分析研究方向。"}
                    report = await self.direction_skill.analyze(matrix, role_context=full_context)
                    self._direction_cache[session_id] = report
                    self._save_session_data()
                    
                    suggestions = await self._generate_suggestions("direction", report, role_context, message)
                    return {"type": "direction", "content": report, "suggestions": suggestions}
                
                elif name == "set_research_direction":
                    large = args.get("large_direction") or ""
                    medium = args.get("medium_direction") or ""
                    small = args.get("small_direction") or ""
                    
                    self.state_skill.update_state(
                        session_id,
                        large_direction=large if large else None,
                        medium_direction=medium if medium else None,
                        small_direction=small if small else None
                    )
                    
                    role_state = self.state_skill.get_state(session_id)
                    role_context = role_state.get_search_context()
                    full_context = role_state.get_full_hierarchy_desc()
                    
                    search_query = small or medium or large or message
                    translated_query = await self._translate_query_to_english(search_query)
                    translated_context = await self._translate_query_to_english(role_context) if role_context else ""
                    papers = await self.search_skill.search(translated_query, context=translated_context, limit=2)
                    
                    result_text = f"🎯 **已為您設定並儲存研究方向：**\n"
                    if large: result_text += f"- **大方向**：{large}\n"
                    if medium: result_text += f"- **中方向**：{medium}\n"
                    if small: result_text += f"- **小方向**：{small}\n"
                    
                    result_text += f"\n🔍 **已自動為您檢索並分析相關論文：**\n\n"
                    
                    if papers:
                        import uuid
                        for idx, p in enumerate(papers):
                            content = p.abstract or "無摘要"
                            paper_id = p.paper_id or str(uuid.uuid4())[:8]
                            summary = await self.analysis_skill.summarize(
                                paper_id=paper_id,
                                title=p.title,
                                authors=p.authors,
                                year=p.year,
                                content=content
                            )
                            if session_id not in self._summaries:
                                self._summaries[session_id] = []
                            if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                                self._summaries[session_id].append(summary)
                        self._save_session_data()
                role_context = role_state.get_search_context()
                full_context = role_state.get_full_hierarchy_desc()
                
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
                        # 避免重複加入
                        if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                            self._summaries[session_id].append(summary)
                    
                    self._save_session_data()
                    result_text += "*(以上論文摘要已自動存入「論文摘要」記錄頁中，您可以切換分頁查看)*"
                else:
                    result_text += "（未尋找到相關論文）\n"
                
                suggestions = await self._generate_suggestions("set_direction", result_text, role_context, message)
                return {
                    "type": "analyze",
                    "content": result_text,
                    "papers": [p.model_dump() for p in papers],
                    "suggestions": suggestions
                }

            else:
                # 一般對話
                sys_prompt = SYSTEM_PROMPT.format(role_context=full_context)
                
                # 自動調用 RAG 檢索
                try:
                    rag_results = self.rag_store.query(message, n_results=3)
                    if rag_results:
                        context_str = "\n\n".join([
                            f"來源文獻【{r['metadata'].get('title', '未知')}】:\n{r['content']}" 
                            for r in rag_results
                        ])
                        sys_prompt += f"\n\n此外，以下是從你已分析的論文中檢索到的相關內容，請優先參考這些內容來回答使用者的提問，並在回答中註明參考來源：\n{context_str}"
                        logger.info(f"RAG context successfully injected for chat query. Found {len(rag_results)} chunks.")
                except Exception as ree:
                    logger.warning(f"RAG query failed inside chat fallback: {ree}")

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
                
                suggestions = await self._generate_suggestions("chat", reply, role_context, message)
                return {"type": "chat", "content": reply, "suggestions": suggestions}

        except g_exceptions.Forbidden as e:
            error_msg = "⚠️ API 金鑰連線被拒絕 (403 Forbidden)。這通常是因為您的 API Key 已被系統判定洩漏或失效。請至 `backend/.env` 檔案更新您可用的 `GEMINI_API_KEY`。"
            return {"type": "error", "content": error_msg, "suggestions": ["如何設定金鑰", "測試連線狀態"]}
        except g_exceptions.GoogleAPICallError as e:
            error_msg = f"⚠️ Gemini API 服務呼叫失敗：{str(e)}。請確認您的網路連線與 `backend/.env` 中的金鑰配置。"
            return {"type": "error", "content": error_msg, "suggestions": ["檢查金鑰設定", "重試對話"]}
        except Exception as e:
            error_msg = f"⚠️ 發生未知錯誤：{str(e)}"
            return {"type": "error", "content": error_msg, "suggestions": ["重試對話"]}

    async def upload_paper(self, session_id: str, file_path: str, title: Optional[str] = None, authors: Optional[list[str]] = None, year: Optional[int] = None) -> dict:
        """處理上傳的 PDF 論文"""
        import uuid
        import google.api_core.exceptions as g_exceptions
        paper_id = str(uuid.uuid4())[:8]

        # 1. 解析 PDF
        try:
            content = parse_pdf_to_markdown(file_path)
        except Exception as e:
            if "MissingDependencyException" in str(e) or "dependencies needed" in str(e):
                raise RuntimeError("PDF 解析失敗：系統缺少讀取 PDF 所需的選填依賴。請至後端終端機執行 `pip install markitdown[pdf]` 安裝相依套件。")
            raise RuntimeError(f"PDF 檔案轉換 Markdown 失敗：{str(e)}")

        try:
            # 2. 存入 RAG (預填)
            self.rag_store.add_document(paper_id, content, {"title": title or "未命名", "year": year})

            # 3. 生成摘要 (由 LLM 動態填補未提供的欄位)
            summary = await self.analysis_skill.summarize(paper_id, title, authors, year, content)

            # 更新 RAG 的 Metadata 為最精準的 AI 檢索值
            self.rag_store.add_document(paper_id, content, {"title": summary.title, "year": summary.year})

            # 4. 儲存摘要
            if session_id not in self._summaries:
                self._summaries[session_id] = []
            if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                self._summaries[session_id].append(summary)

            # 5. 記錄對話歷史
            import time
            if session_id not in self._chat_history:
                self._chat_history[session_id] = []
            
            user_msg_id = int(time.time() * 1000)
            displayName = title.strip() if (title and title.strip()) else os.path.basename(file_path)
            self._chat_history[session_id].append({
                "id": user_msg_id,
                "role": "user",
                "content": f"📎 上傳論文：{displayName}",
                "type": "chat"
            })
            
            assistant_msg_content = f"✅ 論文「{summary.title}」已解析完成，存入知識庫中。\n\n**摘要摘錄：**\n\n**研究目的：** {summary.research_goal}\n\n**主要發現：** {summary.main_findings}"
            self._chat_history[session_id].append({
                "id": user_msg_id + 1,
                "role": "assistant",
                "content": assistant_msg_content,
                "type": "analyze",
                "suggestions": ["生成比較矩陣", "分析研究方向"]
            })
            self._save_session_data()

            return {
                "paper_id": paper_id,
                "chunks": len(content) // 1200 + 1,
                "summary": summary.model_dump(),
                "message": f"論文「{summary.title}」已解析完成，存入知識庫中。",
            }
        except g_exceptions.Forbidden as e:
            raise RuntimeError("API 金鑰連線被拒絕 (403)。您的 API Key 已失效或被回報洩漏，請更換 `backend/.env` 中的 GEMINI_API_KEY。")
        except Exception as e:
            raise RuntimeError(f"論文分析/摘要生成失敗：{str(e)}")

    def get_summaries(self, session_id: str) -> list[dict]:
        # 回傳系統中所有 session 的論文摘要（去重且依年份排序）
        all_sums = []
        seen_titles = set()
        for sums in self._summaries.values():
            for s in sums:
                if s.title.lower() not in seen_titles:
                    seen_titles.add(s.title.lower())
                    all_sums.append(s.model_dump())
        all_sums.sort(key=lambda x: x.get("year") or 0, reverse=True)
        return all_sums

    def get_matrix(self, session_id: str) -> str:
        return self._matrix_cache.get(session_id, "")

    def set_matrix(self, session_id: str, matrix: str) -> None:
        self._matrix_cache[session_id] = matrix
        self._save_session_data()

    def get_direction(self, session_id: str) -> str:
        return self._direction_cache.get(session_id, "")

    def set_direction(self, session_id: str, direction: str) -> None:
        self._direction_cache[session_id] = direction
        self._save_session_data()

    def update_role_state(self, session_id: str, **kwargs) -> dict:
        state = self.state_skill.update_state(session_id, **kwargs)
        return state.model_dump()

    def delete_session(self, session_id: str) -> None:
        if session_id in self._summaries:
            del self._summaries[session_id]
        if session_id in self._matrix_cache:
            del self._matrix_cache[session_id]
        if session_id in self._direction_cache:
            del self._direction_cache[session_id]
        if session_id in self._chat_sessions:
            del self._chat_sessions[session_id]
        if session_id in self._chat_history:
            del self._chat_history[session_id]
        if session_id in self.state_skill._states:
            del self.state_skill._states[session_id]
        self._save_session_data()

    def get_conversations(self) -> list[dict]:
        return self._conversations

    def set_conversations(self, conversations: list[dict]) -> None:
        self._conversations = conversations
        self._save_session_data()

    def get_chat_history(self, session_id: str) -> list[dict]:
        return self._chat_history.get(session_id, [])

    def set_chat_history(self, session_id: str, history: list[dict]) -> None:
        self._chat_history[session_id] = history
        
        # 同步重建 _chat_sessions 供 Gemini 對話使用
        gemini_history = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                gemini_role = "user" if role == "user" else "model"
                gemini_history.append({"role": gemini_role, "parts": [content]})
        self._chat_sessions[session_id] = gemini_history[-20:]
        
        self._save_session_data()
