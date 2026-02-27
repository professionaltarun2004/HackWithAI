from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from graph_logic import load_data, build_graph, get_all_vendor_summaries, compute_vendor_risk

app = FastAPI(title="GST Graph Risk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vendors, invoices = load_data()
G = build_graph(vendors, invoices)
ALL_SUMMARIES = get_all_vendor_summaries(G)

class VendorSummary(BaseModel):
    gstin: str
    name: str
    risk_level: str
    risk_score: int
    missed_filings: int
    total_incoming: int
    total_outgoing: int
    suspicious_invoices_count: int
    sample_suspicious_invoices: List[str]

def generate_ai_explanation(summary: VendorSummary) -> str:
    """
    Placeholder for real LLM integration.
    For now, generate a clear, human-readable explanation string using the summary fields.
    """
    explanation = f"An audit of vendor '{summary.name}' (GSTIN: {summary.gstin}) indicates a {summary.risk_level} risk profile with an overall score of {summary.risk_score}. "
    
    if summary.suspicious_invoices_count > 0:
        explanation += f"This elevated risk is primarily driven by {summary.suspicious_invoices_count} suspicious invoices detected out of {summary.total_incoming} total incoming transactions where input tax credit was claimed but not reported by the supplier. "
        explanation += f"Specifically, attention should be directed to the following sample invoices: {', '.join(summary.sample_suspicious_invoices)}. "
    else:
        explanation += f"Currently, all {summary.total_incoming} incoming transactions appear to be matched properly with supplier filings. "
        
    if summary.missed_filings > 0:
        explanation += f"Additionally, the vendor's compliance history shows {summary.missed_filings} missed return filings, which contributes further to their risk assessment."
    else:
        explanation += "The vendor has maintained a good compliance record with no recently missed return filings."
        
    return explanation

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/vendors")
def get_vendors():
    result = []
    for summary in ALL_SUMMARIES:
        result.append({
            "gstin": summary["gstin"],
            "name": summary["name"],
            "risk_score": summary["risk_score"],
            "risk_level": summary["risk_level"],
            "missed_filings": summary["missed_filings"],
            "total_incoming": summary["total_incoming"],
            "total_outgoing": summary["total_outgoing"]
        })
    return result

@app.get("/vendors/{gstin}")
def get_vendor(gstin: str):
    if gstin not in G or G.nodes[gstin].get("type") != "vendor":
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    summary = compute_vendor_risk(G, gstin)
    
    suspicious_invoices_details = []
    for inv_id in summary["suspicious_invoices"]:
        inv_attrs = G.nodes[inv_id]
        suspicious_invoices_details.append({
            "invoice_id": inv_id,
            "seller_gstin": inv_attrs.get("seller_gstin"),
            "buyer_gstin": inv_attrs.get("buyer_gstin"),
            "amount": inv_attrs.get("amount"),
            "tax": inv_attrs.get("tax"),
            "reported_by_seller": inv_attrs.get("reported_by_seller"),
            "claimed_by_buyer": inv_attrs.get("claimed_by_buyer")
        })
        
    summary["suspicious_invoices_details"] = suspicious_invoices_details
    return summary

@app.get("/vendors/{gstin}/summary")
def get_vendor_summary(gstin: str):
    if gstin not in G or G.nodes[gstin].get("type") != "vendor":
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    summary = compute_vendor_risk(G, gstin)
    
    return {
        "gstin": summary["gstin"],
        "name": summary["name"],
        "risk_level": summary["risk_level"],
        "risk_score": summary["risk_score"],
        "missed_filings": summary["missed_filings"],
        "total_incoming": summary["total_incoming"],
        "total_outgoing": summary["total_outgoing"],
        "suspicious_invoices_count": len(summary["suspicious_invoices"]),
        "sample_suspicious_invoices": summary["suspicious_invoices"][:5]
    }

@app.get("/vendors/{gstin}/ai-explanation")
def get_vendor_ai_explanation(gstin: str):
    if gstin not in G or G.nodes[gstin].get("type") != "vendor":
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    raw_summary = compute_vendor_risk(G, gstin)
    
    summary_data = {
        "gstin": raw_summary["gstin"],
        "name": raw_summary["name"],
        "risk_level": raw_summary["risk_level"],
        "risk_score": raw_summary["risk_score"],
        "missed_filings": raw_summary["missed_filings"],
        "total_incoming": raw_summary["total_incoming"],
        "total_outgoing": raw_summary["total_outgoing"],
        "suspicious_invoices_count": len(raw_summary["suspicious_invoices"]),
        "sample_suspicious_invoices": raw_summary["suspicious_invoices"][:5]
    }
    
    vendor_summary = VendorSummary(**summary_data)
    explanation = generate_ai_explanation(vendor_summary)
    
    return {
        "gstin": vendor_summary.gstin,
        "name": vendor_summary.name,
        "risk_level": vendor_summary.risk_level,
        "risk_score": vendor_summary.risk_score,
        "explanation": explanation
    }

@app.get("/graph")
def get_graph_data():
    """Return all nodes and edges for frontend graph visualization."""
    nodes = []
    edges = []

    for node, attrs in G.nodes(data=True):
        node_data = {"id": node, "type": attrs.get("type", "unknown")}
        if attrs.get("type") == "vendor":
            summary = compute_vendor_risk(G, node)
            node_data.update({
                "name": attrs.get("name", ""),
                "risk_level": summary["risk_level"],
                "risk_score": summary["risk_score"],
                "missed_filings": attrs.get("missed_filings", 0),
                "suspicious_count": len(summary["suspicious_invoices"]),
            })
        elif attrs.get("type") == "invoice":
            is_suspicious = bool(attrs.get("claimed_by_buyer") and not attrs.get("reported_by_seller"))
            node_data.update({
                "amount": attrs.get("amount", 0),
                "tax": attrs.get("tax", 0),
                "seller_gstin": attrs.get("seller_gstin", ""),
                "buyer_gstin": attrs.get("buyer_gstin", ""),
                "reported_by_seller": attrs.get("reported_by_seller", False),
                "claimed_by_buyer": attrs.get("claimed_by_buyer", False),
                "is_suspicious": is_suspicious,
            })
        nodes.append(node_data)

    for source, target in G.edges():
        edges.append({"source": source, "target": target})

    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
