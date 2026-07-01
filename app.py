"""
app.py
======
Streamlit UI for the Quote-to-Order AI Agent.

Flow:
    Upload PO (.txt or .pdf)  ->  Extract text  ->  GLM extracts fields
    ->  Validate against CSVs  ->  Show results + download report
"""

import os
import csv
import io
import streamlit as st

from utils.parser import extract_po_data, extract_text_from_pdf, validate_po


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Quote-to-Order AI Agent",
    page_icon="🧾",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global */
    .stApp { background-color: #f0f2f6; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #1a1f2e; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] h2 { color: #ffffff !important; font-size: 18px; }
    [data-testid="stSidebar"] .stDivider { border-color: #334155; }

    /* Page title */
    .page-title {
        font-size: 28px;
        font-weight: 700;
        color: #1a1f2e;
        margin-bottom: 4px;
    }
    .page-subtitle {
        font-size: 15px;
        color: #64748b;
        margin-bottom: 24px;
    }

    /* Summary cards */
    .card {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.07);
        height: 100%;
    }
    .card .card-label {
        font-size: 11px;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 10px;
    }
    .card .card-value {
        font-size: 20px;
        font-weight: 700;
        color: #1a1f2e;
        word-break: break-word;
        line-height: 1.3;
    }
    .card .card-sub {
        font-size: 13px;
        color: #64748b;
        margin-top: 4px;
    }
    .card-flagged .card-value { color: #dc2626; }
    .card-approved .card-value { color: #16a34a; }

    /* Section header */
    .section-header {
        font-size: 16px;
        font-weight: 700;
        color: #1a1f2e;
        margin: 28px 0 14px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    /* PO detail row */
    .detail-grid {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    }
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #f1f5f9;
        font-size: 14px;
    }
    .detail-row:last-child { border-bottom: none; }
    .detail-key { color: #64748b; font-weight: 500; }
    .detail-val { color: #1a1f2e; font-weight: 600; }

    /* Line item cards */
    .line-item {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 5px solid #e2e8f0;
    }
    .line-item.valid   { border-left-color: #22c55e; }
    .line-item.invalid { border-left-color: #ef4444; }

    .line-item-top {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    .li-sku {
        font-size: 15px;
        font-weight: 700;
        color: #1a1f2e;
        min-width: 110px;
    }
    .li-meta {
        font-size: 13px;
        color: #64748b;
        background: #f8fafc;
        padding: 4px 10px;
        border-radius: 6px;
    }
    .badge-valid {
        background: #dcfce7;
        color: #166534;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 999px;
        margin-left: auto;
    }
    .badge-invalid {
        background: #fee2e2;
        color: #991b1b;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 999px;
        margin-left: auto;
    }
    .li-issues {
        margin-top: 10px;
        font-size: 13px;
        color: #b91c1c;
        background: #fff5f5;
        border-radius: 8px;
        padding: 8px 12px;
        line-height: 1.6;
    }

    /* Flag boxes */
    .flag-item {
        background: #ffffff;
        border-left: 5px solid #ef4444;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
        font-size: 14px;
        color: #7f1d1d;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .flag-icon { margin-right: 8px; }

    /* Success banner */
    .success-banner {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 18px 22px;
        font-size: 15px;
        color: #14532d;
        font-weight: 600;
    }

    /* Upload area */
    .upload-hint {
        text-align: center;
        padding: 60px 20px;
        color: #94a3b8;
    }
    .upload-hint .icon { font-size: 52px; margin-bottom: 12px; }
    .upload-hint .title { font-size: 18px; font-weight: 600; color: #64748b; margin-bottom: 6px; }
    .upload-hint .sub { font-size: 14px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧾 Quote-to-Order")
    st.markdown("*AI-powered PO processing*")
    st.divider()

    api_key = os.environ.get("GLM_API_KEY", "")
    if not api_key or api_key == "YOUR_GLM_API_KEY":
        st.warning("⚠️ API key not set.")
    else:
        st.success("✅ API Key Connected")

    st.divider()
    st.markdown("**Supported formats**")
    st.markdown("📄 PDF (.pdf)")
    st.markdown("📝 Plain text (.txt)")

    st.divider()
    st.markdown("**Validation checks**")
    st.markdown("✔ SKU exists in catalog")
    st.markdown("✔ Price matches contract")
    st.markdown("✔ Stock availability")
    st.markdown("✔ Customer ID verified")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="page-title">🧾 Quote-to-Order AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Upload a Purchase Order to extract line items and validate against your catalog and contracts.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload Purchase Order",
    type=["txt", "pdf"],
    label_visibility="collapsed",
)

if uploaded_file is None:
    st.markdown("""
    <div class="upload-hint">
        <div class="icon">📂</div>
        <div class="title">Drop a Purchase Order here</div>
        <div class="sub">Supports PDF and TXT formats • Max 200MB</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ---------------------------------------------------------------------------
# Read file -> plain text
# ---------------------------------------------------------------------------
file_bytes = uploaded_file.read()

if uploaded_file.name.lower().endswith(".pdf"):
    with st.spinner("Reading PDF..."):
        try:
            po_text = extract_text_from_pdf(file_bytes)
        except Exception as e:
            st.error(f"Could not read PDF: {e}")
            st.stop()
else:
    try:
        po_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        po_text = file_bytes.decode("latin-1")

if not po_text.strip():
    st.error("The file appears to be empty or unreadable.")
    st.stop()


# ---------------------------------------------------------------------------
# Extract + Validate
# ---------------------------------------------------------------------------
with st.spinner("Extracting and validating PO..."):
    try:
        extracted = extract_po_data(po_text)
        result    = validate_po(extracted)
    except Exception as e:
        st.error(f"Processing failed: {e}")
        st.stop()

line_items      = extracted.get("line_items", []) or []
flags           = result.get("flags", [])
validated_items = result.get("validated_items", [])

total_value    = sum((i.get("quantity") or 0) * (i.get("unit_price") or 0) for i in line_items)
invalid_count  = sum(1 for i in validated_items if i.get("status") == "invalid")
valid_count    = sum(1 for i in validated_items if i.get("status") == "valid")
overall_status = "APPROVED" if not flags else "FLAGGED"
status_class   = "card-approved" if not flags else "card-flagged"


# ---------------------------------------------------------------------------
# Summary cards  (2 x 2 grid)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Summary</div>', unsafe_allow_html=True)

r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)

with r1c1:
    st.markdown(f"""
    <div class="card">
        <div class="card-label">PO Number</div>
        <div class="card-value">{extracted.get("po_number", "N/A")}</div>
        <div class="card-sub">{extracted.get("customer_id", "")}</div>
    </div>""", unsafe_allow_html=True)

with r1c2:
    st.markdown(f"""
    <div class="card">
        <div class="card-label">Customer</div>
        <div class="card-value">{extracted.get("customer_name", "N/A")}</div>
        <div class="card-sub">Delivery: {extracted.get("requested_delivery_date", "N/A")}</div>
    </div>""", unsafe_allow_html=True)

with r2c1:
    st.markdown(f"""
    <div class="card">
        <div class="card-label">Total PO Value</div>
        <div class="card-value">${total_value:,.2f}</div>
        <div class="card-sub">{len(line_items)} line item(s)</div>
    </div>""", unsafe_allow_html=True)

with r2c2:
    st.markdown(f"""
    <div class="card {status_class}">
        <div class="card-label">Status</div>
        <div class="card-value">{overall_status}</div>
        <div class="card-sub">{len(flags)} issue(s) found &nbsp;|&nbsp; {valid_count} item(s) valid</div>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Line items
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Line Items</div>', unsafe_allow_html=True)

if validated_items:
    for item in validated_items:
        status     = item.get("status", "invalid")
        issues     = item.get("issues", [])
        badge_html = (
            '<span class="badge-valid">✓ Valid</span>'
            if status == "valid"
            else '<span class="badge-invalid">✗ Invalid</span>'
        )
        issues_html = ""
        if issues:
            issues_list = "".join(f"• {iss}<br>" for iss in issues)
            issues_html = f'<div class="li-issues">{issues_list}</div>'

        st.markdown(f"""
        <div class="line-item {status}">
            <div class="line-item-top">
                <span class="li-sku">{item.get("sku")}</span>
                <span class="li-meta">Qty: {item.get("quantity")}</span>
                <span class="li-meta">${item.get("unit_price", 0):.2f} / unit</span>
                {badge_html}
            </div>
            {issues_html}
        </div>""", unsafe_allow_html=True)
else:
    st.info("No line items found.")


# ---------------------------------------------------------------------------
# Validation results
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Validation Results</div>', unsafe_allow_html=True)

if not flags:
    st.markdown("""
    <div class="success-banner">
        ✅ All checks passed. This PO is ready to process.
    </div>""", unsafe_allow_html=True)
else:
    for flag in flags:
        st.markdown(f'<div class="flag-item"><span class="flag-icon">🔴</span>{flag}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Download report
# ---------------------------------------------------------------------------
st.markdown('<div class="section-header">Export Report</div>', unsafe_allow_html=True)

if validated_items:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["sku", "quantity", "unit_price", "status", "issues"],
    )
    writer.writeheader()
    for item in validated_items:
        writer.writerow({
            "sku":        item.get("sku"),
            "quantity":   item.get("quantity"),
            "unit_price": item.get("unit_price"),
            "status":     item.get("status"),
            "issues":     " | ".join(item.get("issues", [])),
        })

    po_number = extracted.get("po_number", "report").replace("/", "-")
    st.download_button(
        label="⬇️  Download Validation Report (CSV)",
        data=output.getvalue(),
        file_name=f"{po_number}_validation.csv",
        mime="text/csv",
    )
