// =============================================================
// GST Knowledge Graph — Cypher Reference
// =============================================================
// Run these in the Neo4j Browser (http://localhost:7474)
// or they are executed automatically by Neo4jAdapter.
// =============================================================

// ── 1. CONSTRAINTS & INDEXES ─────────────────────────────────

CREATE CONSTRAINT vendor_gstin IF NOT EXISTS
  FOR (v:Vendor) REQUIRE v.gstin IS UNIQUE;

CREATE CONSTRAINT invoice_id IF NOT EXISTS
  FOR (i:Invoice) REQUIRE i.invoice_id IS UNIQUE;

CREATE INDEX vendor_name_idx IF NOT EXISTS
  FOR (v:Vendor) ON (v.name);

CREATE INDEX invoice_seller_idx IF NOT EXISTS
  FOR (i:Invoice) ON (i.seller_gstin);

CREATE INDEX invoice_buyer_idx IF NOT EXISTS
  FOR (i:Invoice) ON (i.buyer_gstin);


// ── 2. SAMPLE INGESTION (single invoice) ─────────────────────

MERGE (seller:Vendor {gstin: 'N098QOW3F17I07N'})
SET seller.name = 'Alpha Traders', seller.missed_filings = 1

MERGE (buyer:Vendor {gstin: '7LT0TPC5YC33ULT'})
SET buyer.name = 'Beta Suppliers', buyer.missed_filings = 2

MERGE (inv:Invoice {invoice_id: 'INV001'})
SET inv.seller_gstin = 'N098QOW3F17I07N',
    inv.buyer_gstin  = '7LT0TPC5YC33ULT',
    inv.amount = 177474,
    inv.tax    = 31945,
    inv.reported_by_seller = true,
    inv.claimed_by_buyer   = true

MERGE (seller)-[:SOLD]->(inv)
MERGE (inv)-[:PURCHASED_BY]->(buyer)

// If reported by seller, create GSTR-1 return node:
MERGE (gstr1:Return {id: 'INV001_GSTR1', type: 'GSTR-1'})
MERGE (seller)-[:FILED]->(gstr1)
MERGE (gstr1)-[:REPORTS]->(inv);

// If claimed by buyer, create GSTR-2B return node:
MERGE (gstr2b:Return {id: 'INV001_GSTR2B', type: 'GSTR-2B'})
MERGE (buyer)-[:FILED]->(gstr2b)
MERGE (gstr2b)-[:CLAIMS]->(inv);


// ── 3. RECONCILIATION QUERIES ────────────────────────────────

// 3a. All mismatched invoices
MATCH (inv:Invoice)
WHERE inv.reported_by_seller <> inv.claimed_by_buyer
RETURN inv.invoice_id, inv.seller_gstin, inv.buyer_gstin,
       inv.amount, inv.tax,
       inv.reported_by_seller, inv.claimed_by_buyer
ORDER BY inv.tax DESC;

// 3b. Claimed by buyer but NOT reported by seller (highest risk)
MATCH (inv:Invoice)
WHERE inv.claimed_by_buyer = true AND inv.reported_by_seller = false
RETURN inv.invoice_id, inv.seller_gstin, inv.buyer_gstin,
       inv.tax
ORDER BY inv.tax DESC;

// 3c. Multi-hop ITC chain: Invoice → Seller GSTR-1 → Buyer GSTR-2B
MATCH (seller:Vendor)-[:SOLD]->(inv:Invoice)-[:PURCHASED_BY]->(buyer:Vendor)
OPTIONAL MATCH (gstr1:Return {type: 'GSTR-1'})-[:REPORTS]->(inv)
OPTIONAL MATCH (gstr2b:Return {type: 'GSTR-2B'})-[:CLAIMS]->(inv)
RETURN inv.invoice_id,
       seller.gstin AS seller, seller.name AS seller_name,
       buyer.gstin  AS buyer,  buyer.name  AS buyer_name,
       gstr1 IS NOT NULL AS gstr1_filed,
       gstr2b IS NOT NULL AS gstr2b_filed,
       inv.amount, inv.tax;


// ── 4. CIRCULAR TRADING DETECTION ────────────────────────────

// Find vendor cycles via invoice chains (depth 2-4)
MATCH path = (v:Vendor)-[:SOLD]->(:Invoice)-[:PURCHASED_BY]->(v2:Vendor)
WHERE v <> v2
WITH v, v2
MATCH circular = (v2)-[:SOLD]->(:Invoice)-[:PURCHASED_BY*1..4]->(v)
RETURN DISTINCT [n IN nodes(circular) WHERE n:Vendor | n.gstin] AS chain
LIMIT 20;


// ── 5. VENDOR RISK AGGREGATION ───────────────────────────────

// Vendors ranked by suspicious incoming invoices + missed filings
MATCH (v:Vendor)
OPTIONAL MATCH (suspicious:Invoice)-[:PURCHASED_BY]->(v)
  WHERE suspicious.claimed_by_buyer = true AND suspicious.reported_by_seller = false
RETURN v.gstin, v.name, v.missed_filings,
       count(suspicious) AS suspicious_count,
       v.missed_filings * 8 + count(suspicious) * 12 AS risk_score
ORDER BY risk_score DESC;


// ── 6. FULL AUDIT TRAIL FOR SINGLE INVOICE ───────────────────

MATCH (inv:Invoice {invoice_id: 'INV003'})
OPTIONAL MATCH (seller:Vendor)-[:SOLD]->(inv)
OPTIONAL MATCH (inv)-[:PURCHASED_BY]->(buyer:Vendor)
OPTIONAL MATCH (gstr1:Return {type: 'GSTR-1'})-[:REPORTS]->(inv)
OPTIONAL MATCH (gstr2b:Return {type: 'GSTR-2B'})-[:CLAIMS]->(inv)
RETURN inv.invoice_id,
       inv.amount, inv.tax,
       inv.reported_by_seller, inv.claimed_by_buyer,
       seller.gstin AS seller_gstin, seller.name AS seller_name,
       seller.missed_filings AS seller_missed,
       buyer.gstin AS buyer_gstin, buyer.name AS buyer_name,
       gstr1 IS NOT NULL AS gstr1_filed,
       gstr2b IS NOT NULL AS gstr2b_filed;


// ── 7. GRAPH SUMMARY ────────────────────────────────────────

MATCH (v:Vendor) WITH count(v) AS vendors
MATCH (i:Invoice) WITH vendors, count(i) AS invoices
MATCH (m:Invoice) WHERE m.reported_by_seller <> m.claimed_by_buyer
WITH vendors, invoices, count(m) AS mismatches
MATCH (s:Invoice) WHERE s.claimed_by_buyer = true AND s.reported_by_seller = false
RETURN vendors, invoices, mismatches, count(s) AS suspicious;
