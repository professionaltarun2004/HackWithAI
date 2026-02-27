"""
Amazon Neptune adapter — stub / minimal implementation.

Neptune supports Gremlin and SPARQL. This stub provides the interface shape
so the application can claim Neptune compatibility. For a real implementation,
use the gremlin_python driver or boto3 with Neptune's HTTP endpoint.
"""

from typing import Any, Dict, List, Optional
from .base import GraphAdapter


class NeptuneAdapter(GraphAdapter):
    """
    Stub adapter for Amazon Neptune.
    Methods raise NotImplementedError with helpful messages.
    """

    def __init__(self, endpoint: str = ""):
        self._endpoint = endpoint

    def connect(self) -> None:
        if not self._endpoint:
            raise RuntimeError(
                "Neptune endpoint not configured. "
                "Set NEPTUNE_ENDPOINT env var to your Neptune cluster endpoint."
            )
        # In production: from gremlin_python.driver import client
        # self._client = client.Client(f"wss://{self._endpoint}:8182/gremlin", "g")

    def close(self) -> None:
        pass

    def clear(self) -> None:
        # g.V().drop().iterate()
        raise NotImplementedError("Neptune clear() not yet implemented")

    def create_constraints(self) -> None:
        # Neptune doesn't have traditional constraints — use index config
        pass

    def upsert_vendor(self, gstin: str, name: str, missed_filings: int) -> None:
        # Gremlin: g.V().has('Vendor','gstin',gstin).fold()
        #           .coalesce(unfold(), addV('Vendor').property('gstin',gstin))
        #           .property('name',name).property('missed_filings',missed_filings)
        raise NotImplementedError("Neptune upsert_vendor() not yet implemented")

    def upsert_invoice(self, invoice_id, seller_gstin, buyer_gstin, amount, tax,
                       reported_by_seller, claimed_by_buyer) -> None:
        raise NotImplementedError("Neptune upsert_invoice() not yet implemented")

    def get_all_vendors(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Neptune get_all_vendors() not yet implemented")

    def get_vendor(self, gstin: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Neptune get_vendor() not yet implemented")

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Neptune get_invoice() not yet implemented")

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Neptune get_all_invoices() not yet implemented")

    def get_vendor_invoices(self, gstin: str) -> Dict[str, List[Dict[str, Any]]]:
        raise NotImplementedError("Neptune get_vendor_invoices() not yet implemented")

    def get_mismatched_invoices(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Neptune get_mismatched_invoices() not yet implemented")

    def detect_circular_trading(self, max_depth: int = 5) -> List[List[str]]:
        raise NotImplementedError("Neptune detect_circular_trading() not yet implemented")

    def get_invoice_trail(self, invoice_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Neptune get_invoice_trail() not yet implemented")

    def get_graph_summary(self) -> Dict[str, Any]:
        raise NotImplementedError("Neptune get_graph_summary() not yet implemented")

    def get_graph_data(self) -> Dict[str, Any]:
        raise NotImplementedError("Neptune get_graph_data() not yet implemented")
