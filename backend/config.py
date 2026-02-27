"""
Application configuration — reads from environment variables with sensible defaults.
"""

import os
from enum import Enum


class GraphBackend(str, Enum):
    NEO4J = "neo4j"
    NETWORKX = "networkx"
    NEPTUNE = "neptune"
    ARANGO = "arango"


# Which adapter to use — set via GRAPH_BACKEND env var
GRAPH_BACKEND: GraphBackend = GraphBackend(
    os.getenv("GRAPH_BACKEND", "networkx")
)

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gst-graph-2024")

# Neptune (stub)
NEPTUNE_ENDPOINT = os.getenv("NEPTUNE_ENDPOINT", "")

# ArangoDB (stub)
ARANGO_URL = os.getenv("ARANGO_URL", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "gst_graph")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")

# Data paths
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

# CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://localhost:80"
).split(",")
