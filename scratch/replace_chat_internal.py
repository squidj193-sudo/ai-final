# -*- coding: utf-8 -*-
import sys

def main():
    filepath = "backend/agent_core.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "    async def _chat_internal(self, session_id: str, message: str) -> dict:"
    end_marker = "    async def upload_paper(self, session_id: str, file_path: str, title: Optional[str] = None"

    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("Error: start_marker not found")
        sys.exit(1)

    end_idx = content.find(end_marker)
    if end_idx == -1:
        print("Error: end_marker not found")
        sys.exit(1)

    # Let's verify we got the right blocks
    print(f"Start index: {start_idx}, End index: {end_idx}")

    new_chat_internal = """    async def _chat_internal(self, session_id: str, message: str) -> dict:
        \"\"\"主要對話內部實作邏輯\"\"\"
        import google.api_core.exceptions as g_exceptions
        logger.info(f"Chat request - Session ID: {session_id} | Message: {message[:100]}")
        role_state = self.state_skill.get_state(session_id)
        role_context = role_state.get_search_context()
        full_context = role_state.get_full_hierarchy_desc()

        # 1. 優先檢測使用者輸入是否包含 URL 或 DOI
        import re
        cleaned_message = re.sub(r'(https?)\\s*:\\s*/\\s*/', r'\\1://', message)
        url_match = re.search(r'(https?://[^\\s]+)', cleaned_message)
        doi_match = re.search(r'(10\\.\\d{4,9}/[-._;()/:a-zA-Z0-9]+)', cleaned_message)
        
        is_url_or_doi = False
        target_query = ""
        if doi_match:
            is_url_or_doi = True
            target_query = doi_match.group(1)
        elif url_match:
            is_url_or_doi = True
            target_query = url_match.group(1)
            
        if is_url_or_doi:
            logger.info(f"Direct URL/DOI detected: {target_query}")
            paper = await self.search_skill.fetch_paper_by_id_or_url(target_query)
            if paper:
                import uuid
                paper_id = paper.paper_id or str(uuid.uuid4())[:8]
                content_paper = paper.abstract or "無摘要"
                
                # 使用 analysis_skill.summarize 生成摘要
                summary = await self.analysis_skill.summarize(
                    paper_id=paper_id,
                    title=paper.title,
                    authors=paper.authors,
                    year=paper.year,
                    content=content_paper,
                )
                
                if session_id not in self._summaries:
                    self._summaries[session_id] = []
                # 避免重複加入
                if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                    self._summaries[session_id].append(summary)
                self._save_session_data()
                
                # 同時將資訊寫入 RAG
                try:
                    self.rag_store.add_document(paper_id, content_paper, {"title": summary.title, "year": summary.year})
                except Exception as ree:
                    logger.warning(f"Failed to add to RAG: {ree}")
                
                result_text = f"✅ 已成功抓取並分析您提供的論文：**{summary.title}**\\n\\n"
                result_text += f"**研究目的：** {summary.research_goal}\\n\\n"
                result_text += f"**主要發現：** {summary.main_findings}\\n\\n"
                result_text += f"**研究限制：** {summary.limitations}\\n\\n"
                result_text += "*(此論文結構化摘要已自動儲存至「論文摘要」分頁中)*"
                
                suggestions = await self._generate_suggestions("analyze", result_text, role_context, message)
                return {"type": "analyze", "content": result_text, "suggestions": suggestions}
            else:
                # 備用方案：如果無法從 Semantic Scholar 取得學術資料，嘗試直接爬取網頁內容進行摘要
                if target_query.startswith("http://") or target_query.startswith("https://"):
                    try:
                        logger.info(f"Semantic Scholar lookup failed. Crawling URL directly: {target_query}")
                        import httpx
                        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                            resp = await client.get(target_query, headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            })
                            if resp.status_code == 200:
                                html_content = resp.text
                                import re
                                text_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
                                text_content = re.sub(r'<style.*?</style>', '', text_content, flags=re.DOTALL)
                                text_content = re.sub(r'<.*?>', '', text_content, flags=re.DOTALL)
                                text_content = re.sub(r'\\s+', ' ', text_content).strip()
                                
                                title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
                                page_title = title_match.group(1).strip() if title_match else "網路文章"
                                
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
                                
                                result_text = f"✅ 已成功擷取並分析網頁文章：**{summary.title}**\\n\\n"
                                result_text += f"**研究目的：** {summary.research_goal}\\n\\n"
                                result_text += f"**主要發現：** {summary.main_findings}\\n\\n"
                                result_text += f"**研究限制：** {summary.limitations}\\n\\n"
                                result_text += "*(此文章結構化摘要已自動儲存至「論文摘要」分頁中)*"
                                
                                suggestions = await self._generate_suggestions("analyze", result_text, role_context, message)
                                return {"type": "analyze", "content": result_text, "suggestions": suggestions}
                    except Exception as ce:
                        logger.warning(f"Failed to crawl URL fallback '{target_query}': {ce}")
                
                logger.warning(f"Could not fetch paper details by URL/DOI directly. Returning error message.")
                if target_query.startswith("http://") or target_query.startswith("https://"):
                    error_desc = f"⚠️ 無法讀取該網頁或論文內容（可能因為該網站有防爬蟲機制，如 Medium / Cloudflare，或不屬於公開學術資料庫格式）。\\n\\n**建議您：**\\n1. 直接使用 **「📎 上傳論文」** 功能上傳 PDF 檔案。\\n2. 將論文摘要或內文複製並直接貼上到對話框中，讓我為您進行分析。"
                    return {"type": "error", "content": error_desc, "suggestions": ["直接搜尋相關文獻", "如何上傳 PDF 論文"]}
                else:
                    error_desc = f"⚠️ 無法透過 DOI `{target_query}` 獲取論文資料（Semantic Scholar 資料庫中可能尚未收錄此 DOI）。\\n\\n**建議您：**\\n1. 使用 **「📎 上傳論文」** 功能上傳 PDF 檔案。\\n2. 直接輸入關鍵字讓我為您搜尋相似文獻。"
                    return {"type": "error", "content": error_desc, "suggestions": ["直接搜尋相關文獻", "如何上傳 PDF 論文"]}

        # 2. 意圖檢測與 Zero-Turn 路由
        try:
            intent_res = await self.detect_intent(message)
            intent = intent_res.get("intent", "chat")
            query = intent_res.get("query") or message
            
            # 尚未進展到論文摘要，則在對話中自動推導並更新方向
            has_summaries = bool(self.get_summaries(session_id))
            if not has_summaries:
                await self._infer_and_update_direction(session_id, "", [], message)
                # 重新取得更新後的 context
                role_state = self.state_skill.get_state(session_id)
                role_context = role_state.get_search_context()
                full_context = role_state.get_full_hierarchy_desc()
        except Exception as e:
            logger.warning(f"Intent detection or auto-updating direction failed: {e}")
            intent = "chat"
            query = message

        try:
            if intent == "set_direction":
                # 提取大中小方向
                extracted = await self._extract_directions_from_message(message)
                large = extracted.get("large") or ""
                medium = extracted.get("medium") or ""
                small = extracted.get("small") or ""
                
                # 如果提取失敗，試著用 infer
                if not large:
                    await self._infer_and_update_direction(session_id, "", [], message)
                else:
                    self.state_skill.update_state(
                        session_id,
                        large_direction=large if large else None,
                        medium_direction=medium if medium else None,
                        small_direction=small if small else None
                    )
                
                role_state = self.state_skill.get_state(session_id)
                role_context = role_state.get_search_context()
                full_context = role_state.get_full_hierarchy_desc()
                
                search_query = small or medium or large or query or message
                translated_query = await self._translate_query_to_english(search_query)
                translated_context = await self._translate_query_to_english(role_context) if role_context else ""
                papers = await self.search_skill.search(translated_query, context=translated_context, limit=2)
                
                result_text = f"🎯 **已為您設定並儲存研究方向：**\\n"
                if role_state.large_direction: result_text += f"- **大方向**：{role_state.large_direction}\\n"
                if role_state.medium_direction: result_text += f"- **中方向**：{role_state.medium_direction}\\n"
                if role_state.small_direction: result_text += f"- **小方向**：{role_state.small_direction}\\n"
                
                result_text += f"\\n🔍 **已自動為您檢索並分析相關論文：**\\n\\n"
                
                if papers:
                    import uuid
                    for idx, p in enumerate(papers):
                        content_paper = p.abstract or "無摘要"
                        paper_id = p.paper_id or str(uuid.uuid4())[:8]
                        summary = await self.analysis_skill.summarize(
                            paper_id=paper_id,
                            title=p.title,
                            authors=p.authors,
                            year=p.year,
                            content=content_paper
                        )
                        if session_id not in self._summaries:
                            self._summaries[session_id] = []
                        if not any(x.title.lower() == summary.title.lower() for x in self._summaries[session_id]):
                            self._summaries[session_id].append(summary)
                    self._save_session_data()
                    result_text += "*(以上論文摘要已自動存入「論文摘要」記錄頁中，您可以切換分頁查看)*"
                else:
                    result_text += "（未尋找到相關論文）\\n"
                
                suggestions = await self._generate_suggestions("set_direction", result_text, role_context, message)
                return {
                    "type": "analyze",
                    "content": result_text,
                    "papers": [p.model_dump() for p in papers] if papers else [],
                    "suggestions": suggestions
                }

            elif intent == "search":
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
                        
                        # 自動從搜尋出來的第一篇論文摘要推導並設定研究方向
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
                return {"type": "search", "content": result_text, "papers": [p.model_dump() for p in papers] if papers else [], "suggestions": suggestions}

            elif intent == "matrix":
                summaries = self.get_summaries(session_id)
                if len(summaries) < 2:
                    return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
                matrix = await self.matrix_skill.build_matrix(summaries, role_context=full_context)
                self._matrix_cache[session_id] = matrix
                self._save_session_data()
                
                suggestions = await self._generate_suggestions("matrix", matrix, role_context, message)
                return {"type": "matrix", "content": matrix, "suggestions": suggestions}

            elif intent == "direction":
                matrix = self._matrix_cache.get(session_id)
                if not matrix:
                    summaries = self.get_summaries(session_id)
                    if len(summaries) >= 2:
                        matrix = await self.matrix_skill.build_matrix(summaries, role_context=full_context)
                        self._matrix_cache[session_id] = matrix
                        self._save_session_data()
                    else:
                        return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
                
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
                return {"type": "direction", "content": report, "suggestions": suggestions}

            else:
                # 一般對話
                sys_prompt = SYSTEM_PROMPT.format(role_context=full_context)
                
                # 自動調用 RAG 檢索
                try:
                    rag_results = self.rag_store.query(message, n_results=3)
                    if rag_results:
                        context_str = "\\n\\n".join([
                            f"來源文獻【{r['metadata'].get('title', '未知')}】:\\n{r['content']}" 
                            for r in rag_results
                        ])
                        sys_prompt += f"\\n\\n此外，以下是從你已分析的論文中檢索到的相關內容，請優先參考這些內容來回答使用者的提問，並在回答中註明參考來源：\\n{context_str}"
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
                self._chat_sessions[session_id] = history[-20:]
                
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

"""

    new_content = content[:start_idx] + new_chat_internal + content[end_idx:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Successfully replaced _chat_internal")

if __name__ == "__main__":
    main()
