import os
import networkx as nx
import numpy as np
import plotly.graph_objects as go
from pyvis.network import Network

class GraphVisualizer:
    @staticmethod
    def calculate_layout(G: nx.Graph) -> dict:
        """
        Calculates spring layout position for all nodes.
        Edges with higher weight (similarity) will attract nodes closer.
        """
        # spring_layout behaves nicely with weight. Higher weight -> stronger pull.
        pos = nx.spring_layout(G, weight="weight", seed=42)
        return pos

    @classmethod
    def visualize_plotly(cls, G: nx.Graph, pos: dict, output_path: str):
        """
        Generates an interactive Plotly HTML visualization.
        """
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        node_x = []
        node_y = []
        node_text = []
        node_size = []
        node_color = []

        # Color palette for clusters
        colors = ['#1f77b4', '#2ca02c', '#d62728', '#ff7f0e', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Retrieve node attributes
            title = G.nodes[node].get("title", "")
            authors = G.nodes[node].get("authors", "")
            year = G.nodes[node].get("year", "")
            citation_count = G.nodes[node].get("citation_count", 0)
            cluster_id = G.nodes[node].get("cluster_id", 0)
            cluster_name = G.nodes[node].get("cluster_name", f"Cluster {cluster_id}")
            
            # Hover text
            hover_text = (
                f"<b>Title:</b> {title}<br>"
                f"<b>Authors:</b> {authors}<br>"
                f"<b>Year:</b> {year}<br>"
                f"<b>Citations:</b> {citation_count}<br>"
                f"<b>Cluster:</b> {cluster_name}"
            )
            node_text.append(hover_text)
            
            # Size proportional to log(citation_count + 1)
            size = int(np.log1p(citation_count) * 6 + 6)
            node_size.append(size)
            
            # Color by cluster
            color_idx = cluster_id % len(colors)
            node_color.append(colors[color_idx])

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                showscale=False,
                color=node_color,
                size=node_size,
                line_width=1
            )
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title='Academic Paper Knowledge Graph',
                titlefont_size=16,
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                template='plotly_dark'
            )
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.write_html(output_path)

    @classmethod
    def visualize_pyvis(cls, G: nx.Graph, output_path: str):
        """
        Generates an interactive PyVis HTML visualization network.
        """
        # Initialize pyvis network
        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
        
        # Color palette for clusters
        colors = ['#1f77b4', '#2ca02c', '#d62728', '#ff7f0e', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        # Add nodes
        for node in G.nodes():
            title = G.nodes[node].get("title", "")
            authors = G.nodes[node].get("authors", "")
            year = G.nodes[node].get("year", "")
            citation_count = G.nodes[node].get("citation_count", 0)
            cluster_id = G.nodes[node].get("cluster_id", 0)
            cluster_name = G.nodes[node].get("cluster_name", f"Cluster {cluster_id}")
            pagerank = G.nodes[node].get("pagerank", 0.0)

            # Node size: based on log scale citations
            node_size = float(np.log1p(citation_count) * 8 + 8)
            
            # Hover title (HTML formatted)
            tooltip = (
                f"<div style='color: black;'>"
                f"<b>Title:</b> {title}<br>"
                f"<b>Authors:</b> {authors}<br>"
                f"<b>Year:</b> {year}<br>"
                f"<b>Citations:</b> {citation_count}<br>"
                f"<b>PageRank:</b> {pagerank:.5f}<br>"
                f"<b>Cluster:</b> {cluster_name}"
                f"</div>"
            )

            color_idx = cluster_id % len(colors)
            node_color = colors[color_idx]

            net.add_node(
                node,
                label=title[:30] + "..." if len(title) > 30 else title,
                title=tooltip,
                size=node_size,
                color=node_color,
                group=cluster_id
            )

        # Add edges
        for u, v, data in G.edges(data=True):
            weight = data.get("weight", 1.0)
            # Threshold representation for visualization
            net.add_edge(u, v, value=float(weight))

        # Set physics to avoid layout explosion
        net.toggle_physics(True)
        net.set_options("""
        var options = {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
              "iterations": 150
            }
          }
        }
        """)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        net.write_html(output_path)
