import csv
import networkx as nx
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def load_data():
    vendors = []
    invoices = []
    
    with open(DATA_DIR / "vendors.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vendors.append({
                "gstin": row["gstin"],
                "name": row["name"],
                "missed_filings": int(row["missed_filings"])
            })
            
    with open(DATA_DIR / "invoices.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            invoices.append({
                "invoice_id": row["invoice_id"],
                "seller_gstin": row["seller_gstin"],
                "buyer_gstin": row["buyer_gstin"],
                "amount": int(row["amount"]),
                "tax": int(row["tax"]),
                "reported_by_seller": row["reported_by_seller"].strip().lower() == "true",
                "claimed_by_buyer": row["claimed_by_buyer"].strip().lower() == "true"
            })
            
    return vendors, invoices

def build_graph(vendors, invoices):
    G = nx.DiGraph()
    
    # Add vendor nodes
    for v in vendors:
        G.add_node(
            v["gstin"],
            type="vendor",
            name=v["name"],
            missed_filings=v["missed_filings"]
        )
        
    # Add invoice nodes and edges
    for inv in invoices:
        inv_id = inv["invoice_id"]
        G.add_node(
            inv_id,
            type="invoice",
            amount=inv["amount"],
            tax=inv["tax"],
            reported_by_seller=inv["reported_by_seller"],
            claimed_by_buyer=inv["claimed_by_buyer"],
            seller_gstin=inv["seller_gstin"],
            buyer_gstin=inv["buyer_gstin"]
        )
        
        # Directed edge: seller -> invoice -> buyer
        G.add_edge(inv["seller_gstin"], inv_id)
        G.add_edge(inv_id, inv["buyer_gstin"])
        
    return G

def compute_vendor_risk(G, gstin):
    # Get vendor attributes
    attrs = G.nodes[gstin]
    vendor_name = attrs.get("name", "")
    missed_filings = attrs.get("missed_filings", 0)
    
    # Incoming invoices (vendor is buyer)
    incoming_nodes = list(G.predecessors(gstin))
    incoming_invoices = [n for n in incoming_nodes if G.nodes[n].get("type") == "invoice"]
    
    # Outgoing invoices (vendor is seller)
    outgoing_nodes = list(G.successors(gstin))
    outgoing_invoices = [n for n in outgoing_nodes if G.nodes[n].get("type") == "invoice"]
    
    # Find suspicious invoices (claimed by buyer but not reported by seller)
    suspicious_invoices = []
    for inv_id in incoming_invoices:
        inv_attrs = G.nodes[inv_id]
        if inv_attrs.get("claimed_by_buyer") and not inv_attrs.get("reported_by_seller"):
            suspicious_invoices.append(inv_id)
            
    # Calculate risk score
    risk_score = len(suspicious_invoices) * 20 + missed_filings * 10
    
    # Determine risk level
    if risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 30:
        risk_level = "medium"
    else:
        risk_level = "low"
        
    return {
        "gstin": gstin,
        "name": vendor_name,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "missed_filings": missed_filings,
        "total_incoming": len(incoming_invoices),
        "total_outgoing": len(outgoing_invoices),
        "suspicious_invoices": suspicious_invoices
    }

def get_all_vendor_summaries(G):
    summaries = []
    for node, attrs in G.nodes(data=True):
        if attrs.get("type") == "vendor":
            summary = compute_vendor_risk(G, node)
            summaries.append(summary)
    return summaries

if __name__ == "__main__":
    pass
