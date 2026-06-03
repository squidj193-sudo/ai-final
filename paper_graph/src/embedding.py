import os
from typing import List, Dict
import numpy as np

class PaperEmbedder:
    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        # We import here to delay load times if needed
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_papers(self, papers: List[Dict]) -> np.ndarray:
        """
        Embeds a list of papers by concatenating title, keywords, and abstract.
        Each paper dict is expected to have 'title', 'keywords', 'abstract'.
        """
        texts = []
        for paper in papers:
            title = paper.get("title", "")
            keywords = paper.get("keywords", [])
            keywords_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            abstract = paper.get("abstract", "")
            # Combine text fields
            doc_text = f"{title} {keywords_str} {abstract}"
            texts.append(doc_text)

        embeddings = self.model.encode(
            texts, 
            show_progress_bar=True, 
            convert_to_numpy=True
        )
        return embeddings
