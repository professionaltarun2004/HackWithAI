"""
Abstract base class for all graph adapters.

Every adapter must implement these methods so that the reconciliation engine,
risk scoring, and API layer are database-agnostic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class GraphAdapter(ABC):
    """Unified interface for graph database operations."""

    # ── lifecycle ──────────────────────────────────────────
    @abstractmethod
    def connect(self) -> None:
        """Establish connection / initialise the graph store."""

    @abstractmethod
    def close(self) -> None:
        """Clean up connections."""

    @abstractmethod
    def clear(self) -> None:
        """Delete ALL data (useful for re-ingestion)."""

    # ── schema / constraints ───────────────────────────────
    @abstractmethod
    def create_constraints(self) -> None:
        """Create indexes / uniqueness constraints on the graph."""

    # ── ingestion ──────────────────────────────────────────
    @abstractmethod
    def upsert_vendor(self, gstin: str, name: str, missed_filings: int) -> None:
        """Create or update a Vendor/Taxpayer node."""

    @abstractmethod
    def upsert_invoice(
        self,
        invoice_id: str,
        seller_gstin: str,
        buyer_gstin: str,
        amount: float,
        tax: float,
        reported_by_seller: bool,
        claimed_by_buyer: bool,
    ) -> None:
        """Create or update an Invoice node and its relationships."""

    # ── queries ────────────────────────────────────────────
    @abstractmethod
    def get_all_vendors(self) -> List[Dict[str, Any]]:
        """Return list of vendor dicts with basic properties."""

    @abstractmethod
    def get_vendor(self, gstin: str) -> Optional[Dict[str, Any]]:
        """Return a single vendor dict or None."""

    @abstractmethod
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Return a single invoice dict or None."""

    @abstractmethod
    def get_all_invoices(self) -> List[Dict[str, Any]]:
        """Return all invoices with seller/buyer info."""

    @abstractmethod
    def get_vendor_invoices(self, gstin: str) -> Dict[str, List[Dict[str, Any]]]:
        """Return {'sold': [...], 'purchased': [...]} for a vendor."""

    @abstractmethod
    def get_mismatched_invoices(self) -> List[Dict[str, Any]]:
        """Return invoices where reported_by_seller != claimed_by_buyer."""

    @abstractmethod
    def detect_circular_trading(self, max_depth: int = 5) -> List[List[str]]:
        """Find circular trading chains (A→B→C→A via invoice chains)."""

    @abstractmethod
    def get_invoice_trail(self, invoice_id: str) -> Dict[str, Any]:
        """Return full audit trail for an invoice: seller, buyer, return status, path."""

    @abstractmethod
    def get_graph_summary(self) -> Dict[str, Any]:
        """Return counts and summary statistics for dashboard."""

    @abstractmethod
    def get_graph_data(self) -> Dict[str, Any]:
        """Return {nodes: [...], edges: [...]} for frontend visualisation."""
