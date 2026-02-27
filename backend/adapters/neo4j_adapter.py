"""
Neo4j adapter — primary production graph store.

Uses the official neo4j Python driver with Cypher queries.
"""

from typing import Any, Dict, List, Optional
from .base import GraphAdapter

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None  # graceful degradation if driver not installed


class Neo4jAdapter(GraphAdapter):
    def __init__(self, uri: str, user: str, password: str):
        if GraphDatabase is None:
            raise RuntimeError("neo4j driver not installed. Run: pip install neo4j")
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None

    # ── lifecycle ──────────────────────────────────────────
    def connect(self) -> None:
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        # verify connectivity
        self._driver.verify_connectivity()

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def _run(self, query: str, **params):
        """Execute a read/write query and return list of records as dicts."""
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [record.data() for record in result]

    def clear(self) -> None:
        self._run("MATCH (n) DETACH DELETE n")

    # ── schema / constraints ───────────────────────────────
    def create_constraints(self) -> None:
        constraints = [
            "CREATE CONSTRAINT vendor_gstin IF NOT EXISTS FOR (v:Vendor) REQUIRE v.gstin IS UNIQUE",
            "CREATE CONSTRAINT invoice_id IF NOT EXISTS FOR (i:Invoice) REQUIRE i.invoice_id IS UNIQUE",
            "CREATE INDEX vendor_name_idx IF NOT EXISTS FOR (v:Vendor) ON (v.name)",
            "CREATE INDEX invoice_seller_idx IF NOT EXISTS FOR (i:Invoice) ON (i.seller_gstin)",
            "CREATE INDEX invoice_buyer_idx IF NOT EXISTS FOR (i:Invoice) ON (i.buyer_gstin)",
        ]
        for cypher in constraints:
            try:
                self._run(cypher)
            except Exception:
                pass  # constraint may already exist

    # ── ingestion ──────────────────────────────────────────
    def upsert_vendor(self, gstin: str, name: str, missed_filings: int) -> None:
        self._run(
            """
            MERGE (v:Vendor {gstin: $gstin})
            SET v.name = $name,
                v.missed_filings = $missed_filings
            """,
            gstin=gstin,
            name=name,
            missed_filings=missed_filings,
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
        self._run(
            """
            MERGE (seller:Vendor {gstin: $seller_gstin})
            MERGE (buyer:Vendor {gstin: $buyer_gstin})
            MERGE (inv:Invoice {invoice_id: $invoice_id})
            SET inv.seller_gstin = $seller_gstin,
                inv.buyer_gstin = $buyer_gstin,
                inv.amount = $amount,
                inv.tax = $tax,
                inv.reported_by_seller = $reported_by_seller,
                inv.claimed_by_buyer = $claimed_by_buyer
            MERGE (seller)-[:SOLD]->(inv)
            MERGE (inv)-[:PURCHASED_BY]->(buyer)
            WITH inv, seller, buyer
            FOREACH (_ IN CASE WHEN $reported_by_seller THEN [1] ELSE [] END |
                MERGE (gstr1:Return {id: $invoice_id + '_GSTR1', type: 'GSTR-1'})
                MERGE (seller)-[:FILED]->(gstr1)
                MERGE (gstr1)-[:REPORTS]->(inv)
            )
            FOREACH (_ IN CASE WHEN $claimed_by_buyer THEN [1] ELSE [] END |
                MERGE (gstr2b:Return {id: $invoice_id + '_GSTR2B', type: 'GSTR-2B'})
                MERGE (buyer)-[:FILED]->(gstr2b)
                MERGE (gstr2b)-[:CLAIMS]->(inv)
            )
            """,
            invoice_id=invoice_id,
            seller_gstin=seller_gstin,
            buyer_gstin=buyer_gstin,
            amount=amount,
            tax=tax,
            reported_by_seller=reported_by_seller,
            claimed_by_buyer=claimed_by_buyer,
        )

    # ── queries ────────────────────────────────────────────
    def get_all_vendors(self) -> List[Dict[str, Any]]:
        rows = self._run(
            """
            MATCH (v:Vendor)
            OPTIONAL MATCH (v)-[:SOLD]->(sold:Invoice)
            OPTIONAL MATCH (purchased:Invoice)-[:PURCHASED_BY]->(v)
            RETURN v.gstin AS gstin,
                   v.name AS name,
                   v.missed_filings AS missed_filings,
                   count(DISTINCT sold) AS total_outgoing,
                   count(DISTINCT purchased) AS total_incoming
            """
        )
        return rows

    def get_vendor(self, gstin: str) -> Optional[Dict[str, Any]]:
        rows = self._run(
            """
            MATCH (v:Vendor {gstin: $gstin})
            OPTIONAL MATCH (v)-[:SOLD]->(sold:Invoice)
            OPTIONAL MATCH (purchased:Invoice)-[:PURCHASED_BY]->(v)
            RETURN v.gstin AS gstin,
                   v.name AS name,
                   v.missed_filings AS missed_filings,
                   count(DISTINCT sold) AS total_outgoing,
                   count(DISTINCT purchased) AS total_incoming
            """,
            gstin=gstin,
        )
        return rows[0] if rows else None

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        rows = self._run(
            """
            MATCH (inv:Invoice {invoice_id: $invoice_id})
            RETURN inv.invoice_id AS invoice_id,
                   inv.seller_gstin AS seller_gstin,
                   inv.buyer_gstin AS buyer_gstin,
                   inv.amount AS amount,
                   inv.tax AS tax,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer
            """,
            invoice_id=invoice_id,
        )
        return rows[0] if rows else None

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        return self._run(
            """
            MATCH (inv:Invoice)
            RETURN inv.invoice_id AS invoice_id,
                   inv.seller_gstin AS seller_gstin,
                   inv.buyer_gstin AS buyer_gstin,
                   inv.amount AS amount,
                   inv.tax AS tax,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer
            """
        )

    def get_vendor_invoices(self, gstin: str) -> Dict[str, List[Dict[str, Any]]]:
        sold = self._run(
            """
            MATCH (v:Vendor {gstin: $gstin})-[:SOLD]->(inv:Invoice)
            RETURN inv.invoice_id AS invoice_id,
                   inv.seller_gstin AS seller_gstin,
                   inv.buyer_gstin AS buyer_gstin,
                   inv.amount AS amount, inv.tax AS tax,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer
            """,
            gstin=gstin,
        )
        purchased = self._run(
            """
            MATCH (inv:Invoice)-[:PURCHASED_BY]->(v:Vendor {gstin: $gstin})
            RETURN inv.invoice_id AS invoice_id,
                   inv.seller_gstin AS seller_gstin,
                   inv.buyer_gstin AS buyer_gstin,
                   inv.amount AS amount, inv.tax AS tax,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer
            """,
            gstin=gstin,
        )
        return {"sold": sold, "purchased": purchased}

    def get_mismatched_invoices(self) -> List[Dict[str, Any]]:
        return self._run(
            """
            MATCH (inv:Invoice)
            WHERE inv.reported_by_seller <> inv.claimed_by_buyer
            RETURN inv.invoice_id AS invoice_id,
                   inv.seller_gstin AS seller_gstin,
                   inv.buyer_gstin AS buyer_gstin,
                   inv.amount AS amount, inv.tax AS tax,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer
            ORDER BY inv.tax DESC
            """
        )

    def detect_circular_trading(self, max_depth: int = 5) -> List[List[str]]:
        """
        Detect circular trading: Vendor A sells to B, B sells to C, C sells to A.
        Uses variable-length path matching in Cypher.
        """
        rows = self._run(
            """
            MATCH path = (v:Vendor)-[:SOLD]->(:Invoice)-[:PURCHASED_BY]->(v2:Vendor)
            WHERE v <> v2
            WITH v, v2
            MATCH circular = (v2)-[:SOLD]->(:Invoice)-[:PURCHASED_BY*1..4]->(v)
            RETURN DISTINCT [n IN nodes(circular) WHERE n:Vendor | n.gstin] AS chain
            LIMIT 20
            """
        )
        return [r["chain"] for r in rows]

    def get_invoice_trail(self, invoice_id: str) -> Dict[str, Any]:
        rows = self._run(
            """
            MATCH (inv:Invoice {invoice_id: $invoice_id})
            OPTIONAL MATCH (seller:Vendor)-[:SOLD]->(inv)
            OPTIONAL MATCH (inv)-[:PURCHASED_BY]->(buyer:Vendor)
            OPTIONAL MATCH (gstr1:Return {type: 'GSTR-1'})-[:REPORTS]->(inv)
            OPTIONAL MATCH (gstr2b:Return {type: 'GSTR-2B'})-[:CLAIMS]->(inv)
            RETURN inv.invoice_id AS invoice_id,
                   inv.amount AS amount,
                   inv.tax AS tax,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer,
                   seller.gstin AS seller_gstin,
                   seller.name AS seller_name,
                   seller.missed_filings AS seller_missed_filings,
                   buyer.gstin AS buyer_gstin,
                   buyer.name AS buyer_name,
                   buyer.missed_filings AS buyer_missed_filings,
                   gstr1 IS NOT NULL AS gstr1_filed,
                   gstr2b IS NOT NULL AS gstr2b_filed
            """,
            invoice_id=invoice_id,
        )
        return rows[0] if rows else {}

    def get_graph_summary(self) -> Dict[str, Any]:
        rows = self._run(
            """
            MATCH (v:Vendor) WITH count(v) AS vendor_count
            MATCH (i:Invoice) WITH vendor_count, count(i) AS invoice_count
            MATCH (i2:Invoice) WHERE i2.reported_by_seller <> i2.claimed_by_buyer
            WITH vendor_count, invoice_count, count(i2) AS mismatch_count
            MATCH (i3:Invoice) WHERE i3.claimed_by_buyer = true AND i3.reported_by_seller = false
            RETURN vendor_count, invoice_count, mismatch_count, count(i3) AS suspicious_count
            """
        )
        return rows[0] if rows else {}

    def get_graph_data(self) -> Dict[str, Any]:
        vendor_rows = self._run(
            """
            MATCH (v:Vendor)
            RETURN v.gstin AS id, 'vendor' AS type,
                   v.name AS name, v.missed_filings AS missed_filings
            """
        )
        invoice_rows = self._run(
            """
            MATCH (inv:Invoice)
            RETURN inv.invoice_id AS id, 'invoice' AS type,
                   inv.amount AS amount, inv.tax AS tax,
                   inv.seller_gstin AS seller_gstin,
                   inv.buyer_gstin AS buyer_gstin,
                   inv.reported_by_seller AS reported_by_seller,
                   inv.claimed_by_buyer AS claimed_by_buyer,
                   (inv.claimed_by_buyer = true AND inv.reported_by_seller = false) AS is_suspicious
            """
        )
        edge_rows = self._run(
            """
            MATCH (a)-[r]->(b)
            WHERE (a:Vendor AND b:Invoice) OR (a:Invoice AND b:Vendor)
            RETURN
              CASE WHEN a:Vendor THEN a.gstin ELSE a.invoice_id END AS source,
              CASE WHEN b:Vendor THEN b.gstin ELSE b.invoice_id END AS target
            """
        )
        return {
            "nodes": vendor_rows + invoice_rows,
            "edges": edge_rows,
        }
