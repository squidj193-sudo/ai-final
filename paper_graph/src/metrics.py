import networkx as nx

class NetworkMetricsCalculator:
    @staticmethod
    def calculate_metrics(G: nx.Graph) -> nx.Graph:
        """
        Calculates PageRank, Betweenness Centrality, and Eigenvector Centrality.
        Adds metrics directly as node attributes.
        """
        # PageRank
        try:
            pagerank = nx.pagerank(G, weight="weight")
        except Exception:
            pagerank = {node: 1.0/len(G) for node in G.nodes()}

        # Betweenness Centrality
        try:
            # For performance, we can approximate it on huge graphs or compute directly
            betweenness = nx.betweenness_centrality(G, weight="weight")
        except Exception:
            betweenness = {node: 0.0 for node in G.nodes()}

        # Eigenvector Centrality
        try:
            eigenvector = nx.eigenvector_centrality_numpy(G, weight="weight")
        except Exception:
            eigenvector = {node: 0.0 for node in G.nodes()}

        # Apply to node attributes
        for node in G.nodes():
            G.nodes[node]["pagerank"] = pagerank.get(node, 0.0)
            G.nodes[node]["betweenness_centrality"] = betweenness.get(node, 0.0)
            G.nodes[node]["eigenvector_centrality"] = eigenvector.get(node, 0.0)

        return G
