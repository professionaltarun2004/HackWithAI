"""
NetworkX adapter — in-memory fallback for fast local demos (no external DB needed).

Refactored from the original graph_logic.py to conform to the GraphAdapter interface.
"""

import networkx as nx
from typing import Any, Dict, List, Optional
from .base import GraphAdapter


class NetworkXAdapter(GraphAdapter):
    def __init__(self):
        self.G: nx.DiGraph = nx.DiGraph()

    # ── lifecycle ──────────────────────────────────────────
    def connect(self) -> None:
        pass  # nothing to connect — it's all in memory

    def close(self) -> None:
        pass

    def clear(self) -> None:
        self.G.clear()

    # ── schema / constraints ───────────────────────────────
    def create_constraints(self) -> None:
        pass  # no schema enforcement in NetworkX

    # ── ingestion ──────────────────────────────────────────
    def upsert_vendor(self, gstin: str, name: str, missed_filings: int) -> None:
        self.G.add_node(
            gstin, type="vendor", name=name, missed_filings=missed_filings
        )

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
        self.G.add_node(
            invoice_id,
            type="invoice",
            seller_gstin=seller_gstin,
            buyer_gstin=buyer_gstin,
            amount=amount,
            tax=tax,
            reported_by_seller=reported_by_seller,
            claimed_by_buyer=claimed_by_buyer,
        )
        # seller → invoice → buyer
        self.G.add_edge(seller_gstin, invoice_id, rel="SOLD")
        self.G.add_edge(invoice_id, buyer_gstin, rel="PURCHASED_BY")

    # ── queries ────────────────────────────────────────────
    def get_all_vendors(self) -> List[Dict[str, Any]]:
        vendors = []
        for node, attrs in self.G.nodes(data=True):
            if attrs.get("type") != "vendor":
                continue
            sold = [
                n for n in self.G.successors(node) if self.G.nodes[n].get("type") == "invoice"
            ]
            purchased = [
                n for n in self.G.predecessors(node) if self.G.nodes[n].get("type") == "invoice"
            ]
            vendors.append(
                {
                    "gstin": node,
                    "name": attrs.get("name", ""),
                    "missed_filings": attrs.get("missed_filings", 0),
                    "total_outgoing": len(sold),
                    "total_incoming": len(purchased),
                }
            )
        return vendors

    def get_vendor(self, gstin: str) -> Optional[Dict[str, Any]]:
        if gstin not in self.G or self.G.nodes[gstin].get("type") != "vendor":
            return None
        attrs = self.G.nodes[gstin]
        sold = [
            n for n in self.G.successors(gstin) if self.G.nodes[n].get("type") == "invoice"
        ]
        purchased = [
            n for n in self.G.predecessors(gstin) if self.G.nodes[n].get("type") == "invoice"
        ]
        return {
            "gstin": gstin,
            "name": attrs.get("name", ""),
            "missed_filings": attrs.get("missed_filings", 0),
            "total_outgoing": len(sold),
            "total_incoming": len(purchased),
        }

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        if invoice_id not in self.G or self.G.nodes[invoice_id].get("type") != "invoice":
            return None
        a = self.G.nodes[invoice_id]
        return {
            "invoice_id": invoice_id,
            "seller_gstin": a.get("seller_gstin", ""),
            "buyer_gstin": a.get("buyer_gstin", ""),
            "amount": a.get("amount", 0),
            "tax": a.get("tax", 0),
            "reported_by_seller": a.get("reported_by_seller", False),
            "claimed_by_buyer": a.get("claimed_by_buyer", False),
        }

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        invoices = []
        for node, attrs in self.G.nodes(data=True):
            if attrs.get("type") != "invoice":
                continue
            invoices.append(
                {
                    "invoice_id": node,
                    "seller_gstin": attrs.get("seller_gstin", ""),
                    "buyer_gstin": attrs.get("buyer_gstin", ""),
                    "amount": attrs.get("amount", 0),
                    "tax": attrs.get("tax", 0),
                    "reported_by_seller": attrs.get("reported_by_seller", False),
                    "claimed_by_buyer": attrs.get("claimed_by_buyer", False),
                }
            )
        return invoices

    def get_vendor_invoices(self, gstin: str) -> Dict[str, List[Dict[str, Any]]]:
        sold = []
        purchased = []
        for n in self.G.successors(gstin):
            if self.G.nodes[n].get("type") == "invoice":
                sold.append(self.get_invoice(n))
        for n in self.G.predecessors(gstin):
            if self.G.nodes[n].get("type") == "invoice":
                purchased.append(self.get_invoice(n))
        return {"sold": sold, "purchased": purchased}

    def get_mismatched_invoices(self) -> List[Dict[str, Any]]:
        mismatches = []
        for node, attrs in self.G.nodes(data=True):
            if attrs.get("type") != "invoice":
                continue
            reported = attrs.get("reported_by_seller", False)
            claimed = attrs.get("claimed_by_buyer", False)
            if reported != claimed:
                mismatches.append(self.get_invoice(node))
        # sort by tax descending
        mismatches.sort(key=lambda x: x.get("tax", 0), reverse=True)
        return mismatches

    def detect_circular_trading(self, max_depth: int = 5) -> List[List[str]]:
        """
        Find cycles where vendors trade in a circle via invoices.
        Extract vendor-only subgraph (vendor→vendor if there is an invoice between them),
        then use nx.simple_cycles.
        """
        vendor_graph = nx.DiGraph()
        for node, attrs in self.G.nodes(data=True):
            if attrs.get("type") != "invoice":
                continue
            seller = attrs.get("seller_gstin")
            buyer = attrs.get("buyer_gstin")
            if seller and buyer and seller != buyer:
                vendor_graph.add_edge(seller, buyer)

        cycles = []
        for cycle in nx.simple_cycles(vendor_graph):
            if 2 <= len(cycle) <= max_depth:
                cycles.append(cycle)
        return cycles

    def get_invoice_trail(self, invoice_id: str) -> Dict[str, Any]:
        inv = self.get_invoice(invoice_id)
        if not inv:
            return {}
        seller = self.get_vendor(inv["seller_gstin"]) or {}
        buyer = self.get_vendor(inv["buyer_gstin"]) or {}
        return {
            "invoice_id": invoice_id,
            "amount": inv.get("amount", 0),
            "tax": inv.get("tax", 0),
            "reported_by_seller": inv.get("reported_by_seller", False),
            "claimed_by_buyer": inv.get("claimed_by_buyer", False),
            "seller_gstin": inv.get("seller_gstin", ""),
            "seller_name": seller.get("name", "Unknown"),
            "seller_missed_filings": seller.get("missed_filings", 0),
            "buyer_gstin": inv.get("buyer_gstin", ""),
            "buyer_name": buyer.get("name", "Unknown"),
            "buyer_missed_filings": buyer.get("missed_filings", 0),
            "gstr1_filed": inv.get("reported_by_seller", False),
            "gstr2b_filed": inv.get("claimed_by_buyer", False),
        }

    def get_graph_summary(self) -> Dict[str, Any]:
        vendors = [n for n, a in self.G.nodes(data=True) if a.get("type") == "vendor"]
        invoices = [n for n, a in self.G.nodes(data=True) if a.get("type") == "invoice"]
        mismatched = [
            n
            for n, a in self.G.nodes(data=True)
            if a.get("type") == "invoice"
            and a.get("reported_by_seller") != a.get("claimed_by_buyer")
        ]
        suspicious = [
            n
            for n, a in self.G.nodes(data=True)
            if a.get("type") == "invoice"
            and a.get("claimed_by_buyer")
            and not a.get("reported_by_seller")
        ]
        return {
            "vendor_count": len(vendors),
            "invoice_count": len(invoices),
            "mismatch_count": len(mismatched),
            "suspicious_count": len(suspicious),
        }

    def get_graph_data(self) -> Dict[str, Any]:
        nodes = []
        edges = []
        for node, attrs in self.G.nodes(data=True):
            nd = {"id": node, "type": attrs.get("type", "unknown")}
            if attrs.get("type") == "vendor":
                nd.update(
                    {
                        "name": attrs.get("name", ""),
                        "missed_filings": attrs.get("missed_filings", 0),
                    }
                )
            elif attrs.get("type") == "invoice":
                nd.update(
                    {
                        "amount": attrs.get("amount", 0),
                        "tax": attrs.get("tax", 0),
                        "seller_gstin": attrs.get("seller_gstin", ""),
                        "buyer_gstin": attrs.get("buyer_gstin", ""),
                        "reported_by_seller": attrs.get("reported_by_seller", False),
                        "claimed_by_buyer": attrs.get("claimed_by_buyer", False),
                        "is_suspicious": bool(
                            attrs.get("claimed_by_buyer") and not attrs.get("reported_by_seller")
                        ),
                    }
                )
            nodes.append(nd)
        for source, target in self.G.edges():
            edges.append({"source": source, "target": target})
        return {"nodes": nodes, "edges": edges}
