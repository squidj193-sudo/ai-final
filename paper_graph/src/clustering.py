import networkx as nx

class CommunityDetector:
    @staticmethod
    def detect_communities(G: nx.Graph) -> nx.Graph:
        """
        Detects communities using Leiden algorithm with Louvain fallback.
        Adds 'cluster_id' to node attributes.
        """
        # Try Leiden clustering first
        try:
            import igraph as ig
            import leidenalg

            # Convert networkx graph to igraph
            # Create mapping
            nodes_list = list(G.nodes())
            mapping = {node: idx for idx, node in enumerate(nodes_list)}
            inv_mapping = {idx: node for idx, node in enumerate(nodes_list)}

            ig_graph = ig.Graph(directed=False)
            ig_graph.add_vertices(len(nodes_list))
            
            edges = []
            weights = []
            for u, v, data in G.edges(data=True):
                edges.append((mapping[u], mapping[v]))
                weights.append(data.get("weight", 1.0))

            ig_graph.add_edges(edges)
            ig_graph.es["weight"] = weights

            # Run Leiden partitioning
            partition = leidenalg.find_partition(
                ig_graph, 
                leidenalg.ModularityVertexPartition, 
                weights="weight"
            )

            # Assign cluster IDs back to networkx nodes
            for cluster_idx, community in enumerate(partition):
                for node_idx in community:
                    orig_node = inv_mapping[node_idx]
                    G.nodes[orig_node]["cluster_id"] = cluster_idx

        except ImportError:
            # Fallback to Louvain clustering
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G, weight="weight")
                for node, cluster_id in partition.items():
                    G.nodes[node]["cluster_id"] = cluster_id
            except ImportError:
                # If everything fails, assign all nodes to a single cluster
                print("Warning: Neither leidenalg nor python-louvain packages are available. Assigning default cluster 0.")
                for node in G.nodes():
                    G.nodes[node]["cluster_id"] = 0

        return G
