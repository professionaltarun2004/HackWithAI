"""
ArangoDB adapter — stub / minimal implementation.

ArangoDB uses AQL and supports both document and graph models.
This stub provides the interface shape so the application can claim
ArangoDB compatibility.
"""

from typing import Any, Dict, List, Optional
from .base import GraphAdapter


class ArangoAdapter(GraphAdapter):
    """
    Stub adapter for ArangoDB.
    Methods raise NotImplementedError with helpful messages.
    """

    def __init__(self, url: str = "", db_name: str = "gst_graph",
                 user: str = "root", password: str = ""):
        self._url = url
        self._db_name = db_name
        self._user = user
        self._password = password

    def connect(self) -> None:
        if not self._url:
            raise RuntimeError(
                "ArangoDB URL not configured. Set ARANGO_URL env var."
            )
        # In production: from arango import ArangoClient
        # client = ArangoClient(hosts=self._url)
        # self._db = client.db(self._db_name, username=self._user, password=self._password)
        # self._graph = self._db.graph('gst_graph')

    def close(self) -> None:
        pass

    def clear(self) -> None:
        # FOR doc IN vendors REMOVE doc IN vendors
        # FOR doc IN invoices REMOVE doc IN invoices
        raise NotImplementedError("Arango clear() not yet implemented")

    def create_constraints(self) -> None:
        # AQL:
        # db.vendors.ensureIndex({ type: "persistent", fields: ["gstin"], unique: true })
        # db.invoices.ensureIndex({ type: "persistent", fields: ["invoice_id"], unique: true })
        raise NotImplementedError("Arango create_constraints() not yet implemented")

    def upsert_vendor(self, gstin: str, name: str, missed_filings: int) -> None:
        # AQL: UPSERT {gstin: @gstin} INSERT {gstin, name, missed_filings}
        #      UPDATE {name, missed_filings} IN vendors
        raise NotImplementedError("Arango upsert_vendor() not yet implemented")

    def upsert_invoice(self, invoice_id, seller_gstin, buyer_gstin, amount, tax,
                       reported_by_seller, claimed_by_buyer) -> None:
        raise NotImplementedError("Arango upsert_invoice() not yet implemented")

    def get_all_vendors(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Arango get_all_vendors() not yet implemented")

    def get_vendor(self, gstin: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Arango get_vendor() not yet implemented")

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Arango get_invoice() not yet implemented")

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Arango get_all_invoices() not yet implemented")

    def get_vendor_invoices(self, gstin: str) -> Dict[str, List[Dict[str, Any]]]:
        raise NotImplementedError("Arango get_vendor_invoices() not yet implemented")

    def get_mismatched_invoices(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Arango get_mismatched_invoices() not yet implemented")

    def detect_circular_trading(self, max_depth: int = 5) -> List[List[str]]:
        raise NotImplementedError("Arango detect_circular_trading() not yet implemented")

    def get_invoice_trail(self, invoice_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Arango get_invoice_trail() not yet implemented")

    def get_graph_summary(self) -> Dict[str, Any]:
        raise NotImplementedError("Arango get_graph_summary() not yet implemented")

    def get_graph_data(self) -> Dict[str, Any]:
        raise NotImplementedError("Arango get_graph_data() not yet implemented")
