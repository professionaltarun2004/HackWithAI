"""
CSV ingestion pipeline — reads vendors.csv and invoices.csv into the graph adapter.
"""

import csv
import os
from typing import Tuple

from ..adapters.base import GraphAdapter


def load_csv(data_dir: str, adapter: GraphAdapter) -> Tuple[int, int]:
    """
    Load vendors.csv and invoices.csv from *data_dir* into the given adapter.
    Returns (vendor_count, invoice_count).
    """
    vendor_count = 0
    invoice_count = 0

    # ── Vendors ────────────────────────────────────────────
    vendors_path = os.path.join(data_dir, "vendors.csv")
    if os.path.exists(vendors_path):
        with open(vendors_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                adapter.upsert_vendor(
                    gstin=row["gstin"].strip(),
                    name=row["name"].strip(),
                    missed_filings=int(row["missed_filings"]),
                )
                vendor_count += 1

    # ── Invoices ───────────────────────────────────────────
    invoices_path = os.path.join(data_dir, "invoices.csv")
    if os.path.exists(invoices_path):
        with open(invoices_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                adapter.upsert_invoice(
                    invoice_id=row["invoice_id"].strip(),
                    seller_gstin=row["seller_gstin"].strip(),
                    buyer_gstin=row["buyer_gstin"].strip(),
                    amount=float(row["amount"]),
                    tax=float(row["tax"]),
                    reported_by_seller=row["reported_by_seller"].strip().lower() == "true",
                    claimed_by_buyer=row["claimed_by_buyer"].strip().lower() == "true",
                )
                invoice_count += 1

    return vendor_count, invoice_count
