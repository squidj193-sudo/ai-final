import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pyvis.network import Network
import community as community_louvain
import jieba
import re
import logging

# Disable jieba default console output logging to keep terminal output clean
jieba.setLogLevel(logging.WARNING)

def ch_en_tokenizer(text):
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
    def generate_graph_html(self, summaries: list) -> str:
        """
        Generates an interactive PyVis HTML representation of the session's papers.
        """
        if not summaries:
            return "<h3>目前尚無已分析的論文，請先在「對話搜尋」上傳 PDF 或搜尋分析論文。</h3>"

        G = nx.Graph()

        # Add nodes
        for idx, s in enumerate(summaries):
            title = s.get("title", "")
            authors = s.get("authors", [])
            authors_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
            year = s.get("year") or "未知"
            paper_id = s.get("paper_id", "")
            
            # Combine text for similarity
            goal = s.get("research_goal", "")
            findings = s.get("main_findings", "")
            keywords = s.get("keywords", [])
            keywords_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            combined_text = f"{title} {keywords_str} {goal} {findings}"
            
            G.add_node(
                idx,
                title=title,
                authors=authors_str,
                year=year,
                paper_id=paper_id,
                combined_text=combined_text
            )

        # Compute TF-IDF similarities to build edges if > 1 node
        if len(summaries) > 1:
            corpus = [G.nodes[i]["combined_text"] for i in range(len(summaries))]
            try:
                vectorizer = TfidfVectorizer(tokenizer=ch_en_tokenizer, token_pattern=None)
                tfidf = vectorizer.fit_transform(corpus)
                sim_matrix = cosine_similarity(tfidf)
                
                # Find maximum similarity value in the matrix to decide a dynamic threshold
                max_sim = 0.0
                for i in range(len(summaries)):
                    for j in range(i + 1, len(summaries)):
                        max_sim = max(max_sim, float(sim_matrix[i, j]))
                
                # Dynamic threshold: pre-selected 0.12 or 70% of max similarity if it's too low
                threshold = min(0.12, max_sim * 0.75) if max_sim > 0.05 else 0.12
                
                # Add edges above threshold
                for i in range(len(summaries)):
                    for j in range(i + 1, len(summaries)):
                        sim = float(sim_matrix[i, j])
                        if sim >= threshold:
                            G.add_edge(i, j, weight=sim)
                
                # Ensure every node has at least one connection to its most similar peer (if any similarity > 0.02)
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
                print(f"Error computing session paper similarity: {e}")

        # PageRank & Centrality
        try:
            pagerank = nx.pagerank(G, weight="weight")
        except Exception:
            pagerank = {n: 1.0/len(G) for n in G.nodes()}

        # Community Detection
        try:
            partition = community_louvain.best_partition(G)
        except Exception:
            partition = {n: 0 for n in G.nodes()}

        # Generate PyVis Network
        net = Network(height="650px", width="100%", bgcolor="#1e1e24", font_color="white")
        
        colors = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', 
                  '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac']

        # Add nodes to PyVis
        for node in G.nodes():
            title = G.nodes[node]["title"]
            authors = G.nodes[node]["authors"]
            year = G.nodes[node]["year"]
            pr = pagerank.get(node, 0.0)
            cluster_id = partition.get(node, 0)
            color = colors[cluster_id % len(colors)]

            tooltip = (
                f"<div style='color: black; font-family: sans-serif; padding: 5px;'>"
                f"<b>標題:</b> {title}<br>"
                f"<b>作者:</b> {authors}<br>"
                f"<b>年份:</b> {year}<br>"
                f"<b>影響力 (PageRank):</b> {pr:.4f}<br>"
                f"</div>"
            )

            # Node size based on PageRank
            size = float(pr * 80 + 15)

            net.add_node(
                node,
                label=title[:30] + "..." if len(title) > 30 else title,
                title=tooltip,
                size=size,
                color=color,
                group=cluster_id,
                shape="dot"
            )

        # Add edges to PyVis
        for u, v, data in G.edges(data=True):
            weight = data.get("weight", 1.0)
            net.add_edge(u, v, value=float(weight))

        net.toggle_physics(True)
        net.set_options("""
        var options = {
          "nodes": {
            "font": {
              "size": 13,
              "color": "#ffffff",
              "strokeWidth": 3,
              "strokeColor": "#1e1e24",
              "face": "system-ui, -apple-system, sans-serif"
            }
          },
          "edges": {
            "color": {
              "color": "rgba(129, 140, 248, 0.4)",
              "highlight": "rgba(129, 140, 248, 0.8)",
              "hover": "rgba(129, 140, 248, 0.8)"
            },
            "smooth": {
              "type": "continuous"
            }
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -4000,
              "centralGravity": 0.15,
              "springLength": 180,
              "springConstant": 0.05
            },
            "solver": "barnesHut"
          }
        }
        """)

        # Return HTML raw string
        html = net.generate_html()
        
        # Inject style in head to remove margins and scrollbars
        custom_css = """
        <style>
        body, html {
          margin: 0 !important;
          padding: 0 !important;
          overflow: hidden !important;
          width: 100% !important;
          height: 100% !important;
          background-color: #1e1e24 !important;
        }
        #mynetwork {
          width: 100% !important;
          height: 100vh !important;
          border: none !important;
        }
        </style>
        </head>
        """
        html = html.replace("</head>", custom_css)
        return html

    def compute_graph_metrics(self, summaries: list) -> dict:
        """
        計算圖的 PageRank (核心論文重要度)、Betweenness Centrality (跨流派樞紐)、與 Louvain 社群 (技術流派)
        """

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

        # 4.5 為每個社群產生代表性標籤（從該群組論文的合併文本中萃取 TF-IDF 最高的關鍵字）
        community_labels = {}
        try:
            # 按群組收集論文的 combined_text
            group_texts = {}
            for idx in range(len(summaries)):
                cid = partition.get(idx, 0)
                if cid not in group_texts:
                    group_texts[cid] = []
                group_texts[cid].append(G.nodes[idx]["combined_text"])
            
            for cid, texts in group_texts.items():
                merged = " ".join(texts)
                tokens = ch_en_tokenizer(merged)
                if tokens:
                    # 用詞頻取前 2~3 個高頻詞作為社群標籤
                    from collections import Counter
                    freq = Counter(tokens)
                    # 過濾掉太短或太通用的詞
                    stopwords = {"the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "has", "have", "been", "not", "but", "can", "also", "will", "our", "their", "which", "based", "using", "used", "results", "study", "research", "paper", "method", "approach", "proposed", "show", "than", "more", "most", "one", "two"}
                    filtered = [(w, c) for w, c in freq.most_common(20) if w.lower() not in stopwords and len(w) >= 2]
                    top_words = [w for w, _ in filtered[:3]]
                    community_labels[cid] = " / ".join(top_words) if top_words else f"社群 {cid}"
                else:
                    community_labels[cid] = f"社群 {cid}"
        except Exception:
            for cid in set(partition.values()):
                community_labels[cid] = f"社群 {cid}"

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
