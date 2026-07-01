# Quote-to-Order AI Agent

An AI-powered Purchase Order processing agent built with Python, Streamlit, and GLM (Z AI).

Upload a PO in **any language** (English, Arabic, German, Urdu, Chinese, French & more) as PDF or TXT, and the agent automatically extracts all structured data, cross-checks line items against your product catalog and customer contracts, applies contracted discounts, and flags any issues before the order is confirmed.

---

## What it does

- 🌐 **Multi-language** — Processes POs written in any language; returns structured data in English
- 💱 **Currency-aware** — Auto-detects currency (USD, EUR, SAR, PKR, GBP, etc.)
- 🧾 **Full extraction** — Extracts PO metadata, financial totals, line items, shipping info, and special instructions
- ✅ **Smart validation** — Checks SKU existence, contracted pricing (with discount), stock availability, and customer verification
- 📊 **Styled dashboard** — Color-coded per-item status cards with issue highlighting
- 📄 **CSV export** — Download a full validation report with one click

## Demo

Upload a clean PO:

> ✅ All checks passed. This PO is ready to process.

Upload a PO with errors:

> 🔴 3 issue(s) found:
> - Price mismatch for SKU-1003: PO=$250.00, Expected=$275.55 (catalog=$289.00 minus 5% discount)
> - Insufficient stock for SKU-1003: requested 40, available 25
> - SKU 'SKU-9999' not found in product catalog

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
├── app.py                  # Streamlit UI (dashboard, upload, export)
├── utils/
│   └── parser.py           # LLM extraction + CSV validation logic
├── data/
│   ├── products.csv        # Product catalog (SKU, price, stock)
│   └── contracts.csv       # Customer contracts (discount, lead time)
├── sample_pos/
│   ├── po_001.txt          # Clean PO (all checks pass)
│   ├── po_002.txt          # PO with errors (price, stock, unknown SKU)
│   ├── po_003.html         # Printable PO template (save as PDF to test)
│   ├── po_003.pdf          # Sample PDF for testing
│   └── po_arabic.html      # Multi-language test (Arabic PO)
├── requirements.txt
└── .env                    # API key (not committed)
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/datawithusman/quote-to-order-agent.git
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

> **Note:** No `python-dotenv` required — the app has a built-in `.env` loader using only the Python standard library.

**4. Run the app**
```bash
streamlit run app.py
```

---

## Validation logic

Each line item in the PO is checked against `data/products.csv`:

| Check | Pass condition |
|---|---|
| SKU exists | SKU found in product catalog |
| Price match | PO price == contracted price (catalog price minus customer's agreed discount %) |
| Stock check | Requested qty <= available stock |
| Customer ID | Customer found in `contracts.csv` |

**Discount example:** If a customer has a 10% agreed discount and the catalog price is $100, the expected PO price is $90. The agent verifies the PO matches this contracted rate.

---

## Extracted fields

The agent extracts the following from any PO:

| Category | Fields |
|---|---|
| **Header** | PO number, PO date, currency, language |
| **Customer** | Customer ID, name, address, email, phone |
| **Vendor** | Vendor/seller name |
| **Delivery** | Ship-to address, requested delivery date |
| **Terms** | Payment terms, shipping terms |
| **Financials** | Subtotal, tax, shipping cost, grand total |
| **Line items** | SKU, description, quantity, unit of measure, unit price, line total |
| **Other** | Special instructions, additional fields |

---

## Sample data

`data/products.csv` contains 7 sample products. `data/contracts.csv` contains 6 sample customers. Replace with your real ERP data to use in production.

---

Built as part of a Build in Public series on LinkedIn.