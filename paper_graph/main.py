import os
import json
import random
import pandas as pd
import numpy as np
import networkx as nx

from src.embedding import PaperEmbedder
from src.similarity import SimilarityCalculator
from src.graph_builder import GraphBuilder
from src.clustering import CommunityDetector
from src.topic_labeling import TopicLabeler
from src.metrics import NetworkMetricsCalculator
from src.visualization import GraphVisualizer

def generate_mock_dataset(file_path: str, count: int = 1000):
    """
    Generates a realistic mock papers dataset of 'count' papers to ensure
    the system runs out-of-the-box.
    """
    print(f"Generating mock dataset of {count} papers...")
    
    topics = [
        {
            "name": "Machine Learning",
            "keywords": ["neural network", "deep learning", "supervised learning", "transformer", "gradient descent"],
            "verbs": ["implements", "optimizes", "proposes", "analyzes", "evaluates"],
            "nouns": ["transformer model", "loss function", "optimization algorithm", "classification accuracy", "representation learning"]
        },
        {
            "name": "Quantum Computing",
            "keywords": ["quantum gate", "qubit", "entanglement", "quantum algorithm", "superconductivity"],
            "verbs": ["demonstrates", "proves", "simulates", "constructs", "entangles"],
            "nouns": ["quantum supremacy", "error correction", "superconducting qubit", "quantum teleportation", "decoherence rate"]
        },
        {
            "name": "Bioinformatics",
            "keywords": ["gene sequencing", "protein folding", "genomics", "alignment", "phylogenetic tree"],
            "verbs": ["identifies", "sequences", "predicts", "aligns", "characterizes"],
            "nouns": ["genomic mutation", "amino acid sequence", "cellular pathway", "phylogenetic analysis", "structural model"]
        },
        {
            "name": "Renewable Energy",
            "keywords": ["solar cell", "wind turbine", "battery storage", "photovoltaic", "grid stability"],
            "verbs": ["improves", "harnesses", "stabilizes", "converts", "designs"],
            "nouns": ["conversion efficiency", "perovskite material", "lithium-ion battery", "grid integration", "energy harvest"]
        },
        {
            "name": "Medical AI",
            "keywords": ["clinical diagnosis", "medical imaging", "patient care", "lesion detection", "radiology"],
            "verbs": ["diagnoses", "detects", "segments", "classifies", "assists"],
            "nouns": ["MRI scan", "tumor classification", "deep learning system", "diagnostic sensitivity", "radiomics feature"]
        }
    ]

    first_names = ["Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    last_names = ["Smith", "Jones", "Taylor", "Wang", "Li", "Zhang", "Chen", "Kim", "Miller", "Davis"]

    papers_data = []
    
    for i in range(count):
        paper_id = f"paper_{i:04d}"
        topic = random.choice(topics)
        
        # Build Title
        verb = random.choice(topic["verbs"])
        noun = random.choice(topic["nouns"])
        kw = random.choice(topic["keywords"])
        title = f"{verb.capitalize()} {noun} for Enhanced {kw.capitalize()}"
        
        # Build Abstract
        abstract = (
            f"In this paper, we {verb} a new approach targeting {noun} "
            f"specifically optimized for {kw} applications. Our methodology leverages state-of-the-art "
            f"techniques in the field of {topic['name']}. Experimental results indicate that our system "
            f"outperforms baseline measures significantly by achieving higher efficiency."
        )
        
        # Random parameters
        year = random.randint(2015, 2026)
        citation_count = int(random.expovariate(1 / 15))  # exponential distribution of citations
        
        # Authors
        num_authors = random.randint(1, 4)
        authors = [f"{random.choice(first_names)} {random.choice(last_names)}" for _ in range(num_authors)]
        authors = list(set(authors))  # Deduplicate
        
        # Keywords
        num_keywords = random.randint(2, 5)
        keywords = list(set(random.sample(topic["keywords"] + [topic["name"].lower()], num_keywords)))
        
        # References
        num_refs = random.randint(2, 10)
        references = [f"paper_{random.randint(0, count-1):04d}" for _ in range(num_refs)]
        # Filter out self-referencing
        references = [ref for ref in references if ref != paper_id]

        papers_data.append({
            "paper_id": paper_id,
            "title": title,
            "abstract": abstract,
            "keywords": keywords,
            "authors": authors,
            "year": year,
            "citation_count": citation_count,
            "references": references
        })

    # Save to data directory
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save CSV
    df = pd.DataFrame(papers_data)
    # Convert lists to JSON string format for easy serialization in CSV
    df["keywords"] = df["keywords"].apply(json.dumps)
    df["authors"] = df["authors"].apply(json.dumps)
    df["references"] = df["references"].apply(json.dumps)
    df.to_csv(file_path, index=False, encoding="utf-8")
    print(f"Mock dataset saved to {file_path}")


def load_papers(file_path: str) -> list:
    """
    Loads papers from CSV and deserializes lists.
    """
    df = pd.read_csv(file_path)
    papers = []
    for _, row in df.iterrows():
        papers.append({
            "paper_id": row["paper_id"],
            "title": row["title"],
            "abstract": row["abstract"],
            "keywords": json.loads(row["keywords"]),
            "authors": json.loads(row["authors"]),
            "year": int(row["year"]),
            "citation_count": int(row["citation_count"]),
            "references": json.loads(row["references"])
        })
    return papers


def main():
    csv_path = "./paper_graph/data/papers.csv"
    
    # Generate mock data if file not present
    if not os.path.exists(csv_path):
        generate_mock_dataset(csv_path, count=1000)

    print("Loading paper data...")
    papers = load_papers(csv_path)
    print(f"Loaded {len(papers)} papers.")

    # 1. Compute Embeddings
    print("Step 1: Encoding papers into vector embeddings using SentenceTransformers...")
    embedder = PaperEmbedder(model_name="all-mpnet-base-v2")
    embeddings = embedder.embed_papers(papers)
    print(f"Generated embeddings shape: {embeddings.shape}")

    # 2. Similarity Calculation
    print("Step 2: Calculating cosine similarity graph edges...")
    calculator = SimilarityCalculator(threshold=0.65, top_k=20)
    edges = calculator.calculate_similarities(embeddings)
    print(f"Created {len(edges)} weighted edges.")

    # 3. Build Graph
    print("Step 3: Building networkx graph...")
    G = GraphBuilder.build_graph(papers, edges)

    # 4. Community Detection
    print("Step 4: Detecting communities...")
    G = CommunityDetector.detect_communities(G)

    # 5. Topic Labeling
    print("Step 5: Labeling clusters...")
    G = TopicLabeler.label_clusters(G, papers)

    # 6. Centrality/PageRank Metrics
    print("Step 6: Calculating network metrics...")
    G = NetworkMetricsCalculator.calculate_metrics(G)

    # 7. Exports
    print("Step 7: Saving output files...")
    output_dir = "./paper_graph/output"
    os.makedirs(output_dir, exist_ok=True)

    # Export CSV Clusters
    cluster_records = []
    for node in G.nodes():
        cluster_records.append({
            "paper_id": G.nodes[node]["paper_id"],
            "title": G.nodes[node]["title"],
            "cluster_id": G.nodes[node]["cluster_id"],
            "cluster_name": G.nodes[node]["cluster_name"],
            "pagerank": G.nodes[node]["pagerank"],
            "citation_count": G.nodes[node]["citation_count"]
        })
    pd.DataFrame(cluster_records).to_csv(f"{output_dir}/clusters.csv", index=False, encoding="utf-8")

    # Export GraphML
    nx.write_graphml(G, f"{output_dir}/graph.graphml")
    # Export GEXF
    nx.write_gexf(G, f"{output_dir}/graph.gexf")
    # Export JSON
    with open(f"{output_dir}/graph.json", "w", encoding="utf-8") as f:
        json.dump(nx.readwrite.json_graph.node_link_data(G), f, ensure_ascii=False, indent=2)

    # 8. Visualizations
    print("Step 8: Generating graph layouts & HTML visualizations...")
    pos = GraphVisualizer.calculate_layout(G)
    GraphVisualizer.visualize_plotly(G, pos, f"{output_dir}/graph_plotly.html")
    GraphVisualizer.visualize_pyvis(G, f"{output_dir}/graph.html")

    print("\nPipeline execution complete! Output files generated:")
    print(f"- Metadata Clusters: {output_dir}/clusters.csv")
    print(f"- Network files: {output_dir}/graph.graphml, {output_dir}/graph.gexf, {output_dir}/graph.json")
    print(f"- Interactive Visualizations: {output_dir}/graph_plotly.html, {output_dir}/graph.html")


if __name__ == "__main__":
    main()
