# -*- coding: utf-8 -*-
from pathlib import Path

file_path = Path("backend/agent_core.py")
content = file_path.read_text(encoding="utf-8", errors="replace")

# 1. Update SYSTEM_PROMPT to require concise academic style
old_sys_prompt = """你永遠使用繁體中文回覆。\"\"\""""
new_sys_prompt = """請永遠使用繁體中文回覆。回答應力求精準、簡明扼要，直奔主題，避免無謂的冗長學術敘述與 filler words。\"\"\""""
content = content.replace(old_sys_prompt, new_sys_prompt)

# 2. Update the chat_internal method to do Zero-Turn execution on intent
# Let's inspect the start of _chat_internal
old_chat_start = """    async def _chat_internal(self, session_id: str, message: str) -> dict:
        \"\"\"主要對話內部實作邏輯\"\"\"
        import google.api_core.exceptions as g_exceptions
        logger.info(f"Chat request - Session ID: {session_id} | Message: {message[:100]}")
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        full_context = role_state.get_full_hierarchy_desc()
        
        # 1. 偵測意圖並自動提取研究方向，讓「研究方向」能夠自動更新
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

new_chat_start = """    async def _chat_internal(self, session_id: str, message: str) -> dict:
        \"\"\"主要對話內部實作邏輯\"\"\"
        import google.api_core.exceptions as g_exceptions
        logger.info(f"Chat request - Session ID: {session_id} | Message: {message[:100]}")
        
        # 1. 優先偵測意圖 (Unconditional)
        intent_res = await self.detect_intent(message)
        intent = intent_res.get("intent", "chat")
        query = intent_res.get("query", "")
        
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        full_context = role_state.get_full_hierarchy_desc()
        
        # 2. 自動提取研究方向
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

content = content.replace(old_chat_start, new_chat_start)

# 3. Add Zero-Turn execution block immediately after URL/DOI check.
old_url_check_end = """                    suggestions = await self._generate_suggestions("analyze", result_text, role_context, message)
                    return {"type": "analyze", "content": result_text, "suggestions": suggestions}"""

new_url_check_end = """                    suggestions = await self._generate_suggestions("analyze", result_text, role_context, message)
                    return {"type": "analyze", "content": result_text, "suggestions": suggestions}

            # ─── Zero-Turn Direct Tool Execution (100% 準確直達，省去二次 LLM 工具協商時間) ───
            if intent == "search":
                logger.info(f"Zero-Turn: Direct search triggered for query '{query or message}'")
                translated_query = await self._translate_query_to_english(query or message)
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
                        
                        valid_summaries = [s for s in summaries if not isinstance(s, Exception)]
                        if valid_summaries:
                            await self._infer_and_update_direction(
                                session_id,
                                valid_summaries[0].title,
                                valid_summaries[0].keywords,
                                valid_summaries[0].research_goal + " " + valid_summaries[0].main_findings
                            )
                    except Exception as e:
                        logger.warning(f"Auto-summarizing failed: {e}")
                result_text = f"已找到 {len(papers)} 篇相關論文：\\n\\n"
                for p in papers:
                    authors = "、".join(p.authors[:3]) + ("..." if len(p.authors) > 3 else "")
                    result_text += f"📄 **{p.title}**\\n"
                    result_text += f"   - 作者：{authors}｜年份：{p.year or '未知'}\\n"
                    if p.abstract:
                        result_text += f"   - 摘要：{p.abstract[:150]}...\\n"
                    result_text += "\\n"
                result_text += "*(以上搜尋到的論文已自動分析並存入「論文摘要」記錄頁中，您可以切換分頁查看)*"
                
                suggestions = await self._generate_suggestions("search", result_text, role_context, message)
                return {"type": "search", "content": result_text, "papers": [p.model_dump() for p in papers], "suggestions": suggestions}

            elif intent == "matrix":
                logger.info("Zero-Turn: Direct comparison matrix generation triggered")
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

            elif intent == "direction":
                logger.info("Zero-Turn: Direct research direction suggestions triggered")
                matrix = self._matrix_cache.get(session_id)
                if not matrix:
                    summaries = []
                    seen = set()
                    for sums in self._summaries.values():
                        for s in sums:
                            if s.title.lower() not in seen:
                                seen.add(s.title.lower())
                                summaries.append(s)
                    if len(summaries) >= 2:
                        matrix = await self.matrix_skill.build_matrix(summaries, role_context=full_context)
                        self._matrix_cache[session_id] = matrix
                        self._save_session_data()
                    else:
                        return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成研究方向建議。"}
                
                # 計算圖譜指標
                from skills.graph_skill import SessionGraphSkill
                summaries = self.get_summaries(session_id)
                graph_insights_str = "尚無足夠文獻建立圖譜指標（至少需要 2 篇）。"
                if len(summaries) >= 2:
                    try:
                        g_skill = SessionGraphSkill()
                        metrics = g_skill.compute_graph_metrics(summaries)
                        
                        infl_str = "\\n".join([f"- **{x['title']}** (PageRank重要度: {x['pagerank']:.4f})" for x in metrics.get("influence", [])[:3]])
                        
                        comm_str = ""
                        for cid, papers in metrics.get("communities", {}).items():
                            comm_str += f"- 技術流派/社群 {cid}:\\n"
                            for p in papers:
                                comm_str += f"  * {p}\\n"
                        
                        bridges = [x for x in metrics.get("bridges", []) if x['betweenness'] > 0]
                        bridge_str = "\\n".join([f"- **{x['title']}** (Betweenness橋接度: {x['betweenness']:.4f})" for x in bridges[:3]])
                        if not bridge_str:
                            bridge_str = "- 尚無顯著的跨領域橋接文獻。"
                            
                        graph_insights_str = f"1. 核心文獻排名 (PageRank):\\n{infl_str}\\n\\n2. 技術社群分組 (Louvain):\\n{comm_str}\\n\\n3. 跨領域橋接文獻 (Betweenness):\\n{bridge_str}"
                    except Exception as ge:
                        logger.warning(f"Failed to compute graph metrics for directions: {ge}")
                        graph_insights_str = "圖譜指標計算失敗，僅使用矩陣分析。"

                report = await self.direction_skill.analyze(matrix, role_context=full_context, graph_insights=graph_insights_str)
                self._direction_cache[session_id] = report
                self._save_session_data()
                
                suggestions = await self._generate_suggestions("direction", report, role_context, message)
                return {"type": "direction", "content": report, "suggestions": suggestions}"""

content = content.replace(old_url_check_end, new_url_check_end)

# 4. Limit max output tokens for general chat to prevent long text generation overhead
old_chat_generation = """                chat_model = genai.GenerativeModel(
                    model_name=self.MODEL_NAME,
                    system_instruction=sys_prompt
                )
                response = await asyncio.to_thread(
                    chat_model.generate_content,
                    history,
                )"""

new_chat_generation = """                chat_model = genai.GenerativeModel(
                    model_name=self.MODEL_NAME,
                    system_instruction=sys_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=1024
                    )
                )
                response = await asyncio.to_thread(
                    chat_model.generate_content,
                    history,
                )"""

content = content.replace(old_chat_generation, new_chat_generation)

file_path.write_text(content, encoding="utf-8")
print("Zero-Turn and max token limit applied to AgentCore.")
