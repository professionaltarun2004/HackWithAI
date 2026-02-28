"""
FastAPI routes — all REST endpoints for the React dashboard.
"""

import os
import glob

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ..adapters.base import GraphAdapter
from ..services.reconciliation import reconcile_all_invoices, get_invoice_audit_trail
from ..services.risk_scoring import score_vendor
from ..services.ingestion import load_csv
from ..models.schemas import (
    HealthResponse,
    IngestResponse,
    GraphSummary,
    VendorRisk,
)
from .. import config

# Will be set by main.py after adapter initialisation
adapter: GraphAdapter = None  # type: ignore

router = APIRouter()


def _get_circular_gstins():
    try:
        chains = adapter.detect_circular_trading(max_depth=5)
    except Exception:
        chains = []
    gstins = set()
    for chain in chains:
        gstins.update(chain)
    return gstins


# ── Health ─────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
def health_check():
    summary = adapter.get_graph_summary()
    return HealthResponse(
        status="ok",
        graph_backend=config.GRAPH_BACKEND.value,
        vendor_count=summary.get("vendor_count", 0),
        invoice_count=summary.get("invoice_count", 0),
    )


# ── Ingest ─────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
def ingest_data():
    """
    Reset to default data.
    Removes all previously uploaded CSVs from the uploads directory,
    clears the graph, and reloads only the static seed data.
    """
    # 1. Wipe upload directory so it no longer contributes
    for f in glob.glob(os.path.join(config.UPLOADS_DATA_DIR, "*.csv")):
        try:
            os.remove(f)
        except OSError:
            pass

    # 2. Reload only the static default data
    adapter.clear()
    adapter.create_constraints()
    v_count, i_count = load_csv(config.DATA_DIR, adapter)
    return IngestResponse(
        status="ok",
        vendors_loaded=v_count,
        invoices_loaded=i_count,
    )


# ── Graph summary ─────────────────────────────────────────

@router.get("/graph/summary")
def graph_summary():
    summary = adapter.get_graph_summary()
    circ = _get_circular_gstins()

    # Top risky vendors
    vendors = adapter.get_all_vendors()
    vendor_risks = []
    for v in vendors:
        vr = score_vendor(adapter, v["gstin"], circ)
        vendor_risks.append(vr)
    vendor_risks.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        **summary,
        "circular_chains": len(circ) > 0,
        "top_risky_vendors": vendor_risks[:10],
    }


# ── Reconciliation ─────────────────────────────────────────

@router.get("/reconcile/invoices")
def reconcile_invoices():
    """List all mismatched invoices with risk scores."""
    return reconcile_all_invoices(adapter)


@router.get("/reconcile/invoice/{invoice_id}")
def reconcile_invoice(invoice_id: str):
    """Get full audit trail for a single invoice."""
    result = get_invoice_audit_trail(adapter, invoice_id)
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result


# ── Vendors ────────────────────────────────────────────────

@router.get("/vendors")
def get_vendors():
    """List all vendors with risk scores."""
    circ = _get_circular_gstins()
    vendors = adapter.get_all_vendors()
    results = []
    for v in vendors:
        vr = score_vendor(adapter, v["gstin"], circ)
        results.append(vr)
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


@router.get("/vendors/{gstin}")
def get_vendor_detail(gstin: str):
    """Get vendor detail including suspicious invoices."""
    vendor = adapter.get_vendor(gstin)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    circ = _get_circular_gstins()
    vr = score_vendor(adapter, gstin, circ)

    # attached suspicious invoices
    vendor_invoices = adapter.get_vendor_invoices(gstin)
    suspicious = [
        inv for inv in vendor_invoices.get("purchased", [])
        if inv.get("claimed_by_buyer") and not inv.get("reported_by_seller")
    ]

    return {
        **vr,
        "suspicious_invoices_details": suspicious,
    }


@router.get("/vendors/{gstin}/risk")
def get_vendor_risk(gstin: str):
    """Vendor risk score + reasons."""
    vendor = adapter.get_vendor(gstin)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    circ = _get_circular_gstins()
    return score_vendor(adapter, gstin, circ)


# ── Graph data (for frontend vis) ─────────────────────────

@router.get("/graph")
def get_graph_data():
    """Return nodes + edges for D3 visualisation."""
    data = adapter.get_graph_data()

    # Enrich vendor nodes with risk info
    circ = _get_circular_gstins()
    for node in data.get("nodes", []):
        if node.get("type") == "vendor":
            vr = score_vendor(adapter, node["id"], circ)
            node["risk_level"] = vr["risk_level"]
            node["risk_score"] = vr["risk_score"]
            node["suspicious_count"] = vr.get("suspicious_invoice_count", 0)

    return data


# ── Real-time CSV upload ───────────────────────────────────

@router.post("/realtime/upload-csv")
async def upload_csv(
    type: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accept a raw CSV upload for vendors or invoices.

    Saves the file to the UPLOADS directory (never overwrites static defaults),
    then APPENDS the new rows to the live graph without clearing existing data.
    This means the default vendors/invoices stay visible alongside the uploaded ones.

    Form fields:
      type — "vendors" | "invoices"
      file — the CSV file (text/csv)
    """
    if type not in ("vendors", "invoices"):
        raise HTTPException(
            status_code=400,
            detail="'type' must be 'vendors' or 'invoices'",
        )

    filename = f"{type}.csv"
    # Always write to the uploads subdirectory — never touch the static defaults
    dest = os.path.join(config.UPLOADS_DATA_DIR, filename)

    content = await file.read()
    with open(dest, "wb") as fh:
        fh.write(content)

    # Append-only: load ONLY the uploads directory without clearing.
    # upsert_vendor / upsert_invoice use MERGE so duplicates are handled safely.
    v_count, i_count = load_csv(config.UPLOADS_DATA_DIR, adapter)

    return {
        "status": "ok",
        "file_saved": filename,
        "vendors_loaded": v_count,
        "invoices_loaded": i_count,
    }
