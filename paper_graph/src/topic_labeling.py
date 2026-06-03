from typing import List, Dict
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import networkx as nx

class TopicLabeler:
    @staticmethod
    def label_clusters(G: nx.Graph, papers: List[Dict]) -> nx.Graph:
        """
        Extracts key terms from the papers in each cluster using TF-IDF
        and names the cluster based on those key terms.
        Adds 'cluster_name' to node attributes.
        """
        # Group papers by cluster
        cluster_docs = {}
        for idx, paper in enumerate(papers):
            cluster_id = G.nodes[idx].get("cluster_id", 0)
            
            title = paper.get("title", "")
            keywords = " ".join(paper.get("keywords", [])) if isinstance(paper.get("keywords"), list) else str(paper.get("keywords", ""))
            abstract = paper.get("abstract", "")
            combined_text = f"{title} {keywords} {abstract}"
            
            if cluster_id not in cluster_docs:
                cluster_docs[cluster_id] = []
            cluster_docs[cluster_id].append(combined_text)

        # Calculate TF-IDF for each cluster
        cluster_ids = list(cluster_docs.keys())
        corpus = [" ".join(cluster_docs[cid]) for cid in cluster_ids]

        if not corpus:
            return G

        # Simple TF-IDF Vectorizer
        vectorizer = TfidfVectorizer(max_features=2000, stop_words="english")
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()

            # Assign topic names to each cluster
            cluster_names = {}
            for i, cid in enumerate(cluster_ids):
                row = tfidf_matrix.getrow(i).toarray()[0]
                top_indices = row.argsort()[::-1][:3]  # Take top 3 words
                top_words = [feature_names[idx] for idx in top_indices]
                # Capitalize words and join them
                topic_name = " & ".join([w.capitalize() for w in top_words if row[idx] > 0])
                if not topic_name:
                    topic_name = f"Cluster {cid}"
                cluster_names[cid] = topic_name
        except Exception as e:
            print(f"Error calculating TF-IDF: {e}")
            cluster_names = {cid: f"Cluster {cid}" for cid in cluster_ids}

        # Apply back to graph nodes
        for node in G.nodes():
            cid = G.nodes[node].get("cluster_id", 0)
            G.nodes[node]["cluster_name"] = cluster_names.get(cid, f"Cluster {cid}")

        return G
