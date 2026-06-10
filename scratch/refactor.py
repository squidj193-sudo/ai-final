# -*- coding: utf-8 -*-
import os
from pathlib import Path

file_path = Path("backend/agent_core.py")
content = file_path.read_text(encoding="utf-8", errors="replace")

# 1. Tool definition
old_tool = """def set_research_direction(large_direction: str, medium_direction: str = "", small_direction: str = "") -> str:
    \"\"\"
    設定或更改使用者的學術研究大方向、中方向或小方向範疇。

    Args:
        large_direction: 最上層領域範疇，例如：生醫、半導體、光電、人工智慧、永續發展。
        medium_direction: 中層次研究技術或子領域，例如：基因工程、第三代半導體、太陽能電池、深度學習。
        small_direction: 具體研究主題或材料，例如：CRISPR 基因編輯、碳化矽元件、鈣鈦礦材料、物件偵測。
    \"\"\"
    return "已觸發設定研究方向\""""

new_tool = """def set_research_direction(research_direction: str) -> str:
    \"\"\"
    設定或更改使用者的學術研究方向範疇。

    Args:
        research_direction: 具體研究主題或領域範疇，例如：鈣鈦礦太陽能電池、大型語言模型微調、生醫基因編輯。
    \"\"\"
    return "已觸發設定研究方向\""""

# 2. _extract_directions_from_message
old_extract = """    async def _extract_directions_from_message(self, message: str) -> dict:
        \"\"\"從使用者訊息中提取大、中、小研究方向\"\"\"
        prompt = f\"\"\"請分析以下使用者關於研究方向的描述，並將其拆解為學術研究的「大方向」、「中方向」、「小方向」。
大方向：最上層領域範疇，例如：生醫、半導體、光電、人工智慧、永續發展。
中方向：中層次研究技術或子領域，例如：基因工程、第三代半導體、太陽能電池、深度學習。
小方向：具體研究主題或材料，例如：CRISPR 基因編輯、碳化矽元件、鈣鈦礦材料、物件偵測。

使用者描述："{message}"

請回傳以下 JSON 格式，若無法提取則填 null。不要包含任何 Markdown 區塊或額外文字：
{{
  "large_direction": "大方向名稱或 null",
  "medium_direction": "中方向名稱或 null",
  "small_direction": "小方向名稱或 null"
}}\"\"\"
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
            raw = response.text.strip()
            res = self._parse_json_robustly(raw)
            return {
                "large": res.get("large_direction"),
                "medium": res.get("medium_direction"),
                "small": res.get("small_direction")
            }
        except Exception as e:
            logger.warning(f"Failed to extract directions: {e}")
            return {"large": None, "medium": None, "small": None}"""

new_extract = """    async def _extract_directions_from_message(self, message: str) -> dict:
        \"\"\"從使用者訊息中提取研究方向\"\"\"
        prompt = f\"\"\"請分析以下使用者關於研究方向的描述，並將其提取為單一的「研究方向」主題。
範例：永續發展與能源、鈣鈦礦太陽能電池、大型語言模型微調。

使用者描述："{message}"

請回傳以下 JSON 格式，若無法提取則填 null。不要包含 any markdown 標記或額外文字：
{{
  "research_direction": "研究方向名稱或 null"
}}\"\"\"
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
            raw = response.text.strip()
            res = self._parse_json_robustly(raw)
            return {
                "research_direction": res.get("research_direction")
            }
        except Exception as e:
            logger.warning(f"Failed to extract direction: {e}")
            return {"research_direction": None}"""

# 3. _infer_and_update_direction
old_infer = """    async def _infer_and_update_direction(self, session_id: str, title: str, keywords: list[str], abstract: str = "") -> None:
        \"\"\"根據論文標題、關鍵字與摘要，或使用者對話內容自動推導並更新大、中、小研究方向\"\"\"
        # 如果已經進展到論文摘要階段，且大、中、小方向都已經設定完整，就不再覆寫
        has_summaries = bool(self.get_summaries(session_id))
        current_state = self.state_skill.get_state(session_id)
        if has_summaries and current_state.large_direction and current_state.medium_direction and current_state.small_direction:
            return # 已經設定完整且有論文摘要，不覆寫
            
        # 動態調整 Prompt，區分「特定論文」與「一般對話」
        if not title and not keywords:
            # 一般對話推導
            prompt = f\"\"\"你是一個學術研究分類專家。請針對以下使用者的對話內容或研究想法，歸納推導出最適當的「大方向（學門領域）」、「中方向（子領域技術）」、「小方向（具體主題材料/特定技術）」。

【分類定義與範例說明】：
1. 大方向 (Large Direction)：最上層的主流領域範疇。
   - 例如：永續發展與能源、人工智慧與資訊、生醫健康、半導體與先進製造、光電物理。
2. 中方向 (Medium Direction)：中層次的研究技術、方法或子領域。
   - 例如：太陽能技術、深度學習、大型語言模型、微電子元件、基因工程。
3. 小方向 (Small Direction)：最底層的具體研究主題、材料、演算法或特定技術應用。
   - 例如：鈣鈦礦太陽能電池、物體偵測、Chain-of-Thought (CoT) 推理、矽基電晶體、CRISPR 基因編輯。

【使用者對話內容】：
"{abstract}"

請務必精準回傳一個 JSON 物件，請勿包含 any markdown 標記（如 ```json）或額外文字，僅回傳 JSON 物件：
{{
  "large_direction": "推導的大方向（限 2-10 字，例如：人工智慧與資訊）",
  "medium_direction": "推導的中方向（限 2-10 字，roleForm.medium，例如：大型語言模型）",
  "small_direction": "推導的小方向（限 2-12 字，roleForm.small，例如：Chain-of-Thought 推理）"
}}\"\"\"
        else:
            # 論文推導
            prompt = f\"\"\"你是一個學術研究分類專家。請針對以下提供的論文標題、關鍵字與摘要，為其歸納推導出最適當的「大方向（學門領域）」、「中方向（子領域技術）」、「小方向（具體主題材料）」。

【分類定義與範例說明】：
1. 大方向 (Large Direction)：最上層的主流領域範疇（通常是跨學門或核心學科）。
   - 例如：永續發展與能源、人工智慧與資訊、生醫健康、半導體與先進製造、光電物理。
2. 中方向 (Medium Direction)：中層次的研究技術、方法或子領域。
   - 例如：太陽能技術、深度學習、基因工程、微電子元件。
3. 小方向 (Small Direction)：最底層的具體研究主題、材料、演算法或特定應用。
   - 例如：鈣鈦礦太陽能電池、物體偵測、CRISPR 基因編輯、矽基電晶體。

【待分析論文資訊】：
論文標題：{title}
關鍵字：{", ".join(keywords) if keywords else "未提供"}
摘要：{abstract[:1000]}

請務必嚴格以下列 JSON 格式回傳，請勿包含 any markdown 標記（如 ```json）或額外敘述，僅回傳 JSON 物件：
{{
  "large_direction": "推導的大方向（限 2-10 字，例如：永續發展與能源）",
  "medium_direction": "推導的中方向（限 2-10 字，例如：太陽能技術）",
  "small_direction": "推導的小方向（限 2-12 字，例如：鈣鈦礦太陽能電池）"
}}\"\"\"
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
            raw = response.text.strip()
            res = self._parse_json_robustly(raw)
            
            large = res.get("large_direction")
            medium = res.get("medium_direction")
            small = res.get("small_direction")
            
            # 清理可能夾帶的 "例：" 等無效字樣
            def clean_dir(val):
                if not val:
                    return None
                val = val.strip().replace("例：", "").replace("例如：", "").strip(" \\"'、")
                return val if val and val.lower() != "null" else None

            large = clean_dir(large)
            medium = clean_dir(medium)
            small = clean_dir(small)
            
            if large:
                self.state_skill.update_state(
                    session_id,
                    large_direction=large,
                    medium_direction=None,
                    small_direction=None
                )
                self._save_session_data()
                logger.info(f"Automatically inferred and updated research direction for session {session_id}: {large}")
        except Exception as e:
            logger.warning(f"Failed to infer research direction: {e}")"""

new_infer = """    async def _infer_and_update_direction(self, session_id: str, title: str, keywords: list[str], abstract: str = "") -> None:
        \"\"\"根據論文標題、關鍵字與摘要，或使用者對話內容自動推導並更新研究方向\"\"\"
        has_summaries = bool(self.get_summaries(session_id))
        current_state = self.state_skill.get_state(session_id)
        if has_summaries and current_state.research_direction:
            return # 已經設定完整且有論文摘要，不覆寫
            
        # 動態調整 Prompt，區分「特定論文」與「一般對話」
        if not title and not keywords:
            # 一般對話推導
            prompt = f\"\"\"你是一個學術研究分類專家。請針對以下使用者的對話內容或研究想法，歸納推導出一個具體且適當的「研究方向」（限 2-15 字，例如：鈣鈦礦太陽能電池、大型語言模型微調、CRISPR 基因編輯）。

【使用者對話內容】：
"{abstract}"

請務必精準回傳一個 JSON 物件，請勿包含 any markdown 標記（如 ```json）或額外文字，僅回傳 JSON 物件：
{{
  "research_direction": "推導的研究方向"
}}\"\"\"
        else:
            # 論文推導
            prompt = f\"\"\"你是一個學術研究分類專家。請針對以下提供的論文標題、關鍵字與摘要，為其歸納推導出一個具體且適當的「研究方向」（限 2-15 字，例如：鈣鈦礦太陽能電池、大型語言模型微調、CRISPR 基因編輯）。

【待分析論文資訊】：
論文標題：{title}
關鍵字：{", ".join(keywords) if keywords else "未提供"}
摘要：{abstract[:1000]}

請務必嚴格以下列 JSON 格式回傳，請勿包含 any markdown 標記（如 ```json）或額外敘述，僅回傳 JSON 物件：
{{
  "research_direction": "推導的研究方向"
}}\"\"\"
        try:
            response = await asyncio.to_thread(self._intent_model.generate_content, prompt)
            raw = response.text.strip()
            res = self._parse_json_robustly(raw)
            
            direction = res.get("research_direction")
            
            # 清理可能夾帶的 "例：" 等無效字樣
            if direction:
                direction = direction.strip().replace("例：", "").replace("例如：", "").strip(" \\"'、")
                if direction and direction.lower() != "null":
                    self.state_skill.update_state(
                        session_id,
                        research_direction=direction
                    )
                    self._save_session_data()
                    logger.info(f"Automatically inferred and updated research direction for session {session_id}: {direction}")
        except Exception as e:
            logger.warning(f"Failed to infer research direction: {e}")"""

# 4. _chat_internal method logic around update_state
old_chat_internal_intent = """        # 1. 偵測意圖並自動提取研究方向，讓「大中小方向」能夠自動更新
        try:
            has_summaries = bool(self.get_summaries(session_id))
            if not has_summaries:
                # 尚未進展到論文摘要，則在所有對話中自動推導並更新方向
                await self._infer_and_update_direction(session_id, "", [], message)
                # 重新取得更新後的 context
                role_state = self.state_skill.get_state(session_id)
                role_context = role_state.get_search_context()
                full_context = role_state.get_full_hierarchy_desc()
            else:
                # 若已有摘要，僅在包含明確設定意圖時嘗試提取
                intent_res = await self.detect_intent(message)
                intent = intent_res.get("intent", "chat")
                if intent == "set_direction":
                    extracted = await self._extract_directions_from_message(message)
                    if extracted.get("large"):
                        self.state_skill.update_state(
                            session_id,
                            large_direction=extracted["large"],
                            medium_direction=None,
                            small_direction=None
                        )
                        # 重新取得更新後的 context
                        role_state = self.state_skill.get_state(session_id)
                        role_context = role_state.get_search_context()
                        full_context = role_state.get_full_hierarchy_desc()
        except Exception as e:
            logger.warning(f"Auto-updating direction failed: {e}")"""

new_chat_internal_intent = """        # 1. 偵測意圖並自動提取研究方向，讓「研究方向」能夠自動更新
        try:
            has_summaries = bool(self.get_summaries(session_id))
            if not has_summaries:
                # 尚未進展到論文摘要，則在所有對話中自動推導並更新方向
                await self._infer_and_update_direction(session_id, "", [], message)
                # 重新取得更新後的 context
                role_state = self.state_skill.get_state(session_id)
                role_context = role_state.get_search_context()
                full_context = role_state.get_full_hierarchy_desc()
            else:
                # 若已有摘要，僅在包含明確設定意圖時嘗試提取
                intent_res = await self.detect_intent(message)
                intent = intent_res.get("intent", "chat")
                if intent == "set_direction":
                    extracted = await self._extract_directions_from_message(message)
                    if extracted.get("research_direction"):
                        self.state_skill.update_state(
                            session_id,
                            research_direction=extracted["research_direction"]
                        )
                        # 重新取得更新後的 context
                        role_state = self.state_skill.get_state(session_id)
                        role_context = role_state.get_search_context()
                        full_context = role_state.get_full_hierarchy_desc()
        except Exception as e:
            logger.warning(f"Auto-updating direction failed: {e}")"""

# 5. set_research_direction tool call execution in chat_internal
old_tool_call = """                elif name == "set_research_direction":
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
                    
                    result_text = f"🎯 **已為您設定並儲存研究方向：**\\n"
                    if large: result_text += f"- **大方向**：{large}\\n"
                    if medium: result_text += f"- **中方向**：{medium}\\n"
                    if small: result_text += f"- **小方向**：{small}\\n"
                    
                    result_text += f"\\n🔍 **已自動為您檢索並分析相關論文：**\\n\\n"
                    
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
                        self._save_session_data()"""

new_tool_call = """                elif name == "set_research_direction":
                    research_dir = args.get("research_direction") or ""
                    
                    self.state_skill.update_state(
                        session_id,
                        research_direction=research_dir if research_dir else None
                    )
                    
                    role_state = self.state_skill.get_state(session_id)
                    role_context = role_state.get_search_context()
                    full_context = role_state.get_full_hierarchy_desc()
                    
                    search_query = research_dir or message
                    translated_query = await self._translate_query_to_english(search_query)
                    translated_context = await self._translate_query_to_english(role_context) if role_context else ""
                    papers = await self.search_skill.search(translated_query, context=translated_context, limit=2)
                    
                    result_text = f"🎯 **已為您設定並儲存研究方向：**\\n"
                    if research_dir: result_text += f"- **研究方向**：{research_dir}\\n"
                    
                    result_text += f"\\n🔍 **已自動為您檢索並分析相關論文：**\\n\\n"
                    
                    if papers:
                        import uuid
                        for idx, p in enumerate(papers):
                            p_content = p.abstract or "無摘要"
                            paper_id = p.paper_id or str(uuid.uuid4())[:8]
                            summary = await self.analysis_skill.summarize(
                                paper_id=paper_id,
                                title=p.title,
                                authors=p.authors,
                                year=p.year,
                                content=p_content
                            )
                            if session_id not in self._summaries:
                                self._summaries[session_id] = []
                            if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                                self._summaries[session_id].append(summary)
                        self._save_session_data()"""

# 6. Fallback search
old_search_fallback = """                # 自動搜尋論文
                search_query = query if query else (small or medium or large or message)"""
new_search_fallback = """                # 自動搜尋論文
                search_query = query if query else (role_context or message)"""

# Apply literal replacements
content = content.replace(old_tool, new_tool)
content = content.replace(old_extract, new_extract)
content = content.replace(old_infer, new_infer)
content = content.replace(old_chat_internal_intent, new_chat_internal_intent)
content = content.replace(old_tool_call, new_tool_call)
content = content.replace(old_search_fallback, new_search_fallback)

file_path.write_text(content, encoding="utf-8", errors="replace")
print("Literal refactoring done.")
