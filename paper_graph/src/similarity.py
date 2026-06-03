from typing import Tuple, List, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class SimilarityCalculator:
    def __init__(self, threshold: float = 0.65, top_k: int = 20):
        self.threshold = threshold
        self.top_k = top_k

    def calculate_similarities(self, embeddings: np.ndarray) -> List[Tuple[int, int, float]]:
        """
        Calculates similarity edges. Returns list of tuples (idx_i, idx_j, similarity).
        If number of embeddings >= 10000, it uses FAISS for optimization.
        Otherwise it uses O(N^2) cosine similarity with threshold and top_k pruning.
        """
        n = len(embeddings)
        edges = []

        if n >= 10000:
            # Optimize using FAISS
            import faiss
            # Normalize embeddings to unit length for cosine similarity (Inner Product index)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            normalized_embeddings = embeddings / norms

            dim = normalized_embeddings.shape[1]
            # Use IndexFlatIP for exact top-K search or IndexHNSWFlat for extreme performance
            # IndexFlatIP is fine for 10k-50k; we can use IndexFlatIP or HNSW. Let's use IndexFlatIP
            index = faiss.IndexFlatIP(dim)
            index.add(normalized_embeddings.astype('float32'))

            # Search top_k + 1 (since the paper itself will be the nearest neighbor)
            k_search = min(n, self.top_k + 1)
            similarities, indices = index.search(normalized_embeddings.astype('float32'), k_search)

            for i in range(n):
                for rank in range(k_search):
                    j = int(indices[i, rank])
                    sim = float(similarities[i, rank])
                    if i < j:  # Undirected graph: add edge only once
                        if sim > self.threshold:
                            edges.append((i, j, sim))
        else:
            # Standard O(N^2) cosine similarity
            sim_matrix = cosine_similarity(embeddings)
            for i in range(n):
                # Find top K indices for paper i (excluding itself)
                peer_indices = np.argsort(sim_matrix[i])[::-1]
                # Filter indices
                count = 0
                for j in peer_indices:
                    if i == j:
                        continue
                    sim = float(sim_matrix[i, j])
                    if sim <= self.threshold or count >= self.top_k:
                        break
                    if i < j:
                        edges.append((i, j, sim))
                    count += 1

        return edges
