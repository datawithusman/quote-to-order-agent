# Quote-to-Order AI Agent

An AI-powered Purchase Order processing agent built with Python, Streamlit, and GLM (Z AI).

Upload a PO as PDF or TXT and the agent automatically extracts line items, cross-checks them against your product catalog and contracts, and flags any issues before the order is confirmed.

---

## What it does

- Extracts structured data from raw PO documents (PDF or TXT) using an LLM
- Validates each line item against a product catalog (SKU, price, stock)
- Flags pricing mismatches, stock shortages, and unknown SKUs
- Shows a color-coded result dashboard with per-item status
- Exports a validation report as CSV

## Demo

Upload a clean PO:

> All checks passed. This PO is ready to process.

Upload a PO with errors:

> 3 issue(s) found:
> - Price mismatch for SKU-1003: PO=$250.00, Catalog=$289.00
> - Insufficient stock for SKU-1003: requested 40, available 25
> - SKU SKU-9999 not found in product catalog

---

## Tech stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| AI brain | GLM-4.5-Flash via Z AI (api.z.ai) |
| Data | Local CSV files (products, contracts) |
| PDF parsing | pdfplumber |
| Language | Python 3.10+ |

---

## Project structure

```
quote-to-order-agent/
├── app.py                  # Streamlit UI
├── utils/
│   └── parser.py           # LLM extraction + CSV validation logic
├── data/
│   ├── products.csv        # Product catalog (SKU, price, stock)
│   └── contracts.csv       # Customer contracts (discount, lead time)
├── sample_pos/
│   ├── po_001.txt          # Clean PO (all checks pass)
│   ├── po_002.txt          # PO with 3 errors (price, stock, unknown SKU)
│   └── po_003.html         # Printable PO template (save as PDF to test)
├── requirements.txt
└── .env                    # API key (not committed)
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/quote-to-order-agent.git
cd quote-to-order-agent
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API key**

Create a `.env` file in the project root:
```
GLM_API_KEY=your_key_here
```

Get a free key at [api.z.ai](https://api.z.ai)

**4. Run the app**
```bash
streamlit run app.py
```

---

## Validation logic

Each line item in the PO is checked against `data/products.csv`:

| Check | Pass condition |
|---|---|
| SKU exists | SKU found in catalog |
| Price match | PO price == catalog price |
| Stock check | Requested qty <= available stock |
| Customer ID | Customer found in contracts.csv |

---

## Sample data

`data/products.csv` contains 7 sample products. `data/contracts.csv` contains 6 sample customers. Replace with your real ERP data to use in production.

---

Built as part of a Build in Public series on LinkedIn.
