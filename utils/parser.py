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

    # Instruction for GLM: extract exactly these fields, output as JSON.
    extraction_prompt = f"""
You are a data extraction assistant for a Quote-to-Order system.

Read the Purchase Order (PO) text below and extract the following fields:
  - customer_id            (string)
  - customer_name          (string)
  - po_number              (string)
  - requested_delivery_date (string, as written in the PO)
  - line_items             (list of objects)
        each object: sku (string), quantity (integer), unit_price (number)

Rules:
  1. Return ONLY valid JSON. No extra text, no markdown fences.
  2. If a field is missing, use null.
  3. Quantities must be integers (no units like "pcs").
  4. Unit prices must be numbers (no currency symbols).

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
    products = pd.read_csv(PRODUCTS_CSV)
    contracts = pd.read_csv(CONTRACTS_CSV)

    # Index products by SKU for quick lookup.
    products_by_sku = products.set_index("sku")

    flags = []          # Global list of all exceptions/warnings.
    validated_items = []  # Per-item results.

    # --- Validate each line item --------------------------------------------
    line_items = extracted_data.get("line_items", []) or []

    for item in line_items:
        sku = item.get("sku")
        quantity = item.get("quantity")
        unit_price = item.get("unit_price")

        item_issues = []

        # (a) Does the SKU exist in the catalog?
        if sku not in products_by_sku.index:
            item_issues.append(f"SKU {sku} not found in product catalog")

        else:
            product_row = products_by_sku.loc[sku]

            # (b) Does the price match? (rounded to 2 decimals for tolerance)
            catalog_price = round(float(product_row["price"]), 2)
            po_price = round(float(unit_price), 2)

            if catalog_price != po_price:
                item_issues.append(
                    f"Price mismatch for {sku}: PO=${po_price:.2f}, Catalog=${catalog_price:.2f}"
                )

            # (c) Is stock sufficient for the requested quantity?
            available_stock = int(product_row["stock"])
            if quantity > available_stock:
                item_issues.append(
                    f"Insufficient stock for {sku}: requested {quantity}, available {available_stock}"
                )

        # Record the outcome for this item.
        status = "valid" if not item_issues else "invalid"
        validated_items.append({
            "sku": sku,
            "quantity": quantity,
            "unit_price": unit_price,
            "status": status,
            "issues": item_issues,
        })

        # Merge per-item issues into the global flags list.
        flags.extend(item_issues)

    # --- Validate customer --------------------------------------------------
    customer_id = extracted_data.get("customer_id")

    if customer_id not in contracts["customer_id"].values:
        flags.append(f"Customer ID {customer_id} not found in contracts")

    return {
        "validated_items": validated_items,
        "flags": flags,
    }