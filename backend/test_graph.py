from graph_logic import load_data, build_graph, get_all_vendor_summaries, compute_vendor_risk

if __name__ == "__main__":
    vendors, invoices = load_data()
    G = build_graph(vendors, invoices)
    
    summaries = get_all_vendor_summaries(G)
    for summary in summaries:
        print(summary)
        
    if vendors:
        first_gstin = vendors[0]["gstin"]
        print(f"\nDETAIL FOR {first_gstin}")
        detail = compute_vendor_risk(G, first_gstin)
        print(detail)
