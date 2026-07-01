"""
utils/parser.py
================
Responsibility: Parse and validate Purchase Orders (POs).

Contains two functions:
    1. extract_po_data(po_text)  -> Extract structured data from raw PO text using Z AI (GLM).
    2. validate_po(extracted)    -> Validate extracted PO data against product & contract CSVs.

Dependencies (per requirements.txt): pandas, openai
"""

import os
import json
import io
import pandas as pd
import pdfplumber
from openai import OpenAI


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# --- Lightweight .env loader (stdlib only, no python-dotenv needed) ---------
# Reads a .env file from the project root and sets values ONLY if the
# environment variable is not already present. This makes the API key work
# from any terminal without relying on system-level env vars.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_PROJECT_ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            # Skip blank lines and comments.
            if not _line or _line.startswith("#"):
                continue
            if "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip().strip('"').strip("'")
                os.environ.setdefault(_k, _v)

# Read the API key from the environment (set above by .env loader or by the OS).
GLM_API_KEY = os.environ.get("GLM_API_KEY", "YOUR_GLM_API_KEY")

# Configure the OpenAI-compatible client to point at Z AI's endpoint.
client = OpenAI(api_key=GLM_API_KEY, base_url="https://api.z.ai/api/paas/v4/")

# Use the free GLM model for structured extraction tasks.
MODEL_NAME = "glm-4.5-flash"

# Resolve CSV paths relative to the project root (already computed above).
PRODUCTS_CSV = os.path.join(_PROJECT_ROOT, "data", "products.csv")
CONTRACTS_CSV = os.path.join(_PROJECT_ROOT, "data", "contracts.csv")


# ---------------------------------------------------------------------------
# 0) PDF HELPER  --  PDF bytes  ->  plain text
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF file given its raw bytes."""
    text_pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_pages.append(page_text)
    return "\n".join(text_pages)


# ---------------------------------------------------------------------------
# 1) EXTRACTION  --  PO text  ->  structured dict (via Z AI / GLM)
# ---------------------------------------------------------------------------

def extract_po_data(po_text: str) -> dict:
    """
    Send raw Purchase Order text to Z AI (GLM) and extract structured fields.

    Args:
        po_text (str): The full text content of a Purchase Order document.

    Returns:
        dict: {
            "customer_id": "C001",
            "customer_name": "Acme Corp",
            "po_number": "PO-2024-0001",
            "requested_delivery_date": "July 15, 2024",
            "line_items": [
                {"sku": "WM-001", "quantity": 10, "unit_price": 12.99},
                ...
            ]
        }
    """

    extraction_prompt = f"""
You are an expert Purchase Order analyst. Extract ALL relevant business information from the PO below.

The PO may be written in ANY language (Arabic, Chinese, German, Urdu, French, Spanish, etc.).
Extract everything and return ALL field names in English.

Return this exact JSON structure (use null for missing fields):
{{
  "language": "detected language of the PO",
  "po_number": "PO reference number",
  "po_date": "date as written",
  "currency": "currency code (USD, EUR, SAR, PKR, GBP, etc.)",
  "customer_id": "buyer ID or code if present",
  "customer_name": "buyer company name",
  "customer_address": "buyer full address",
  "customer_email": "buyer email if present",
  "customer_phone": "buyer phone if present",
  "vendor_name": "seller/vendor company name",
  "ship_to_address": "delivery/shipping address",
  "requested_delivery_date": "delivery date as written",
  "payment_terms": "e.g. Net 30, COD, advance, etc.",
  "shipping_terms": "e.g. FOB, CIF, DDP, etc.",
  "subtotal": numeric subtotal or null,
  "tax_amount": numeric tax or null,
  "shipping_cost": numeric shipping cost or null,
  "grand_total": numeric grand total or null,
  "special_instructions": "any notes, conditions, or special instructions",
  "line_items": [
    {{
      "line_number": integer or null,
      "sku": "product code / item number / SKU",
      "description": "product description",
      "quantity": numeric quantity,
      "unit_of_measure": "pcs / kg / meters / boxes / liters / etc.",
      "unit_price": numeric unit price,
      "line_total": numeric line total or null
    }}
  ],
  "additional_fields": {{}}
}}

Rules:
  1. Return ONLY valid JSON. No markdown fences, no extra text.
  2. All prices and quantities must be numbers, no symbols.
  3. If you find any important fields not in the schema, put them in additional_fields.

Purchase Order text:
\"\"\"
{po_text}
\"\"\"
"""

    # Call the Z AI (OpenAI-compatible) Chat Completions API and parse JSON.
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a data extraction assistant. Return ONLY valid JSON.",
            },
            {"role": "user", "content": extraction_prompt},
        ],
        temperature=0,
    )

    # Parse the JSON response into a Python dict.
    raw_text = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps JSON in them.
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
        raw_text = raw_text.strip()

    extracted_data = json.loads(raw_text)

    return extracted_data


# ---------------------------------------------------------------------------
# 2) VALIDATION  --  extracted dict  ->  validated dict + flags
# ---------------------------------------------------------------------------

def validate_po(extracted_data: dict) -> dict:
    """
    Validate extracted PO data against the product catalog and customer contracts.

    Checks performed:
      - Each line item's SKU exists in data/products.csv
      - The unit price in the PO matches the catalog price
      - Available stock is sufficient for the requested quantity
      - The customer_id exists in data/contracts.csv

    Args:
        extracted_data (dict): Output of extract_po_data().

    Returns:
        dict: {
            "validated_items": [
                {
                    "sku": "WM-001",
                    "quantity": 10,
                    "unit_price": 12.99,
                    "status": "valid" | "invalid",
                    "issues": ["Price mismatch...", ...]
                },
                ...
            ],
            "flags": [
                "SKU WM-001 not found in product catalog",
                ...
            ]
        }
    """

    # --- Load reference data -------------------------------------------------
    products  = pd.read_csv(PRODUCTS_CSV)
    contracts = pd.read_csv(CONTRACTS_CSV)

    products_by_sku = products.set_index("sku")

    flags          = []
    validated_items = []

    # --- Resolve customer discount ------------------------------------------
    customer_id  = extracted_data.get("customer_id")
    discount_pct = 0.0
    customer_found = False

    if customer_id:
        customer_rows = contracts[contracts["customer_id"] == customer_id]
        if not customer_rows.empty:
            customer_found = True
            discount_pct = float(customer_rows.iloc[0].get("agreed_discount", 0) or 0)
        else:
            flags.append(f"Customer ID '{customer_id}' not found in contracts")

    # --- Validate each line item --------------------------------------------
    line_items = extracted_data.get("line_items", []) or []

    for item in line_items:
        sku        = item.get("sku")
        quantity   = item.get("quantity")
        unit_price = item.get("unit_price")

        item_issues = []

        if not sku:
            item_issues.append("Missing SKU")
        elif sku not in products_by_sku.index:
            item_issues.append(f"SKU '{sku}' not found in product catalog")
        else:
            product_row    = products_by_sku.loc[sku]
            catalog_price  = round(float(product_row["price"]), 2)
            expected_price = round(catalog_price * (1 - discount_pct / 100), 2)
            po_price       = round(float(unit_price), 2)

            if po_price != expected_price:
                if discount_pct > 0:
                    item_issues.append(
                        f"Price mismatch for {sku}: PO=${po_price:.2f}, "
                        f"Expected=${expected_price:.2f} "
                        f"(catalog=${catalog_price:.2f} minus {discount_pct:.0f}% discount)"
                    )
                else:
                    item_issues.append(
                        f"Price mismatch for {sku}: PO=${po_price:.2f}, Catalog=${catalog_price:.2f}"
                    )

            available_stock = int(product_row["stock"])
            if quantity and quantity > available_stock:
                item_issues.append(
                    f"Insufficient stock for {sku}: requested {quantity}, available {available_stock}"
                )

        status = "valid" if not item_issues else "invalid"
        validated_items.append({
            "sku":         sku,
            "description": item.get("description"),
            "quantity":    quantity,
            "uom":         item.get("unit_of_measure"),
            "unit_price":  unit_price,
            "line_total":  item.get("line_total"),
            "status":      status,
            "issues":      item_issues,
        })
        flags.extend(item_issues)

    return {
        "validated_items":  validated_items,
        "flags":            flags,
        "discount_applied": discount_pct,
        "customer_found":   customer_found,
    }