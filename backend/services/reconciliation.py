"""
Reconciliation engine — multi-hop ITC chain validation.

Works with any GraphAdapter implementation.
"""

from typing import Any, Dict, List

from ..adapters.base import GraphAdapter
from ..models.schemas import MismatchType


def classify_mismatch(inv: Dict[str, Any]) -> MismatchType:
    """Classify a single invoice's mismatch type."""
    reported = inv.get("reported_by_seller", False)
    claimed = inv.get("claimed_by_buyer", False)

    if reported and claimed:
        return MismatchType.MATCHED
    elif claimed and not reported:
        return MismatchType.CLAIMED_NOT_REPORTED
    elif reported and not claimed:
        return MismatchType.REPORTED_NOT_CLAIMED
    else:
        return MismatchType.BOTH_MISSING


def reconcile_all_invoices(adapter: GraphAdapter) -> List[Dict[str, Any]]:
    """
    Run reconciliation across all invoices.
    Returns list of invoices annotated with mismatch_type + risk metadata.
    """
    from .risk_scoring import score_invoice  # avoid circular import

    mismatches = adapter.get_mismatched_invoices()
    results = []

    # Also detect circular chains for enrichment
    try:
        circular_chains = adapter.detect_circular_trading(max_depth=5)
    except Exception:
        circular_chains = []

    # Build set of GSTINs involved in circular trades
    circular_gstins = set()
    for chain in circular_chains:
        circular_gstins.update(chain)

    for inv in mismatches:
        mtype = classify_mismatch(inv)
        risk = score_invoice(inv, adapter, circular_gstins)
        results.append(
            {
                **inv,
                "mismatch_type": mtype.value,
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
            }
        )

    # sort by risk descending
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


def get_invoice_audit_trail(adapter: GraphAdapter, invoice_id: str) -> Dict[str, Any]:
    """
    Build a full audit trail for a single invoice:
    1. Invoice exists?
    2. Seller filed GSTR-1?
    3. Buyer received in GSTR-2B?
    4. Seller compliance (missed filings)?
    5. Circular involvement?
    """
    from .risk_scoring import score_invoice

    trail_data = adapter.get_invoice_trail(invoice_id)
    if not trail_data:
        return {}

    mtype = classify_mismatch(trail_data)

    # Check circularity
    try:
        circular_chains = adapter.detect_circular_trading(max_depth=5)
    except Exception:
        circular_chains = []
    circular_gstins = set()
    for chain in circular_chains:
        circular_gstins.update(chain)

    in_circular = (
        trail_data.get("seller_gstin", "") in circular_gstins
        or trail_data.get("buyer_gstin", "") in circular_gstins
    )

    risk = score_invoice(trail_data, adapter, circular_gstins)

    # Build step-by-step trail
    steps = []
    step_num = 1

    # Step 1: Invoice details
    steps.append(
        {
            "step": step_num,
            "description": f"Invoice {invoice_id}: ₹{trail_data.get('amount', 0):,.0f} "
            f"(tax ₹{trail_data.get('tax', 0):,.0f}) "
            f"from {trail_data.get('seller_name', 'Unknown')} → "
            f"{trail_data.get('buyer_name', 'Unknown')}",
            "status": "ok",
        }
    )
    step_num += 1

    # Step 2: GSTR-1 (seller reporting)
    reported = trail_data.get("reported_by_seller", False)
    steps.append(
        {
            "step": step_num,
            "description": (
                f"Seller ({trail_data.get('seller_gstin', '')}) "
                + ("filed GSTR-1 — invoice reported ✓" if reported else "did NOT file GSTR-1 — invoice NOT reported ✗")
            ),
            "status": "ok" if reported else "error",
        }
    )
    step_num += 1

    # Step 3: GSTR-2B (buyer claim)
    claimed = trail_data.get("claimed_by_buyer", False)
    steps.append(
        {
            "step": step_num,
            "description": (
                f"Buyer ({trail_data.get('buyer_gstin', '')}) "
                + ("claimed ITC in GSTR-2B ✓" if claimed else "did NOT claim ITC in GSTR-2B")
            ),
            "status": "warning" if (claimed and not reported) else ("ok" if claimed else "ok"),
        }
    )
    step_num += 1

    # Step 4: Seller compliance
    seller_missed = trail_data.get("seller_missed_filings", 0)
    if seller_missed > 0:
        steps.append(
            {
                "step": step_num,
                "description": f"Seller has {seller_missed} missed return filings — compliance concern",
                "status": "warning",
            }
        )
        step_num += 1

    # Step 5: Circular trade check
    if in_circular:
        steps.append(
            {
                "step": step_num,
                "description": "⚠ Parties involved in circular trading pattern",
                "status": "error",
            }
        )
        step_num += 1

    # Generate natural-language explanation
    explanation = _generate_explanation(trail_data, mtype, risk, in_circular)

    return {
        "invoice_id": invoice_id,
        "seller_gstin": trail_data.get("seller_gstin", ""),
        "seller_name": trail_data.get("seller_name", "Unknown"),
        "buyer_gstin": trail_data.get("buyer_gstin", ""),
        "buyer_name": trail_data.get("buyer_name", "Unknown"),
        "amount": trail_data.get("amount", 0),
        "tax": trail_data.get("tax", 0),
        "reported_by_seller": trail_data.get("reported_by_seller", False),
        "claimed_by_buyer": trail_data.get("claimed_by_buyer", False),
        "mismatch_type": mtype.value,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "trail": steps,
        "explanation": explanation,
    }


def _generate_explanation(
    trail: Dict[str, Any],
    mtype: MismatchType,
    risk: Dict[str, Any],
    in_circular: bool,
) -> str:
    """Generate a natural-language audit explanation."""
    inv_id = trail.get("invoice_id", "?")
    seller = trail.get("seller_name", trail.get("seller_gstin", "Unknown"))
    buyer = trail.get("buyer_name", trail.get("buyer_gstin", "Unknown"))
    amount = trail.get("amount", 0)
    tax = trail.get("tax", 0)

    parts = [
        f"Invoice {inv_id} records a transaction of ₹{amount:,.0f} "
        f"(GST ₹{tax:,.0f}) from {seller} to {buyer}."
    ]

    if mtype == MismatchType.CLAIMED_NOT_REPORTED:
        parts.append(
            f"The buyer has claimed Input Tax Credit (ITC) in their GSTR-2B, "
            f"but the seller has NOT reported this invoice in their GSTR-1. "
            f"This is a red flag — the buyer may be claiming fraudulent ITC."
        )
    elif mtype == MismatchType.REPORTED_NOT_CLAIMED:
        parts.append(
            f"The seller reported this invoice in GSTR-1, but the buyer "
            f"has not claimed the ITC in GSTR-2B. This may indicate the buyer "
            f"is unaware of the transaction or the invoice is disputed."
        )
    elif mtype == MismatchType.BOTH_MISSING:
        parts.append(
            f"Neither party has reported this invoice — it is not in GSTR-1 "
            f"or GSTR-2B. This could indicate off-the-books transactions."
        )

    seller_missed = trail.get("seller_missed_filings", 0)
    if seller_missed > 0:
        parts.append(
            f"The seller has {seller_missed} missed GST return filings, "
            f"raising further compliance concerns."
        )

    if in_circular:
        parts.append(
            f"Additionally, one or both parties are involved in a circular "
            f"trading pattern (A→B→C→A), which is a common indicator of "
            f"fraudulent ITC chains."
        )

    parts.append(
        f"Overall risk score: {risk['risk_score']}/100 ({risk['risk_level']})."
    )

    return " ".join(parts)
