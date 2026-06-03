from typing import List, Dict, Tuple
import networkx as nx

class GraphBuilder:
    @staticmethod
    def build_graph(papers: List[Dict], edges: List[Tuple[int, int, float]]) -> nx.Graph:
        """
        Builds a networkx weighted graph.
        """
        G = nx.Graph()

        # Add nodes with attributes
        for idx, paper in enumerate(papers):
            G.add_node(
                idx,
                paper_id=paper.get("paper_id", ""),
                title=paper.get("title", ""),
                authors="; ".join(paper.get("authors", [])) if isinstance(paper.get("authors"), list) else str(paper.get("authors", "")),
                year=paper.get("year", 0),
                citation_count=paper.get("citation_count", 0),
                keywords="; ".join(paper.get("keywords", [])) if isinstance(paper.get("keywords"), list) else str(paper.get("keywords", ""))
            )

        # Add edges
        for u, v, weight in edges:
            G.add_edge(u, v, weight=weight)

        return G
