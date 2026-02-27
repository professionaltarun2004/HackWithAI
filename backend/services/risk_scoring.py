"""
Risk scoring engine — produces explainable 0–100 scores.

Factors:
  - Mismatch type (claimed-not-reported is worst)
  - Tax amount at risk
  - Seller missed filings
  - Circular trading involvement
  - Vendor compliance aggregation
"""

from typing import Any, Dict, List, Optional, Set

from ..adapters.base import GraphAdapter
from ..models.schemas import MismatchType, RiskLevel

# ── weights (tuned for hackathon demo) ─────────────────────
WEIGHT_MISMATCH_TYPE = {
    MismatchType.CLAIMED_NOT_REPORTED: 35,
    MismatchType.REPORTED_NOT_CLAIMED: 15,
    MismatchType.BOTH_MISSING: 25,
    MismatchType.MATCHED: 0,
    MismatchType.CIRCULAR_TRADE: 30,
    MismatchType.VENDOR_MISSED_FILINGS: 10,
}

TAX_THRESHOLDS = [
    (100_000, 20),  # tax > 1L  → +20
    (50_000, 15),   # tax > 50k → +15
    (20_000, 10),   # tax > 20k → +10
    (0, 5),         # any tax   → +5
]

MISSED_FILINGS_FACTOR = 8   # per missed filing
CIRCULAR_BONUS = 20         # if either party is in a cycle


def _tax_score(tax: float) -> int:
    for threshold, points in TAX_THRESHOLDS:
        if tax >= threshold:
            return points
    return 0


def score_invoice(
    inv: Dict[str, Any],
    adapter: GraphAdapter,
    circular_gstins: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Score a single invoice.  Returns {"risk_score": int, "risk_level": str, "reasons": [...]}.
    """
    from .reconciliation import classify_mismatch

    reasons: List[str] = []
    score = 0

    mtype = classify_mismatch(inv)

    # 1) Mismatch type
    mtype_points = WEIGHT_MISMATCH_TYPE.get(mtype, 0)
    if mtype_points:
        score += mtype_points
        reasons.append(f"{mtype.value} (+{mtype_points})")

    # 2) Tax amount at risk
    tax = inv.get("tax", 0)
    tp = _tax_score(tax)
    score += tp
    reasons.append(f"Tax amount ₹{tax:,.0f} (+{tp})")

    # 3) Seller missed filings
    seller_gstin = inv.get("seller_gstin", "")
    seller = adapter.get_vendor(seller_gstin) if seller_gstin else None
    if seller:
        missed = seller.get("missed_filings", 0)
        if missed > 0:
            pts = missed * MISSED_FILINGS_FACTOR
            score += pts
            reasons.append(f"Seller missed {missed} filings (+{pts})")

    # 4) Circular trading
    if circular_gstins:
        buyer_gstin = inv.get("buyer_gstin", "")
        if seller_gstin in circular_gstins or buyer_gstin in circular_gstins:
            score += CIRCULAR_BONUS
            reasons.append(f"Circular trading involvement (+{CIRCULAR_BONUS})")

    # Clamp to 0–100
    score = max(0, min(100, score))

    return {
        "risk_score": score,
        "risk_level": _level(score),
        "reasons": reasons,
    }


def score_vendor(adapter: GraphAdapter, gstin: str, circular_gstins: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    Compute a vendor-level risk score + compliance score.
    """
    vendor = adapter.get_vendor(gstin)
    if not vendor:
        return {"risk_score": 0, "risk_level": "low", "compliance_score": 100, "reasons": []}

    reasons: List[str] = []
    score = 0

    missed = vendor.get("missed_filings", 0)
    if missed:
        pts = missed * MISSED_FILINGS_FACTOR
        score += pts
        reasons.append(f"Missed {missed} filings (+{pts})")

    # Count suspicious incoming invoices
    vendor_invoices = adapter.get_vendor_invoices(gstin)
    purchased = vendor_invoices.get("purchased", [])
    suspicious = [
        inv for inv in purchased
        if inv.get("claimed_by_buyer") and not inv.get("reported_by_seller")
    ]
    if suspicious:
        pts = min(len(suspicious) * 25, 50)
        score += pts
        reasons.append(f"{len(suspicious)} suspicious incoming invoices (+{pts})")

    # High-risk neighbours (counterparty vendors with missed_filings >= 2)
    all_vendors_map = {v["gstin"]: v for v in adapter.get_all_vendors()}
    sold = vendor_invoices.get("sold", [])
    neighbour_gstins: Set[str] = set()
    for inv in purchased:
        seller = inv.get("seller_gstin")
        if seller and seller != gstin:
            neighbour_gstins.add(seller)
    for inv in sold:
        buyer = inv.get("buyer_gstin")
        if buyer and buyer != gstin:
            neighbour_gstins.add(buyer)
    high_risk_neighbours = sum(
        1 for g in neighbour_gstins
        if all_vendors_map.get(g, {}).get("missed_filings", 0) >= 2
    )
    if high_risk_neighbours > 0:
        pts = high_risk_neighbours * 5
        score += pts
        reasons.append(f"{high_risk_neighbours} high-risk neighbouring vendor(s) (+{pts})")

    # Circularity
    possible_circular_trading = gstin in (circular_gstins or set())
    if possible_circular_trading:
        score += CIRCULAR_BONUS
        reasons.append(f"Involved in circular trading (+{CIRCULAR_BONUS})")

    score = max(0, min(100, score))

    # Compliance score is inverse: 100 means fully compliant
    compliance = max(0, 100 - score)

    return {
        "gstin": gstin,
        "name": vendor.get("name", ""),
        "risk_score": score,
        "risk_level": _level(score),
        "missed_filings": missed,
        "total_incoming": vendor.get("total_incoming", 0),
        "total_outgoing": vendor.get("total_outgoing", 0),
        "suspicious_invoice_count": len(suspicious),
        "compliance_score": compliance,
        "reasons": reasons,
        "possible_circular_trading": possible_circular_trading,
        "high_risk_neighbours": high_risk_neighbours,
    }


def _level(score: int) -> str:
    if score >= 70:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 25:
        return "medium"
    return "low"
