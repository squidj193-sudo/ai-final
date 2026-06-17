import re
import logging

# Lazy-loaded modules will be imported inside functions to speed up AgentCore startup time

def ch_en_tokenizer(text):
    import jieba
    jieba.setLogLevel(logging.WARNING)
    if not text:
        return []
    words = jieba.lcut(text.lower())
    tokens = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        # Check if it contains Chinese characters
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in w)
        if has_chinese:
            # Filter out single characters to keep only words with length >= 2
            if len(w) >= 2:
                tokens.append(w)
        else:
            # Keep English/number words with length >= 2
            if len(w) >= 2 and re.match(r'^[a-zA-Z0-9\-_]+$', w):
                tokens.append(w)
    return tokens

class SessionGraphSkill:
    # NOTE: generate_graph_html() 已移除（原使用 PyVis 生成後端 HTML，但無任何 API 端點呼叫）
    # 前端使用 get_graph_data() JSON API + vis-network 自行渲染，pyvis 依賴可從 requirements.txt 移除

    def compute_graph_metrics(self, summaries: list) -> dict:
        """
        計算圖的 PageRank (核心論文重要度)、Betweenness Centrality (跨流派樞紐)、與 Louvain 社群 (技術流派)
        """
        import networkx as nx
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import community as community_louvain

        if not summaries:
            return {"influence": [], "communities": {}, "bridges": []}

        G = nx.Graph()
        
        # 1. 建立節點
        for idx, s in enumerate(summaries):
            title = s.get("title", "")
            goal = s.get("research_goal", "")
            findings = s.get("main_findings", "")
            keywords = s.get("keywords", [])
            keywords_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            combined_text = f"{title} {keywords_str} {goal} {findings}"
            G.add_node(idx, title=title, combined_text=combined_text)

        # 2. 建立相似度連線
        if len(summaries) > 1:
            corpus = [G.nodes[i]["combined_text"] for i in range(len(summaries))]
            try:
                vectorizer = TfidfVectorizer(tokenizer=ch_en_tokenizer, token_pattern=None)
                tfidf = vectorizer.fit_transform(corpus)
                sim_matrix = cosine_similarity(tfidf)
                
                max_sim = 0.0
                for i in range(len(summaries)):
                    for j in range(i + 1, len(summaries)):
                        max_sim = max(max_sim, float(sim_matrix[i, j]))
                
                threshold = min(0.12, max_sim * 0.75) if max_sim > 0.05 else 0.12
                
                for i in range(len(summaries)):
                    for j in range(i + 1, len(summaries)):
                        sim = float(sim_matrix[i, j])
                        if sim >= threshold:
                            G.add_edge(i, j, weight=sim)
                
                # 確保孤立點至少連線至其最相似的點
                for i in range(len(summaries)):
                    if G.degree(i) == 0:
                        best_j = -1
                        best_sim = 0.0
                        for j in range(len(summaries)):
                            if i != j:
                                sim = float(sim_matrix[i, j])
                                if sim > best_sim:
                                    best_sim = sim
                                    best_j = j
                        if best_j != -1 and best_sim > 0.02:
                            G.add_edge(i, best_j, weight=best_sim)
            except Exception as e:
                print(f"Error computing graph metrics edges: {e}")

        # 3. 計算 PageRank
        try:
            pagerank = nx.pagerank(G, weight="weight")
        except Exception:
            pagerank = {n: 1.0/len(G) for n in G.nodes()}

        # 4. 計算 Louvain 社群
        try:
            partition = community_louvain.best_partition(G)
        except Exception:
            partition = {n: 0 for n in G.nodes()}

        # 5. 計算 Betweenness Centrality (跨社群橋接度)
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
        except Exception:
            betweenness = {n: 0.0 for n in G.nodes()}

        # 6. 包裝成果
        influence_list = []
        communities_map = {}
        bridge_list = []
        
        for n in G.nodes():
            title = G.nodes[n]["title"]
            pr_val = pagerank.get(n, 0.0)
            cluster_id = partition.get(n, 0)
            bt_val = betweenness.get(n, 0.0)
            
            influence_list.append({"title": title, "pagerank": pr_val})
            bridge_list.append({"title": title, "betweenness": bt_val})
            
            if cluster_id not in communities_map:
                communities_map[cluster_id] = []
            communities_map[cluster_id].append(title)
            
        influence_list.sort(key=lambda x: x["pagerank"], reverse=True)
        bridge_list.sort(key=lambda x: x["betweenness"], reverse=True)
        
        return {
            "influence": influence_list,
            "communities": communities_map,
            "bridges": bridge_list
        }

    def get_graph_data(self, summaries: list) -> dict:
        """
        計算並回傳論文知識圖譜的 Nodes 與 Edges 結構化 JSON 資料
        """
        import networkx as nx
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import community as community_louvain

        if not summaries:
            return {"nodes": [], "edges": [], "count": 0}

        # 1. 建立 NetworkX Graph
        G = nx.Graph()
        for idx, s in enumerate(summaries):
            title = s.get("title", "")
            goal = s.get("research_goal", "")
            findings = s.get("main_findings", "")
            keywords = s.get("keywords", [])
            keywords_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            combined_text = f"{title} {keywords_str} {goal} {findings}"
            G.add_node(idx, title=title, combined_text=combined_text)

        # 2. 計算 TF-IDF 與 Cosine 相似度
        edges_data = []
        if len(summaries) > 1:
            corpus = [G.nodes[i]["combined_text"] for i in range(len(summaries))]
            try:
                vectorizer = TfidfVectorizer(tokenizer=ch_en_tokenizer, token_pattern=None)
                tfidf = vectorizer.fit_transform(corpus)
                sim_matrix = cosine_similarity(tfidf)

                # 提取共同關鍵字，並建立所有潛在 edges (包含微弱關聯，供前端拉桿動態過濾)
                for i in range(len(summaries)):
                    for j in range(i + 1, len(summaries)):
                        sim = float(sim_matrix[i, j])
                        if sim > 0.02: # 放寬相似度，讓前端滑桿有更大的調控空間
                            row_i = tfidf[i].toarray()[0]
                            row_j = tfidf[j].toarray()[0]
                            overlap = row_i * row_j
                            feature_names = vectorizer.get_feature_names_out()
                            top_indices = np.argsort(overlap)[::-1]
                            common = [feature_names[idx] for idx in top_indices if overlap[idx] > 0][:5]
                            
                            edges_data.append({
                                "from": i,
                                "to": j,
                                "weight": sim,
                                "common_terms": common
                            })
                            G.add_edge(i, j, weight=sim)
            except Exception as e:
                print(f"Error computing graph data similarities: {e}")

        # 3. 計算重要度指標與社群群組
        try:
            pagerank = nx.pagerank(G, weight="weight")
        except Exception:
            pagerank = {n: 1.0/len(G) for n in G.nodes()}

        try:
            partition = community_louvain.best_partition(G)
        except Exception:
            partition = {n: 0 for n in G.nodes()}

        # 4.5 為每個社群產生人類友善的代表性標籤
        # 優先使用論文自帶的 keywords 欄位，fallback 到 TF-IDF tokenizer
        from collections import Counter
        community_labels = {}
        try:
            # 按群組收集論文資料
            group_papers = {}  # cid -> list of summary dicts
            for idx in range(len(summaries)):
                cid = partition.get(idx, 0)
                if cid not in group_papers:
                    group_papers[cid] = []
                group_papers[cid].append(summaries[idx])

            for cid, papers in group_papers.items():
                # 如果群組只有 1 篇論文，直接用標題前 15 字
                if len(papers) == 1:
                    title = papers[0].get("title", "")
                    community_labels[str(cid)] = title[:15] + "…" if len(title) > 15 else (title or f"社群 {cid}")
                    continue

                # 策略一：從論文的 keywords 欄位統計高頻關鍵字
                all_keywords = []
                for p in papers:
                    kws = p.get("keywords", [])
                    if isinstance(kws, list):
                        all_keywords.extend([k.strip() for k in kws if k.strip()])

                if all_keywords:
                    freq = Counter(all_keywords)
                    # 過濾掉太泛的詞
                    generic = {"research", "study", "analysis", "review", "model", "method",
                               "approach", "system", "data", "results", "paper", "based"}
                    filtered = [(w, c) for w, c in freq.most_common(10)
                                if w.lower() not in generic and len(w) >= 2]
                    top_words = [w for w, _ in filtered[:3]]
                    if top_words:
                        community_labels[str(cid)] = " · ".join(top_words)
                        continue

                # 策略二 (fallback)：從合併文本用 tokenizer 取詞頻
                merged = " ".join(G.nodes[idx]["combined_text"]
                                  for idx in range(len(summaries))
                                  if partition.get(idx, 0) == cid)
                tokens = ch_en_tokenizer(merged)
                if tokens:
                    freq = Counter(tokens)
                    stopwords = {"the", "and", "for", "with", "from", "that", "this",
                                 "are", "was", "were", "has", "have", "been", "not",
                                 "but", "can", "also", "will", "our", "their", "which",
                                 "based", "using", "used", "results", "study",
                                 "research", "paper", "method", "approach", "proposed",
                                 "show", "than", "more", "most", "one", "two"}
                    filtered = [(w, c) for w, c in freq.most_common(20)
                                if w.lower() not in stopwords and len(w) >= 2]
                    top_words = [w for w, _ in filtered[:3]]
                    community_labels[str(cid)] = " · ".join(top_words) if top_words else f"社群 {cid}"
                else:
                    community_labels[str(cid)] = f"社群 {cid}"
        except Exception:
            for cid in set(partition.values()):
                community_labels[str(cid)] = f"社群 {cid}"

        # 5. 組裝 Nodes
        nodes_data = []
        for idx, s in enumerate(summaries):
            pr = pagerank.get(idx, 0.0)
            cluster_id = partition.get(idx, 0)
            title = s.get("title", "")
            nodes_data.append({
                "id": idx,
                "label": title[:22] + "..." if len(title) > 22 else title,
                "title": title,
                "authors": ", ".join(s.get("authors", [])) if isinstance(s.get("authors", []), list) else str(s.get("authors", "")),
                "year": s.get("year") or "未知",
                "pagerank": pr,
                "group": cluster_id,
                "details": {
                    "research_goal": s.get("research_goal", "無"),
                    "main_findings": s.get("main_findings", "無"),
                    "limitations": s.get("limitations", "無")
                }
            })

        return {"nodes": nodes_data, "edges": edges_data, "count": len(summaries), "community_labels": community_labels}
