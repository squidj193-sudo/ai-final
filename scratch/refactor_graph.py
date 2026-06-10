# -*- coding: utf-8 -*-
from pathlib import Path

file_path = Path("backend/skills/graph_skill.py")
content = file_path.read_text(encoding="utf-8")

# Let's replace the top imports with a simple log/re setup
old_top = """import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pyvis.network import Network
import community as community_louvain
import jieba
import re
import logging

# Disable jieba default console output logging to keep terminal output clean
jieba.setLogLevel(logging.WARNING)"""

new_top = """import re
import logging

# Lazy-loaded modules will be imported inside functions to speed up AgentCore startup time"""

content = content.replace(old_top, new_top)

# Update ch_en_tokenizer to lazy import jieba
old_tokenizer = """def ch_en_tokenizer(text):
    if not text:
        return []
    words = jieba.lcut(text.lower())"""

new_tokenizer = """def ch_en_tokenizer(text):
    import jieba
    jieba.setLogLevel(logging.WARNING)
    if not text:
        return []
    words = jieba.lcut(text.lower())"""

content = content.replace(old_tokenizer, new_tokenizer)

# Update SessionGraphSkill methods to lazy import numpy, networkx, TfidfVectorizer, cosine_similarity, Network, community_louvain
old_generate = """    def generate_graph_html(self, summaries: list) -> str:
        \"\"\"
        Generates an interactive PyVis HTML representation of the session's papers.
        \"\"\"
        if not summaries:
            return "<h3>目前尚無已分析的論文，請先在「對話搜尋」上傳 PDF 或搜尋分析論文。</h3>"

        G = nx.Graph()"""

new_generate = """    def generate_graph_html(self, summaries: list) -> str:
        \"\"\"
        Generates an interactive PyVis HTML representation of the session's papers.
        \"\"\"
        import networkx as nx
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        from pyvis.network import Network
        import community as community_louvain

        if not summaries:
            return "<h3>目前尚無已分析的論文，請先在「對話搜尋」上傳 PDF 或搜尋分析論文。</h3>"

        G = nx.Graph()"""

content = content.replace(old_generate, new_generate)

# Update compute_graph_metrics
old_metrics = """    def compute_graph_metrics(self, summaries: list) -> dict:
        \"\"\"
        計算圖的 PageRank (核心論文重要度)、Betweenness Centrality (跨流派樞紐)、與 Louvain 社群 (技術流派)
        \"\"\"

        if not summaries:
            return {"influence": [], "communities": {}, "bridges": []}

        G = nx.Graph()"""

new_metrics = """    def compute_graph_metrics(self, summaries: list) -> dict:
        \"\"\"
        計算圖的 PageRank (核心論文重要度)、Betweenness Centrality (跨流派樞紐)、與 Louvain 社群 (技術流派)
        \"\"\"
        import networkx as nx
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import community as community_louvain

        if not summaries:
            return {"influence": [], "communities": {}, "bridges": []}

        G = nx.Graph()"""

content = content.replace(old_metrics, new_metrics)

# Update get_graph_data
old_graph_data = """    def get_graph_data(self, summaries: list) -> dict:
        \"\"\"
        計算並回傳論文知識圖譜的 Nodes 與 Edges 結構化 JSON 資料
        \"\"\"
        if not summaries:
            return {"nodes": [], "edges": [], "count": 0}

        # 1. 建立 NetworkX Graph
        G = nx.Graph()"""

new_graph_data = """    def get_graph_data(self, summaries: list) -> dict:
        \"\"\"
        計算並回傳論文知識圖譜的 Nodes 與 Edges 結構化 JSON 資料
        \"\"\"
        import networkx as nx
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import community as community_louvain

        if not summaries:
            return {"nodes": [], "edges": [], "count": 0}

        # 1. 建立 NetworkX Graph
        G = nx.Graph()"""

content = content.replace(old_graph_data, new_graph_data)

file_path.write_text(content, encoding="utf-8")
print("GraphSkill refactored successfully.")
