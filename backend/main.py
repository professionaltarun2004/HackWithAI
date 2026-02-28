"""
GST Graph Reconciliation — FastAPI entry point.

Initialises the chosen graph adapter, loads data, and mounts all API routes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    GRAPH_BACKEND,
    GraphBackend,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEPTUNE_ENDPOINT,
    ARANGO_URL,
    ARANGO_DB,
    ARANGO_USER,
    ARANGO_PASSWORD,
    DATA_DIR,
    UPLOADS_DATA_DIR,
    CORS_ORIGINS,
)
from .adapters import (
    NetworkXAdapter,
    Neo4jAdapter,
    NeptuneAdapter,
    ArangoAdapter,
)
from .services.ingestion import load_csv
from .api import routes

logger = logging.getLogger("gst-graph")


def _create_adapter():
    """Factory: build the right adapter based on GRAPH_BACKEND env var."""
    if GRAPH_BACKEND == GraphBackend.NEO4J:
        return Neo4jAdapter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    elif GRAPH_BACKEND == GraphBackend.NEPTUNE:
        return NeptuneAdapter(NEPTUNE_ENDPOINT)
    elif GRAPH_BACKEND == GraphBackend.ARANGO:
        return ArangoAdapter(ARANGO_URL, ARANGO_DB, ARANGO_USER, ARANGO_PASSWORD)
    else:
        return NetworkXAdapter()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: connect adapter, create constraints, load seed data."""
    adapter = _create_adapter()
    adapter.connect()
    adapter.create_constraints()

    # Auto-load seed data if the graph is empty
    summary = adapter.get_graph_summary()
    if summary.get("vendor_count", 0) == 0:
        logger.info("Graph is empty — loading seed data from %s", DATA_DIR)
        v, i = load_csv(DATA_DIR, adapter)
        logger.info("Loaded %d vendors, %d invoices", v, i)

    # Re-apply any previously uploaded CSVs (survives server restarts)
    import os, glob
    upload_files = glob.glob(os.path.join(UPLOADS_DATA_DIR, "*.csv"))
    if upload_files:
        logger.info("Re-applying uploaded CSVs from %s", UPLOADS_DATA_DIR)
        v2, i2 = load_csv(UPLOADS_DATA_DIR, adapter)
        logger.info("Appended %d vendors, %d invoices from uploads", v2, i2)

    # Inject adapter into routes module
    routes.adapter = adapter
    application.state.adapter = adapter

    yield

    adapter.close()


app = FastAPI(
    title="GST Graph Risk API",
    description="Intelligent GST Reconciliation using Knowledge Graphs",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
