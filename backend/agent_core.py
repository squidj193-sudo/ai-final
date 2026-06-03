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
- "set_direction"：當使用者明確說明自己的研究領域、想研究的主題、設定或更改研究方向時（例如：「我想研究鈣鈦礦太陽能電池」、「我的題目是機器學習在醫學的應用」、「我在研究...」、「我的方向是...」等）。只要使用者陳述了研究主題，就應歸類為此類型，不需要等待更多確認。
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
        self.rag_store = RAGStore(db_path=os.getenv("PAPERS_DB_PATH", "./data/papers"))

        # 儲存各 session 的摘要快取
        self._summaries: dict[str, list[PaperSummary]] = {}
        self._matrix_cache: dict[str, str] = {}
        self._chat_sessions: dict[str, list] = {}

    async def detect_intent(self, message: str) -> dict:
        msg_lower = message.lower()
        
        # 1. 強制關鍵字規則路由到 Skill，以提升精確度並強制使用
        if any(k in msg_lower for k in ["大方向", "中方向", "小方向", "設定方向", "研究方向是", "研究領域是", "設定我的領域", "研究主題是", "設定主題"]):
            return {"intent": "set_direction", "query": message}
        
        if any(k in msg_lower for k in ["搜尋", "尋找", "查找", "檢索", "論文搜尋", "找論文", "搜尋文獻", "找文獻", "search", "find paper", "find papers"]):
            # 只清除動作詞，保留主題詞作為搜尋關鍵字
            clean_query = re.sub(r'^(請幫我|幫我|請)', '', message, flags=re.IGNORECASE).strip()
            clean_query = re.sub(r'^(搜尋|尋找|查找|檢索|找)', '', clean_query, flags=re.IGNORECASE).strip()
            clean_query = re.sub(r'(的論文|相關論文|文獻)$', '', clean_query, flags=re.IGNORECASE).strip()
            return {"intent": "search", "query": clean_query if clean_query else message}
            
        if any(k in msg_lower for k in ["分析", "摘要", "閱讀論文", "摘要論文", "論文分析", "這篇論文", "analyze", "summarize", "summary"]):
            clean_query = re.sub(r'(請幫我|幫我|分析|摘要|閱讀論文|摘要論文|論文分析|這篇論文|的摘要|的內容|analyze|summarize|summary|paper)', '', message, flags=re.IGNORECASE).strip()
            return {"intent": "analyze", "query": clean_query if clean_query else message}
            
        if any(k in msg_lower for k in ["比較矩陣", "生成矩陣", "矩陣", "比較表", "表格", "matrix", "compare"]):
            return {"intent": "matrix", "query": message}
            
        if any(k in msg_lower for k in ["研究建議", "題目建議", "方向建議", "研究缺口", "學術建議", "方向分析", "建議方向", "學術題目"]):
            return {"intent": "direction", "query": message}

        # 2. 使用 LLM 進行意圖判斷
        prompt = INTENT_PROMPT.format(message=message)
        response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        try:
            res = json.loads(raw)
            # 輔助判斷：非問候的長句子，預設偏向 search 意圖，強制調用學術檢索
            if res.get("intent") == "chat":
                if len(message) > 5 and not any(h in msg_lower for h in ["你好", "哈囉", "嗨", "hello", "hi", "早安"]):
                    res["intent"] = "search"
            return res
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

    async def _auto_extract_and_update_state(self, session_id: str, message: str, current_state) -> bool:
        """從對話中自動提取真實的研究方向名稱並更新角色狀態（嚴格：只取使用者訊息中出現的真實名詞）"""
        extract_prompt = f"""你的任務是從使用者訊息中，提取他提到的研究領域分類詞。

規則：
- 大方向 = 最上層學術領域，例如：光電、半導體、生醫、人工智慧、永續發展、材料科學
- 中方向 = 次一級子領域，例如：太陽能電池、深度學習、基因工程、碳捕集
- 小方向 = 最具體的研究主題，例如：鈣鈦礦材料、物件偵測、CRISPR
- 如果訊息中沒有提到某層級的詞，該欄位一定要回傳空字串 ""（不是說明文字）
- 只能提取訊息中真正出現的詞，不能自行推斷或補全

使用者訊息：{message}

請只回傳以下 JSON，禁止包含任何其他文字或說明：
{{"large_direction": "", "medium_direction": "", "small_direction": ""}}"""
        
        # 已知的說明文字前綴（LLM 有時會回傳這些而非真實值）
        INVALID_PATTERNS = ["提取的", "若無", "最上層", "中層次", "具體", "例如", "最上", "中層"]
        
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, extract_prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:-1])
            extracted = json.loads(raw)
            
            def clean_value(v):
                if not v or not isinstance(v, str):
                    return ""
                v = v.strip()
                # 若 LLM 回傳的是說明文字而非真實方向名稱，拒絕接受
                if any(p in v for p in INVALID_PATTERNS):
                    return ""
                # 若長度超過 20 字，可能是說明文字
                if len(v) > 20:
                    return ""
                return v
            
            large = clean_value(extracted.get("large_direction", ""))
            medium = clean_value(extracted.get("medium_direction", ""))
            small = clean_value(extracted.get("small_direction", ""))
            
            new_large = large if large else current_state.large_direction
            new_medium = medium if medium else current_state.medium_direction
            new_small = small if small else current_state.small_direction
            
            if new_large != current_state.large_direction or new_medium != current_state.medium_direction or new_small != current_state.small_direction:
                self.state_skill.update_state(
                    session_id,
                    large_direction=new_large if new_large else None,
                    medium_direction=new_medium if new_medium else None,
                    small_direction=new_small if new_small else None
                )
                return True
        except Exception as e:
            print(f"Auto state update failed: {e}")
        return False

    async def _translate_query_to_english(self, query: str) -> str:
        """從查詢中提取/翻譯出英文學術搜尋關鍵字（最終輸出必為 ASCII 英文）"""
        if not query or not query.strip():
            return ""
        query = query.strip()

        # ── Step 1: 直接從輸入中提取現有的英文單字（最可靠）──
        # 例如「近10年 Transformer 架構 CT Segmentation」→ 直接拿 Transformer CT Segmentation
        english_words = re.findall(r'[a-zA-Z][a-zA-Z0-9\-]*', query)
        # 過濾掉無意義的短英文字（長度 < 3，如介詞）
        STOPWORDS = {"the", "for", "and", "or", "in", "on", "at", "of", "to", "a", "an", "is", "are", "was"}
        english_words = [w for w in english_words if len(w) >= 3 and w.lower() not in STOPWORDS]

        # 如果英文詞已經足夠（3個以上），直接使用，不調用 LLM
        if len(english_words) >= 2:
            return " ".join(english_words[:5])

        # ── Step 2: 純中文查詢 → 用 LLM 翻譯，但嚴格驗證輸出 ──
        # 提取純中文部分
        chinese_part = re.sub(r'[a-zA-Z0-9\s\-_,\.\(\)\[\]（）「」\'"]+', ' ', query).strip()
        if not chinese_part:
            # 沒有中文，直接回傳已有英文詞
            return " ".join(english_words[:5]) if english_words else query[:50]

        prompt = f"Translate to English keywords (2-4 words, ASCII only, no explanation):\n{chinese_part[:100]}\nKeywords:"
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
            result = response.text.strip()
            # 只取第一行
            result = result.split("\n")[0].strip().strip('"\'`*#')
            # 嚴格驗證：結果必須全為 ASCII，否則放棄
            if result.isascii() and len(result) <= 80:
                # 合併翻譯結果與已有的英文詞
                translated_words = [w for w in result.split() if len(w) >= 2][:4]
                combined = (translated_words + english_words)[:5]
                if combined:
                    return " ".join(combined)
        except Exception:
            pass

        # ── 最終後備：若所有方法失敗，只用已提取的英文詞；若無，回傳 query 的 ASCII 部分 ──
        if english_words:
            return " ".join(english_words[:5])
        ascii_only = re.sub(r'[^\x00-\x7F]+', ' ', query).strip()
        words = ascii_only.split()[:5]
        return " ".join(words) if words else "academic research"

    async def chat(self, session_id: str, message: str) -> dict:
        """主要對話入口，回傳結構化回應"""
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        intent_data = await self.detect_intent(message)
        intent = intent_data.get("intent", "chat")
        query = intent_data.get("query", message)

        # 每次對話都自動嘗試提取方向以更新設定區
        state_updated = await self._auto_extract_and_update_state(session_id, message, role_state)
        if state_updated:
            role_state = self.state_skill.get_state(session_id)
            role_context = role_state.get_search_context()

        if intent == "search":
            import uuid
            translated_query = await self._translate_query_to_english(query)
            translated_context = await self._translate_query_to_english(role_context) if role_context else ""
            papers = await self.search_skill.search(translated_query, context=translated_context)
            
            result_text = f"🔍 已為您尋找到 {len(papers)} 篇相關論文，並自動載入至您的「比較矩陣」與「論文圖譜」中：\n\n"
            for idx, p in enumerate(papers):
                authors = "、".join(p.authors[:3]) + ("..." if len(p.authors) > 3 else "")
                result_text += f"{idx+1}. 📄 **{p.title}**\n"
                result_text += f"   - 作者：{authors}｜年份：{p.year or '未知'}\n"
                if p.abstract:
                    result_text += f"   - 摘要：{p.abstract[:150]}...\n"
                result_text += "\n"
                
                # 自動分析與儲存前 3 篇
                if idx < 3:
                    content = p.abstract or "無摘要"
                    paper_id = p.paper_id or str(uuid.uuid4())[:8]
                    try:
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
                        if not any(s.title == p.title for s in self._summaries[session_id]):
                            self._summaries[session_id].append(summary)
                    except Exception as e:
                        print(f"Auto summarizing paper failed: {e}")

            result_text += "\n*(前 3 篇論文的結構化分析已存入本地，您隨時可以到「比較矩陣」或「論文圖譜」中查看成果)*"
            
            suggestions = await self._generate_suggestions(intent, result_text, role_context, message)
            updated_state = self.state_skill.get_state(session_id)
            return {
                "type": "search",
                "content": result_text,
                "papers": [p.model_dump() for p in papers],
                "suggestions": suggestions,
                "role_updated": state_updated,
                "role_state": {
                    "large_direction": updated_state.large_direction,
                    "medium_direction": updated_state.medium_direction,
                } if state_updated else None
            }

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
            if not any(s.title == p.title for s in self._summaries[session_id]):
                self._summaries[session_id].append(summary)
            
            result_text = f"✅ 已為您分析論文：**{p.title}**\n\n"
            result_text += f"**研究目的：** {summary.research_goal}\n\n"
            result_text += f"**主要發現：** {summary.main_findings}\n\n"
            result_text += "*(摘要已自動存入「論文摘要」與「論文圖譜」區)*"
            
            suggestions = await self._generate_suggestions(intent, result_text, role_context, message)
            updated_state = self.state_skill.get_state(session_id)
            return {
                "type": "analyze",
                "content": result_text,
                "suggestions": suggestions,
                "role_updated": state_updated,
                "role_state": {
                    "large_direction": updated_state.large_direction,
                    "medium_direction": updated_state.medium_direction,
                } if state_updated else None
            }

        elif intent == "matrix":
            summaries = self._summaries.get(session_id, [])
            if len(summaries) < 2:
                return {"type": "chat", "content": "目前已 analyzed 的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
            matrix = await self.matrix_skill.build_matrix(summaries)
            self._matrix_cache[session_id] = matrix
            
            suggestions = await self._generate_suggestions(intent, matrix, role_context, message)
            updated_state = self.state_skill.get_state(session_id)
            return {
                "type": "matrix",
                "content": matrix,
                "suggestions": suggestions,
                "role_updated": state_updated,
                "role_state": {
                    "large_direction": updated_state.large_direction,
                    "medium_direction": updated_state.medium_direction,
                } if state_updated else None
            }

        elif intent == "direction":
            matrix = self._matrix_cache.get(session_id)
            summaries = self._summaries.get(session_id, [])
            # 檢查：無方向且無論文時，提示用戶先設定
            if role_state.is_empty() and not summaries and not matrix:
                return {
                    "type": "chat",
                    "content": "⚠️ 目前尚未設定研究方向，且沒有已分析的論文。請先：\n1. 點擊左上角「👤 研究角色設定」設定大方向與中方向，或直接告訴我您的研究領域（例如：「我的研究方向是鈣鈦礦太陽能電池」）\n2. 搜尋或上傳相關論文並生成比較矩陣後，再要求分析研究方向。",
                    "suggestions": ["我的研究方向是...", "搜尋相關論文", "幫我生成比較矩陣"]
                }
            if not matrix:
                return {"type": "chat", "content": "請先在「比較矩陣」頁面生成文獻比較矩陣，再要求分析研究方向。"}
            report = await self.direction_skill.analyze(matrix, role_context=role_context)
            
            suggestions = await self._generate_suggestions(intent, report, role_context, message)
            updated_state = self.state_skill.get_state(session_id)
            return {
                "type": "direction",
                "content": report,
                "suggestions": suggestions,
                "role_updated": state_updated,
                "role_state": {
                    "large_direction": updated_state.large_direction,
                    "medium_direction": updated_state.medium_direction,
                } if state_updated else None
            }


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
            updated_state = self.state_skill.get_state(session_id)
            return {
                "type": "analyze",
                "content": result_text,
                "papers": [p.model_dump() for p in papers],
                "suggestions": suggestions,
                "role_updated": True,
                "role_state": {
                    "large_direction": updated_state.large_direction,
                    "medium_direction": updated_state.medium_direction,
                }
            }


        else:
            # 一般對話：強制加入 RAG 本地已分析論文文獻檢索，展現 Skill/RAG 的運用
            rag_context = ""
            try:
                rag_results = self.rag_store.query(message, n_results=3)
                if rag_results:
                    rag_context = "\n根據您上傳的文獻內容：\n"
                    for idx, doc in enumerate(rag_results):
                        title = doc.get("metadata", {}).get("title", "未命名論文")
                        rag_context += f"[{idx+1}] 📄 《{title}》內文片段：\n{doc['content'][:300]}...\n\n"
            except Exception as e:
                print(f"RAG query failed: {e}")

            full_context = role_state.get_full_hierarchy_desc()
            
            enhanced_sys_prompt = SYSTEM_PROMPT.format(role_context=full_context)
            if rag_context:
                enhanced_sys_prompt += f"\n\n在回答使用者時，請優先參考以下從他們上傳的文獻中檢索出的相關片段：\n{rag_context}"
                
            history = self._chat_sessions.get(session_id, [])
            history.append({"role": "user", "parts": [message]})
            
            chat_model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                system_instruction=enhanced_sys_prompt
            )
            response = await asyncio.to_thread(
                chat_model.generate_content,
                history,
            )
            reply = response.text
            
            if rag_context:
                reply += "\n\n*(此回覆已參考您所上傳的本地文獻庫)*"
                
            history.append({"role": "model", "parts": [reply]})
            self._chat_sessions[session_id] = history[-20:]  # 保留最近 20 則
            
            suggestions = await self._generate_suggestions(intent, reply, role_context, message)
            return {"type": "chat", "content": reply, "suggestions": suggestions}

    async def upload_paper(self, session_id: str, file_path: str) -> dict:
        """處理上傳的 PDF 論文"""
        import uuid
        paper_id = str(uuid.uuid4())[:8]

        # 1. 解析 PDF
        content = parse_pdf_to_markdown(file_path)

        # 2. 生成摘要 (包含從內容中提取標題、作者、年份)
        summary = await self.analysis_skill.summarize(paper_id, content)

        # 3. 存入 RAG
        chunks = self.rag_store.add_document(paper_id, content, {"title": summary.title, "year": summary.year})

        # 4. 儲存摘要
        if session_id not in self._summaries:
            self._summaries[session_id] = []
        self._summaries[session_id].append(summary)

        return {
            "paper_id": paper_id,
            "chunks": chunks,
            "summary": summary.model_dump(),
            "message": f"論文「{summary.title}」已解析完成，共切分為 {chunks} 個段落並存入知識庫。",
        }

    async def extract_paper_metadata(self, file_path: str) -> dict:
        """解析上傳的 PDF 檔案內容並自動提取元數據"""
        content = parse_pdf_to_markdown(file_path)
        metadata = await self.analysis_skill.extract_metadata(content)
        return metadata

    def get_summaries(self, session_id: str) -> list[dict]:
        return [s.model_dump() for s in self._summaries.get(session_id, [])]

    def update_role_state(self, session_id: str, **kwargs) -> dict:
        state = self.state_skill.update_state(session_id, **kwargs)
        return state.model_dump()
