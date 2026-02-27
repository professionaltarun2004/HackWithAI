import random

random.seed(42)

# Generate Vendors
vendors = []
names = [
    "Alpha Traders", "Beta Suppliers", "Gamma Enterprises", "Delta Corp",
    "Epsilon Logistics", "Zeta Imports", "Eta Exports", "Theta Solutions",
    "Iota Manufacturing", "Kappa Services", "Lambda Distributors", "Mu Holdings",
    "Nu Resources", "Xi Ventures", "Omicron Group"
]
chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def generate_gstin():
    return "".join(random.choices(chars, k=15))

for i in range(15):
    gstin = generate_gstin()
    name = names[i]
    missed_filings = random.choices([0, 1, 2, 3, 4], weights=[40, 30, 15, 10, 5], k=1)[0]
    vendors.append({
        "gstin": gstin,
        "name": name,
        "missed_filings": missed_filings
    })

circ_vendors = vendors[:3] # A, B, C
A, B, C = circ_vendors[0]['gstin'], circ_vendors[1]['gstin'], circ_vendors[2]['gstin']

invoices = []
invoice_count = 1

def make_invoice(seller, buyer, amount, reported, claimed):
    global invoice_count
    inv_id = f"INV{invoice_count:03d}"
    invoice_count += 1
    return {
        "invoice_id": inv_id,
        "seller_gstin": seller,
        "buyer_gstin": buyer,
        "amount": amount,
        "tax": round(amount * 0.18),
        "reported_by_seller": str(reported).lower(),
        "claimed_by_buyer": str(claimed).lower()
    }

circ_patterns = [
    (A, B), (A, B),
    (B, C), (B, C),
    (C, A), (C, A)
]
for seller, buyer in circ_patterns:
    amount = random.randint(150000, 200000)
    if random.random() < 0.5:
        reported, claimed = False, True
    else:
        reported, claimed = True, True
    invoices.append(make_invoice(seller, buyer, amount, reported, claimed))

def pick_buyer(seller):
    buyer = seller
    while buyer == seller:
        buyer = random.choice(vendors)['gstin']
    return buyer

# Generate Normal (81 invoices)
for _ in range(81):
    seller = random.choice(vendors)['gstin']
    buyer = pick_buyer(seller)
    amount = random.randint(5000, 100000)
    invoices.append(make_invoice(seller, buyer, amount, True, True))

# Generate Suspicious (21 invoices)
weights = [v['missed_filings'] + 1 for v in vendors]
for _ in range(21):
    seller_obj = random.choices(vendors, weights=weights, k=1)[0]
    seller = seller_obj['gstin']
    buyer = pick_buyer(seller)
    amount = random.randint(50000, 150000)
    invoices.append(make_invoice(seller, buyer, amount, False, True))

# Generate Other (12 invoices)
for _ in range(12):
    seller = random.choice(vendors)['gstin']
    buyer = pick_buyer(seller)
    amount = random.randint(5000, 50000)
    if random.random() < 0.5:
        invoices.append(make_invoice(seller, buyer, amount, False, False))
    else:
        invoices.append(make_invoice(seller, buyer, amount, True, False))

with open("vendors.csv", "w") as f:
    f.write("gstin,name,missed_filings\n")
    for v in vendors:
        f.write(f"{v['gstin']},{v['name']},{v['missed_filings']}\n")

with open("invoices.csv", "w") as f:
    f.write("invoice_id,seller_gstin,buyer_gstin,amount,tax,reported_by_seller,claimed_by_buyer\n")
    for inv in invoices:
        f.write(f"{inv['invoice_id']},{inv['seller_gstin']},{inv['buyer_gstin']},{inv['amount']},{inv['tax']},{inv['reported_by_seller']},{inv['claimed_by_buyer']}\n")
