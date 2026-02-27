# Intelligent GST Reconciliation using Knowledge Graphs

A production-ready architecture for GST invoice reconciliation using graph databases, with multi-adapter support for **Neo4j** (primary), **NetworkX** (in-memory fallback), and stubs for **Amazon Neptune** and **ArangoDB**.

## Architecture

```
┌─────────────────┐     REST API      ┌──────────────────────────────────┐
│  React Dashboard │ ◄──────────────► │  FastAPI Backend                 │
│  (Vite + D3.js)  │                  │                                  │
└─────────────────┘                   │  ┌────────────────────────────┐  │
                                      │  │  GraphAdapter (ABC)        │  │
                                      │  │  ├─ Neo4jAdapter (Cypher)  │  │
                                      │  │  ├─ NetworkXAdapter (mem)  │  │
                                      │  │  ├─ NeptuneAdapter (stub)  │  │
                                      │  │  └─ ArangoAdapter  (stub)  │  │
                                      │  └────────────────────────────┘  │
                                      │                                  │
                                      │  Services:                       │
                                      │  ├─ Ingestion (CSV → Graph)     │
                                      │  ├─ Reconciliation Engine       │
                                      │  ├─ Risk Scoring (0-100)        │
                                      │  └─ Audit Trail Generator       │
                                      └──────────────────────────────────┘
                                                    │
                                      ┌─────────────┴────────────┐
                                      │  Neo4j (Docker)          │
                                      │  Knowledge Graph:        │
                                      │  Vendor ─SOLD─► Invoice  │
                                      │  Invoice ─PURCHASED_BY─► │
                                      │  Vendor ─FILED─► Return  │
                                      │  Return ─REPORTS/CLAIMS─►│
                                      └──────────────────────────┘
```

## Graph Schema

| Node     | Properties                                      | Description        |
|----------|------------------------------------------------|--------------------|
| Vendor   | gstin, name, missed_filings                     | Taxpayer / GSTIN   |
| Invoice  | invoice_id, seller_gstin, buyer_gstin, amount, tax, reported_by_seller, claimed_by_buyer | Transaction |
| Return   | id, type (GSTR-1 / GSTR-2B)                    | GST Return filing  |

| Relationship | From → To         | Meaning                         |
|-------------|--------------------|---------------------------------|
| SOLD        | Vendor → Invoice   | Seller issued this invoice      |
| PURCHASED_BY| Invoice → Vendor   | Buyer received this invoice     |
| FILED       | Vendor → Return    | Vendor filed this return        |
| REPORTS     | Return → Invoice   | GSTR-1 reports this invoice     |
| CLAIMS      | Return → Invoice   | GSTR-2B claims ITC for invoice  |

## API Endpoints

| Method | Path                              | Description                     |
|--------|-----------------------------------|---------------------------------|
| GET    | `/health`                         | Health + backend info           |
| POST   | `/ingest`                         | Reload CSV data into graph      |
| GET    | `/graph/summary`                  | Counts + top risky vendors      |
| GET    | `/reconcile/invoices`             | All mismatches with risk scores |
| GET    | `/reconcile/invoice/{invoice_id}` | Full audit trail for invoice    |
| GET    | `/vendors`                        | All vendors with risk scores    |
| GET    | `/vendors/{gstin}`                | Vendor detail + suspicious inv  |
| GET    | `/vendors/{gstin}/risk`           | Vendor risk score + reasons     |
| GET    | `/graph`                          | Nodes + edges for D3 vis        |

## Quick Start

### Option A: Docker Compose (recommended — uses Neo4j)

```bash
# 1. Clone and enter the repo
git clone https://github.com/professionaltarun2004/HackWithAI.git
cd HackWithAI

# 2. Copy env file
cp .env.example .env
# Edit .env — set GRAPH_BACKEND=neo4j (default)

# 3. Start everything
docker compose up --build

# 4. Open
#    Dashboard: http://localhost
#    Neo4j Browser: http://localhost:7474  (neo4j / gst-graph-2024)
#    API: http://localhost:8000/health
```

### Option B: Local dev (no Docker, uses NetworkX)

```bash
# 1. Backend
cd backend
pip install -r requirements.txt

# Set env to use in-memory graph
set GRAPH_BACKEND=networkx           # Windows
# export GRAPH_BACKEND=networkx      # Linux/Mac

cd ..
uvicorn backend.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 3. Open http://localhost:5173
```

### Option C: Local dev with Neo4j

```bash
# 1. Start Neo4j (Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/gst-graph-2024 \
  neo4j:5-community

# 2. Backend
set GRAPH_BACKEND=neo4j
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=gst-graph-2024

cd backend && pip install -r requirements.txt && cd ..
uvicorn backend.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev
```

## Re-Ingesting Data

```bash
# Via API (clears graph + reloads CSVs)
curl -X POST http://localhost:8000/ingest

# Or regenerate mock data first
python generate_data.py
cp vendors.csv invoices.csv backend/data/
curl -X POST http://localhost:8000/ingest
```

## Risk Scoring (0–100)

| Factor                              | Points      |
|-------------------------------------|-------------|
| Claimed but not reported            | +35         |
| Reported but not claimed            | +15         |
| Neither reported nor claimed        | +25         |
| Tax > ₹1L                          | +20         |
| Tax > ₹50K                         | +15         |
| Tax > ₹20K                         | +10         |
| Seller missed filings (per filing)  | +8          |
| Circular trading involvement        | +20         |

**Risk levels**: low (0-24), medium (25-49), high (50-69), critical (70-100)

## Switching Graph Backends

Set `GRAPH_BACKEND` in `.env`:

| Value      | Backend             | Status            |
|-----------|---------------------|-------------------|
| `neo4j`   | Neo4j (Cypher)      | Full implementation |
| `networkx`| NetworkX (in-memory)| Full implementation |
| `neptune` | Amazon Neptune      | Stub              |
| `arango`  | ArangoDB            | Stub              |

## Project Structure

```
HackWithAI/
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Environment config
│   ├── requirements.txt
│   ├── adapters/
│   │   ├── base.py               # GraphAdapter ABC
│   │   ├── neo4j_adapter.py      # Neo4j (Cypher)
│   │   ├── networkx_adapter.py   # NetworkX (in-memory)
│   │   ├── neptune_adapter.py    # Neptune (stub)
│   │   └── arango_adapter.py     # ArangoDB (stub)
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── services/
│   │   ├── ingestion.py          # CSV → Graph
│   │   ├── reconciliation.py     # Mismatch engine
│   │   └── risk_scoring.py       # Risk scoring
│   ├── api/
│   │   └── routes.py             # REST endpoints
│   └── data/
│       ├── vendors.csv
│       └── invoices.csv
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Main app + tabs
│   │   ├── api.js                # API client
│   │   ├── GraphVisualization.jsx # D3 graph
│   │   ├── MismatchList.jsx      # Invoice reconciliation
│   │   ├── VendorRiskBoard.jsx   # Vendor risk leaderboard
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── cypher/
│   └── schema_and_queries.cypher # Reference Cypher
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
├── generate_data.py
├── vendors.csv
└── invoices.csv
```
