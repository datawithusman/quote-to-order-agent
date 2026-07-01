"""
app.py  —  Quote-to-Order AI Agent
Streamlit UI: upload any PO (PDF/TXT, any language) → extract all fields → validate → report
"""

import os
import csv
import io
import streamlit as st

from utils.parser import extract_po_data, extract_text_from_pdf, validate_po


st.set_page_config(page_title="Quote-to-Order AI Agent", page_icon="🧾", layout="wide")


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    [data-testid="stSidebar"] { background-color: #1a1f2e; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    .page-title { font-size: 26px; font-weight: 700; color: #1a1f2e; margin-bottom: 4px; }
    .page-sub   { font-size: 14px; color: #64748b; margin-bottom: 20px; }

    .card {
        background: #fff; border-radius: 14px; padding: 18px 22px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.07); height: 100%;
    }
    .card .lbl { font-size: 11px; font-weight: 600; color: #94a3b8;
                 text-transform: uppercase; letter-spacing: .07em; margin-bottom: 8px; }
    .card .val { font-size: 19px; font-weight: 700; color: #1a1f2e;
                 word-break: break-word; line-height: 1.3; }
    .card .sub { font-size: 12px; color: #64748b; margin-top: 4px; }
    .card-red .val   { color: #dc2626; }
    .card-green .val { color: #16a34a; }

    .sec { font-size: 15px; font-weight: 700; color: #1a1f2e;
           margin: 24px 0 12px; padding-bottom: 6px;
           border-bottom: 2px solid #e2e8f0; }

    .meta-box {
        background: #fff; border-radius: 12px; padding: 18px 22px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.07);
    }
    .meta-row { display: flex; justify-content: space-between;
                padding: 7px 0; border-bottom: 1px solid #f1f5f9;
                font-size: 13px; }
    .meta-row:last-child { border-bottom: none; }
    .mk { color: #64748b; font-weight: 500; }
    .mv { color: #1a1f2e; font-weight: 600; text-align: right; max-width: 60%; }

    .fin-box {
        background: #1a1f2e; border-radius: 12px; padding: 18px 22px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.07);
    }
    .fin-row { display: flex; justify-content: space-between;
               padding: 6px 0; font-size: 13px; color: #94a3b8;
               border-bottom: 1px solid #2d3748; }
    .fin-row:last-child { border-bottom: none; }
    .fin-total { color: #fff !important; font-size: 16px !important;
                 font-weight: 700 !important; padding-top: 10px !important; }
    .fin-val { color: #e2e8f0; font-weight: 600; }

    .li-card {
        background: #fff; border-radius: 12px; padding: 14px 18px;
        margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 5px solid #e2e8f0;
    }
    .li-card.valid   { border-left-color: #22c55e; }
    .li-card.invalid { border-left-color: #ef4444; }
    .li-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .li-sku  { font-size: 14px; font-weight: 700; color: #1a1f2e; min-width: 100px; }
    .li-desc { font-size: 13px; color: #475569; flex: 1; }
    .li-meta { font-size: 12px; color: #64748b; background: #f8fafc;
               padding: 3px 9px; border-radius: 6px; white-space: nowrap; }
    .badge-v { background:#dcfce7; color:#166534; font-size:11px; font-weight:700;
               padding:3px 10px; border-radius:999px; white-space:nowrap; }
    .badge-i { background:#fee2e2; color:#991b1b; font-size:11px; font-weight:700;
               padding:3px 10px; border-radius:999px; white-space:nowrap; }
    .li-issues { margin-top: 8px; font-size: 12px; color: #b91c1c;
                 background: #fff5f5; border-radius: 8px; padding: 8px 12px;
                 line-height: 1.7; }

    .flag-box { background: #fff; border-left: 5px solid #ef4444; border-radius: 10px;
                padding: 12px 16px; margin-bottom: 8px; font-size: 13px;
                color: #7f1d1d; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
    .ok-box   { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px;
                padding: 16px 20px; font-size: 14px; color: #14532d; font-weight: 600; }

    .lang-badge { display: inline-block; background: #ede9fe; color: #5b21b6;
                  font-size: 11px; font-weight: 700; padding: 3px 10px;
                  border-radius: 999px; margin-right: 6px; }
    .curr-badge { display: inline-block; background: #fef3c7; color: #92400e;
                  font-size: 11px; font-weight: 700; padding: 3px 10px;
                  border-radius: 999px; }
    .disc-badge { display: inline-block; background: #d1fae5; color: #065f46;
                  font-size: 11px; font-weight: 700; padding: 3px 10px;
                  border-radius: 999px; margin-left: 6px; }

    .note-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
                padding: 14px 18px; font-size: 13px; color: #78350f; }

    .upload-hint { text-align:center; padding:60px 20px; color:#94a3b8; }
    .upload-hint .ico { font-size:48px; margin-bottom:12px; }
    .upload-hint .t1  { font-size:17px; font-weight:600; color:#64748b; margin-bottom:6px; }
    .upload-hint .t2  { font-size:13px; }
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
    st.markdown("**Supported languages**")
    st.markdown("English, Arabic, German, French, Urdu, Chinese, Spanish & more")
    st.divider()
    st.markdown("**Validation checks**")
    st.markdown("✔ SKU exists in catalog")
    st.markdown("✔ Price vs contracted rate")
    st.markdown("✔ Discount validation")
    st.markdown("✔ Stock availability")
    st.markdown("✔ Customer ID verified")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="page-title">🧾 Quote-to-Order AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Upload any Purchase Order — any language, any format — to extract, validate and flag issues instantly.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload Purchase Order", type=["txt", "pdf"], label_visibility="collapsed"
)

if uploaded_file is None:
    st.markdown("""
    <div class="upload-hint">
        <div class="ico">📂</div>
        <div class="t1">Drop a Purchase Order here</div>
        <div class="t2">PDF or TXT &nbsp;·&nbsp; Any language &nbsp;·&nbsp; Max 200 MB</div>
    </div>""", unsafe_allow_html=True)
    st.stop()


# ---------------------------------------------------------------------------
# Read file
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
discount_pct    = result.get("discount_applied", 0)

grand_total    = extracted.get("grand_total")
subtotal       = extracted.get("subtotal")
tax_amount     = extracted.get("tax_amount")
shipping_cost  = extracted.get("shipping_cost")
language       = extracted.get("language", "English")
currency       = extracted.get("currency", "USD")
valid_count    = sum(1 for i in validated_items if i.get("status") == "valid")
overall_status = "APPROVED" if not flags else "FLAGGED"
status_class   = "card-green" if not flags else "card-red"


# ---------------------------------------------------------------------------
# Language / currency badges
# ---------------------------------------------------------------------------
disc_badge = f'<span class="disc-badge">✓ {discount_pct:.0f}% discount applied</span>' if discount_pct > 0 else ""
st.markdown(f"""
<span class="lang-badge">🌐 {language}</span>
<span class="curr-badge">💱 {currency}</span>
{disc_badge}
""", unsafe_allow_html=True)

st.markdown("")


# ---------------------------------------------------------------------------
# Summary cards  (2 × 2)
# ---------------------------------------------------------------------------
st.markdown('<div class="sec">Summary</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)

with c1:
    st.markdown(f"""
    <div class="card">
        <div class="lbl">PO Number</div>
        <div class="val">{extracted.get("po_number") or "N/A"}</div>
        <div class="sub">Date: {extracted.get("po_date") or "N/A"}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="card">
        <div class="lbl">Customer</div>
        <div class="val">{extracted.get("customer_name") or "N/A"}</div>
        <div class="sub">ID: {extracted.get("customer_id") or "N/A"}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    total_display = f"{currency} {grand_total:,.2f}" if grand_total else "N/A"
    st.markdown(f"""
    <div class="card">
        <div class="lbl">Grand Total</div>
        <div class="val">{total_display}</div>
        <div class="sub">{len(line_items)} line item(s)</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="card {status_class}">
        <div class="lbl">Status</div>
        <div class="val">{overall_status}</div>
        <div class="sub">{len(flags)} issue(s) &nbsp;·&nbsp; {valid_count} item(s) valid</div>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PO Details  +  Financial Summary
# ---------------------------------------------------------------------------
st.markdown('<div class="sec">Order Details</div>', unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    def meta(k, v):
        if v:
            return f'<div class="meta-row"><span class="mk">{k}</span><span class="mv">{v}</span></div>'
        return ""

    rows = "".join(filter(None, [
        meta("Vendor",           extracted.get("vendor_name")),
        meta("Delivery Date",    extracted.get("requested_delivery_date")),
        meta("Payment Terms",    extracted.get("payment_terms")),
        meta("Shipping Terms",   extracted.get("shipping_terms")),
        meta("Ship To",          extracted.get("ship_to_address")),
        meta("Customer Email",   extracted.get("customer_email")),
        meta("Customer Phone",   extracted.get("customer_phone")),
    ]))
    st.markdown(f'<div class="meta-box">{rows or "<span style=color:#94a3b8>No additional details found</span>"}</div>', unsafe_allow_html=True)

with right:
    def fin_row(label, amount, bold=False):
        if amount is None:
            return ""
        cls = "fin-row fin-total" if bold else "fin-row"
        return f'<div class="{cls}"><span>{label}</span><span class="fin-val">{currency} {amount:,.2f}</span></div>'

    fin_rows = "".join(filter(None, [
        fin_row("Subtotal",         subtotal),
        fin_row("Tax",              tax_amount),
        fin_row("Shipping",         shipping_cost),
        fin_row("Grand Total",      grand_total, bold=True),
    ]))

    if fin_rows:
        st.markdown(f'<div class="fin-box">{fin_rows}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="fin-box"><span style="color:#64748b;font-size:13px">No financial totals found in PO</span></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Line Items
# ---------------------------------------------------------------------------
st.markdown('<div class="sec">Line Items</div>', unsafe_allow_html=True)

if validated_items:
    for item in validated_items:
        status  = item.get("status", "invalid")
        issues  = item.get("issues", [])
        desc    = item.get("description") or ""
        uom     = item.get("uom") or "pcs"
        lt      = item.get("line_total")

        badge = '<span class="badge-v">✓ Valid</span>' if status == "valid" else '<span class="badge-i">✗ Invalid</span>'
        lt_html = f'<span class="li-meta">Total: {currency} {lt:,.2f}</span>' if lt else ""
        issues_html = ""
        if issues:
            issues_html = '<div class="li-issues">' + "".join(f"• {i}<br>" for i in issues) + "</div>"

        st.markdown(f"""
        <div class="li-card {status}">
            <div class="li-top">
                <span class="li-sku">{item.get("sku") or "N/A"}</span>
                <span class="li-desc">{desc}</span>
                <span class="li-meta">Qty: {item.get("quantity")} {uom}</span>
                <span class="li-meta">{currency} {item.get("unit_price", 0):.2f}/unit</span>
                {lt_html}
                {badge}
            </div>
            {issues_html}
        </div>""", unsafe_allow_html=True)
else:
    st.info("No line items found.")


# ---------------------------------------------------------------------------
# Special Instructions
# ---------------------------------------------------------------------------
special = extracted.get("special_instructions")
if special:
    st.markdown('<div class="sec">Special Instructions</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="note-box">📋 {special}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Additional Fields
# ---------------------------------------------------------------------------
extra = extracted.get("additional_fields") or {}
if extra:
    st.markdown('<div class="sec">Additional Information</div>', unsafe_allow_html=True)
    rows = "".join(
        f'<div class="meta-row"><span class="mk">{k}</span><span class="mv">{v}</span></div>'
        for k, v in extra.items() if v
    )
    st.markdown(f'<div class="meta-box">{rows}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Validation Results
# ---------------------------------------------------------------------------
st.markdown('<div class="sec">Validation Results</div>', unsafe_allow_html=True)

if not flags:
    st.markdown('<div class="ok-box">✅ All checks passed. This PO is ready to process.</div>', unsafe_allow_html=True)
else:
    for flag in flags:
        st.markdown(f'<div class="flag-box">🔴 {flag}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
st.markdown('<div class="sec">Export Report</div>', unsafe_allow_html=True)

if validated_items:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["sku", "description", "quantity", "uom", "unit_price", "line_total", "status", "issues"])
    writer.writeheader()
    for item in validated_items:
        writer.writerow({
            "sku":         item.get("sku"),
            "description": item.get("description"),
            "quantity":    item.get("quantity"),
            "uom":         item.get("uom"),
            "unit_price":  item.get("unit_price"),
            "line_total":  item.get("line_total"),
            "status":      item.get("status"),
            "issues":      " | ".join(item.get("issues", [])),
        })

    po_num = (extracted.get("po_number") or "report").replace("/", "-")
    st.download_button(
        label="⬇️  Download Validation Report (CSV)",
        data=output.getvalue(),
        file_name=f"{po_num}_validation.csv",
        mime="text/csv",
    )
