"""
QuotAI Cost Estimator — Streamlit Application

A professional interactive UI for variant-based manufacturing
cost estimation. Includes parameter inputs, cost metrics,
pie-chart visualization, and downloadable HTML reports.
"""

import os
import sys
from decimal import Decimal

import streamlit as st
import plotly.graph_objects as go

# ── Ensure the project root is on sys.path ─────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quotai.engine.estimator import CostEstimator, EstimationError
from quotai.reports.report_generator import generate_html_report

# ── Resolve sample_data path ───────────────────────────────────────────
SAMPLE_DATA_DIR = os.path.join(PROJECT_ROOT, "sample_data")


# ────────────────────────────────────────────────────────────────────────
# Page Config
# ────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuotAI Cost Estimator",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Header styling — inherits text color from theme */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .main-header span { color: #4A7BF7; }
    .sub-header {
        font-size: 1rem;
        opacity: 0.6;
        margin-top: -10px;
        margin-bottom: 24px;
    }
    /* Metric cards — use semi-transparent fills so they work on any theme */
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.06);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 10px;
        padding: 14px 18px;
    }
    /* Sidebar — subtle tint that works in both light & dark */
    [data-testid="stSidebar"] {
        background: rgba(128, 128, 128, 0.04);
    }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────────
# Initialize estimator
# ────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_estimator():
    """Load the estimator once and cache it."""
    return CostEstimator(SAMPLE_DATA_DIR)


try:
    estimator = get_estimator()
except FileNotFoundError as exc:
    st.error(f"❌ {exc}")
    st.stop()


# ────────────────────────────────────────────────────────────────────────
# Header
# ────────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🏭 Quot<span>AI</span> Cost Estimator</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Variant-based manufacturing cost estimation prototype</p>', unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────────
# Sidebar — Inputs
# ────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Estimation Parameters")

    # ── Step 1: Product Family selector ──
    family_names = estimator.loader.get_family_names()
    family_options = ["— Auto-detect —"] + family_names
    family_selection = st.selectbox("Product Family", family_options, index=0)
    selected_family = None if family_selection == "— Auto-detect —" else family_selection

    # ── Step 2: Variant selector (filtered by family when selected) ──
    if selected_family:
        family_row = estimator.loader.get_family_by_name(selected_family)
        if family_row:
            family_variants = estimator.loader.get_variants_for_family(family_row["id"])
            variant_names = [v["name"] for v in family_variants]
        else:
            variant_names = estimator.loader.get_variant_names()
    else:
        variant_names = estimator.loader.get_variant_names()

    all_variants = variant_names + ["bearing_ring", "flange_adapter"]
    variant = st.selectbox("Product Variant", all_variants, index=0)

    # ── Step 2b: Upload variant drawing ──
    st.divider()
    st.subheader("📤 Variant Drawing")
    uploaded_drawing = st.file_uploader(
        "Upload variant drawing (image)",
        type=["png", "jpg", "jpeg", "bmp", "tiff", "webp"],
        help="Upload the variant's engineering drawing. "
             "AI will extract features using the family's reference drawing as context.",
    )
    variant_drawing_bytes = None
    if uploaded_drawing is not None:
        variant_drawing_bytes = uploaded_drawing.getvalue()
        st.image(uploaded_drawing, caption="Uploaded Variant Drawing", use_container_width=True)
        st.caption(f"📎 {uploaded_drawing.name} — {len(variant_drawing_bytes)/1024:.1f} KB")
    else:
        st.caption("No drawing uploaded — using stored extraction or mock AI.")

    # Show reference drawing info if family is selected
    if selected_family:
        _fam = estimator.loader.get_family_by_name(selected_family)
        if _fam and _fam.get("ref_drawing_path"):
            st.info(f"📐 Reference drawing: `{_fam['ref_drawing_path']}`")

    # Template selector
    template_names = estimator.loader.get_template_names()
    template = st.selectbox("Pricing Template", template_names, index=0)

    # Quantity and scrap
    col1, col2 = st.columns(2)
    with col1:
        quantity = st.number_input("Quantity", min_value=1, value=100, step=10)
    with col2:
        scrap_pct = st.number_input("Scrap %", min_value=0.0, max_value=50.0,
                                     value=5.0, step=0.5)

    effective_date = st.date_input("Effective Date", value=None)
    if effective_date is None:
        effective_date_str = "2026-03-09"
    else:
        effective_date_str = effective_date.isoformat()

    st.divider()

    # ── Manual Engineering Overrides ──
    st.subheader("🔧 Manual Overrides")
    st.caption("Leave at 0 to use AI-extracted values")

    ov_od = st.number_input("Outer Diameter (mm)", min_value=0.0, value=0.0, step=1.0)
    ov_id = st.number_input("Inner Diameter (mm)", min_value=0.0, value=0.0, step=1.0)
    ov_len = st.number_input("Length (mm)", min_value=0.0, value=0.0, step=1.0)
    ov_hc = st.number_input("Hole Count", min_value=0, value=0, step=1)
    ov_hd = st.number_input("Hole Diameter (mm)", min_value=0.0, value=0.0, step=0.5)

    st.divider()
    run_btn = st.button("🚀 Run Estimation", use_container_width=True, type="primary")


# ────────────────────────────────────────────────────────────────────────
# Main Area — Run estimation on button click
# ────────────────────────────────────────────────────────────────────────
if run_btn:
    try:
        result = estimator.estimate(
            variant=variant,
            quantity=quantity,
            scrap_percent=scrap_pct,
            effective_date=effective_date_str,
            template_name=template,
            family_name=selected_family,
            variant_drawing_bytes=variant_drawing_bytes,
            outer_diameter=ov_od if ov_od > 0 else None,
            inner_diameter=ov_id if ov_id > 0 else None,
            length=ov_len if ov_len > 0 else None,
            hole_count=int(ov_hc) if ov_hc > 0 else None,
            hole_diameter=ov_hd if ov_hd > 0 else None,
        )

        # Store result in session state for persistence
        st.session_state["result"] = result
        st.session_state["run"] = True

    except EstimationError as exc:
        st.error(f"⚠️ Estimation Error: {exc}")
    except Exception as exc:
        st.error(f"❌ Unexpected error: {exc}")


# ────────────────────────────────────────────────────────────────────────
# Display results (if available)
# ────────────────────────────────────────────────────────────────────────
if st.session_state.get("run"):
    result = st.session_state["result"]

    # ── Frozen Snapshot Header ─────────────────────────────────────────
    snap_col1, snap_col2, snap_col3, snap_col4 = st.columns(4)
    snap_col1.metric("Estimation ID", result.get("estimation_id", "—")[:8] + "…")
    snap_col2.metric("Status", result.get("status", "draft").upper())
    snap_col3.metric("Product Family", result.get("family_name", "N/A"))
    snap_col4.metric("Currency", result.get("currency", "INR"))

    st.divider()

    # ── Key Metrics ────────────────────────────────────────────────────
    st.subheader("📊 Cost Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Material Cost / Unit", f"₹ {result['material_cost']:,.2f}")
    m2.metric("Operation Cost / Unit", f"₹ {result['operation_cost']:,.2f}")
    m3.metric("Net Cost / Unit", f"₹ {result['net_cost_per_unit']:,.2f}")
    m4.metric("Total Cost", f"₹ {result['total_cost']:,.2f}")

    st.divider()

    # ── Charts & Features side by side ─────────────────────────────────
    chart_col, detail_col = st.columns([1, 1])

    with chart_col:
        st.subheader("🥧 Cost Breakdown")

        mat = float(result["material_cost"])
        ops = float(result["operation_cost"])
        ovh = float(result["overheads"])

        fig = go.Figure(data=[go.Pie(
            labels=["Material", "Operations", "Overheads"],
            values=[mat, ops, ovh],
            hole=0.45,
            marker=dict(colors=["#4A7BF7", "#27AE60", "#E67E22"]),
            textinfo="label+percent",
            textfont=dict(size=14),
            hovertemplate="<b>%{label}</b><br>₹ %{value:,.2f}<br>%{percent}<extra></extra>",
        )])
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=20, b=40, l=20, r=20),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    with detail_col:
        st.subheader("📐 Extracted Features")

        # Show extraction source
        features = result["features"]
        source = features.get("_extraction_source", "")
        if source == "mock_ai_from_upload":
            st.success("🤖 AI extracted from uploaded drawing (mock)")
        elif source == "ref_baseline_from_upload":
            st.info("📐 Used reference baseline (uploaded drawing unrecognised)")
        elif source == "defaults_from_upload":
            st.warning("⚠️ Drawing uploaded but no reference — using defaults")
        elif result.get("ref_extraction"):
            st.caption("📋 Features from stored extraction / mock AI")

        fc1, fc2 = st.columns(2)
        fc1.metric("Outer Diameter", f'{features["outer_diameter_mm"]} mm')
        fc2.metric("Inner Diameter", f'{features["inner_diameter_mm"]} mm')

        fc3, fc4 = st.columns(2)
        fc3.metric("Length", f'{features["length_mm"]} mm')
        holes = features.get("holes", [])
        hole_info = ", ".join(f'{h["count"]}× ⌀{h["diameter_mm"]}mm' for h in holes) or "None"
        fc4.metric("Holes", hole_info)

        fc5, fc6 = st.columns(2)
        fc5.metric("Material", result["material_name"])
        fc6.metric("Weight (incl. scrap)", f'{result["weight_kg"]} kg')

    st.divider()

    # ── Operation Details Table ────────────────────────────────────────
    st.subheader("🔧 Operation Cost Details")
    op_data = []
    rate_warnings = []
    for op in result["operation_details"]:
        if op.get("rate_missing"):
            rate_warnings.append(op["operation_name"])
        op_data.append({
            "Operation": op["operation_name"],
            "Work Center": op["work_center_name"],
            "Setup (hr)": float(op["setup_time_hrs"]),
            "Cycle (hr)": float(op["cycle_time_hrs"]),
            "Rate (₹/hr)": float(op["rate_per_hour"]),
            "Cost / Unit (₹)": float(op["cost_per_unit"]),
        })
    if rate_warnings:
        st.warning(
            f"⚠️ Rate not configured for: **{', '.join(rate_warnings)}**. "
            "These operations have ₹0 cost. Configure rates in work_center_rate.csv."
        )
    if op_data:
        st.dataframe(op_data, use_container_width=True, hide_index=True)
    else:
        st.info("No operations with configured rates found.")

    # ── Pricing Adjustments Table ──────────────────────────────────────
    st.subheader(f"📄 Pricing Adjustments — {result['template_name']}")
    adj_data = []
    for adj in result["adjustments"]:
        sign = "+" if adj["category"] == "overhead" else "−"
        basis = (f'{adj["value"]}% of {adj["apply_on"]}'
                 if adj["type"] == "percentage" else "fixed/unit")
        adj_data.append({
            "Item": adj["name"],
            "Category": adj["category"].title(),
            "Basis": basis,
            "Amount / Unit (₹)": f'{sign} {float(adj["computed_amount"]):,.2f}',
        })
    if adj_data:
        st.dataframe(adj_data, use_container_width=True, hide_index=True)

    # ── Final Summary ──────────────────────────────────────────────────
    st.divider()
    st.subheader("💰 Final Summary")
    s1, s2, s3 = st.columns(3)
    s1.metric("Subtotal / Unit", f"₹ {result['subtotal']:,.2f}")
    s2.metric("Overheads / Unit", f"+ ₹ {result['overheads']:,.2f}")
    s3.metric("Discounts / Unit", f"− ₹ {result['discounts']:,.2f}")

    st.markdown("---")
    t1, t2 = st.columns(2)
    t1.metric("Net Cost / Unit", f"₹ {result['net_cost_per_unit']:,.2f}")
    t2.metric(f"Total Cost ({result['quantity']} units)", f"₹ {result['total_cost']:,.2f}")

    # ── Download Report ────────────────────────────────────────────────
    st.divider()
    report_html = generate_html_report(result)
    est_id_short = result.get("estimation_id", "draft")[:8]
    st.download_button(
        label="📥 Download HTML Report",
        data=report_html,
        file_name=f"quotai_report_{result['variant']}_{est_id_short}.html",
        mime="text/html",
        use_container_width=True,
    )

else:
    # ── Welcome state ──────────────────────────────────────────────────
    st.info("👈 Configure parameters in the sidebar and click **Run Estimation** to start.")

    st.markdown("""
    ### How it works

    ```
    ① Select Product Family
          │
          ▼
    ② Upload Variant Drawing
          │
          ▼
    AI Feature Extraction
    (ref drawing as context)
          │
    ┌─────┴──────┐
    ▼            ▼
    ③ Material   Operation
       Rates      Rates
    │            │
    └─────┬──────┘
          ▼
    ④ Pricing Template
    (overheads & discounts)
          │
          ▼
    ⑤ Frozen Cost Estimation
       + Generated Report
    ```

    **Select a product family**, upload a variant drawing,
    adjust parameters, and click **Run Estimation**.
    """)
