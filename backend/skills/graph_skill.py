import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pyvis.network import Network
import community as community_louvain

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
                vectorizer = TfidfVectorizer(stop_words="english")
                tfidf = vectorizer.fit_transform(corpus)
                sim_matrix = cosine_similarity(tfidf)
                
                # Add edges
                for i in range(len(summaries)):
                    for j in range(i + 1, len(summaries)):
                        sim = float(sim_matrix[i, j])
                        if sim > 0.15:  # Lower threshold for local session papers
                            G.add_edge(i, j, weight=sim)
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
                group=cluster_id
            )

        # Add edges to PyVis
        for u, v, data in G.edges(data=True):
            weight = data.get("weight", 1.0)
            net.add_edge(u, v, value=float(weight))

        net.toggle_physics(True)
        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -2000,
              "centralGravity": 0.3,
              "springLength": 95,
              "springConstant": 0.04
            },
            "solver": "barnesHut"
          }
        }
        """)

        # Return HTML raw string
        return net.generate_html()
