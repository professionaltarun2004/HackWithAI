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


// =============================================================
// 8. DIAGNOSTIC QUERIES — run these to audit graph health
// =============================================================

// ── 8a. Floating invoices (no :SOLD relationship — no known seller) ──────────
MATCH (inv:Invoice)
WHERE NOT ()-[:SOLD]->(inv)
RETURN inv.invoice_id AS floating_invoice,
       inv.seller_gstin,
       inv.buyer_gstin,
       inv.amount,
       'missing SOLD edge' AS problem
ORDER BY inv.invoice_id;

// ── 8b. Invoices missing their buyer edge (:PURCHASED_BY) ───────────────────
MATCH (inv:Invoice)
WHERE NOT (inv)-[:PURCHASED_BY]->()
RETURN inv.invoice_id AS floating_invoice,
       inv.seller_gstin,
       inv.buyer_gstin,
       inv.amount,
       'missing PURCHASED_BY edge' AS problem
ORDER BY inv.invoice_id;

// ── 8c. Invoices missing BOTH edges (completely orphaned) ───────────────────
MATCH (inv:Invoice)
WHERE NOT ()-[:SOLD]->(inv)
  AND NOT (inv)-[:PURCHASED_BY]->()
RETURN inv.invoice_id, inv.seller_gstin, inv.buyer_gstin,
       'fully orphaned — no edges at all' AS problem;

// ── 8d. Vendor nodes without any invoice relationships ──────────────────────
MATCH (v:Vendor)
WHERE NOT (v)-[:SOLD]->()
  AND NOT ()-[:PURCHASED_BY]->(v)
RETURN v.gstin, v.name, v.missed_filings,
       'isolated vendor — no invoices' AS problem
ORDER BY v.gstin;

// ── 8e. Stub vendor nodes (created from invoice data, missing proper name) ───
//  These are vendors whose name equals their GSTIN (placeholder set by adapter)
MATCH (v:Vendor)
WHERE v.name = v.gstin
RETURN v.gstin, v.name, v.missed_filings,
       'stub node — name not loaded from vendors.csv' AS problem
ORDER BY v.gstin;

// ── 8f. Duplicate GSTIN detection ───────────────────────────────────────────
//  Should return zero rows if the UNIQUE constraint is enforced correctly.
MATCH (v:Vendor)
WITH v.gstin AS gstin, count(*) AS cnt
WHERE cnt > 1
RETURN gstin, cnt AS duplicate_count
ORDER BY cnt DESC;

// ── 8g. Invoice relationship cardinality check ───────────────────────────────
//  Each invoice must have exactly 1 :SOLD and 1 :PURCHASED_BY edge.
MATCH (inv:Invoice)
OPTIONAL MATCH ()-[s:SOLD]->(inv)
OPTIONAL MATCH (inv)-[p:PURCHASED_BY]->()
WITH inv.invoice_id AS invoice_id,
     count(DISTINCT s) AS sold_count,
     count(DISTINCT p) AS purchased_count
WHERE sold_count <> 1 OR purchased_count <> 1
RETURN invoice_id, sold_count, purchased_count,
       CASE
         WHEN sold_count = 0    THEN 'missing seller edge'
         WHEN sold_count > 1    THEN 'multiple sellers — data integrity error'
         WHEN purchased_count = 0 THEN 'missing buyer edge'
         WHEN purchased_count > 1 THEN 'multiple buyers — data integrity error'
         ELSE 'unknown anomaly'
       END AS diagnosis
ORDER BY invoice_id;

// ── 8h. GSTIN cross-check: invoice properties vs graph edges ─────────────────
//  Confirms that inv.seller_gstin / inv.buyer_gstin match the connected Vendors.
MATCH (seller:Vendor)-[:SOLD]->(inv:Invoice)-[:PURCHASED_BY]->(buyer:Vendor)
WHERE seller.gstin <> inv.seller_gstin
   OR buyer.gstin  <> inv.buyer_gstin
RETURN inv.invoice_id,
       seller.gstin AS edge_seller, inv.seller_gstin AS prop_seller,
       buyer.gstin  AS edge_buyer,  inv.buyer_gstin  AS prop_buyer,
       'edge GSTIN does not match invoice property' AS problem;


// =============================================================
// 9. CORRECTIVE CYPHER — repair a floating invoice if found
// =============================================================

// Repair: attach a floating invoice to its seller/buyer using the
// seller_gstin / buyer_gstin properties already stored on the node.
MATCH (inv:Invoice)
WHERE NOT ()-[:SOLD]->(inv)
MERGE (seller:Vendor {gstin: inv.seller_gstin})
ON CREATE SET seller.name = inv.seller_gstin, seller.missed_filings = 0
MERGE (seller)-[:SOLD]->(inv);

MATCH (inv:Invoice)
WHERE NOT (inv)-[:PURCHASED_BY]->()
MERGE (buyer:Vendor {gstin: inv.buyer_gstin})
ON CREATE SET buyer.name = inv.buyer_gstin, buyer.missed_filings = 0
MERGE (inv)-[:PURCHASED_BY]->(buyer);


// =============================================================
// 10. RECOMMENDED BEST-PRACTICE SCHEMA (reference)
// =============================================================
//
// Node labels:
//   Vendor  { gstin: String UNIQUE, name: String, missed_filings: Int }
//   Invoice { invoice_id: String UNIQUE, seller_gstin: String,
//             buyer_gstin: String, amount: Float, tax: Float,
//             reported_by_seller: Boolean, claimed_by_buyer: Boolean }
//   Return  { id: String UNIQUE, type: 'GSTR-1'|'GSTR-2B' }
//
// Relationships (all directed):
//   (Vendor)  -[:SOLD]--------->  (Invoice)   seller issued this invoice
//   (Invoice) -[:PURCHASED_BY]-> (Vendor)    buyer received this invoice
//   (Vendor)  -[:FILED]--------> (Return)    vendor filed this return
//   (Return)  -[:REPORTS]------> (Invoice)   GSTR-1 reports this invoice
//   (Return)  -[:CLAIMS]-------> (Invoice)   GSTR-2B claims ITC for invoice
//
// Key invariants:
//   1. UNIQUE constraint on Vendor.gstin  — enforced via CREATE CONSTRAINT
//   2. UNIQUE constraint on Invoice.invoice_id — enforced via CREATE CONSTRAINT
//   3. Every Invoice has exactly 1 :SOLD and 1 :PURCHASED_BY edge
//   4. All MERGE on Vendor uses {gstin:...} (the unique key) — never by name
//   5. Invoice-side stubs use ON CREATE SET so existing good data is preserved

