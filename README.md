# 🏭 QuotAI — Variant-Based Cost Estimation Prototype

> A modular Python prototype demonstrating automated manufacturing cost estimation for product variants, built as a clean engineering prototype.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red.svg)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/tests-24%20passed-green.svg)](#)

---

## 📋 Problem Statement

Manufacturing companies receive requests for quotations (RFQs) based on engineering drawings. Engineers must manually determine material requirements, machining operations, time estimates, and business adjustments (overheads, freight, discounts). This process is **slow**, **inconsistent**, and **error-prone**.

**QuotAI** demonstrates how a structured, data-driven pipeline can **automate** these calculations and produce **repeatable, auditable** cost estimates.

---

## 🏗️ Project Architecture

```
quotai/
├── app/
│   └── streamlit_app.py          # Interactive Streamlit UI
├── engine/
│   ├── estimator.py              # CostEstimator — main pipeline class
│   ├── material_cost.py          # Weight & material cost calculation
│   ├── operation_cost.py         # Machining time & operation cost
│   └── pricing_engine.py         # Pricing template adjustments
├── extraction/
│   └── feature_extractor.py      # Mock AI feature extraction
├── data/
│   └── csv_loader.py             # CSV data loader & lookup helpers
├── utils/
│   └── math_utils.py             # Decimal math & geometry helpers
├── reports/
│   └── report_generator.py       # HTML report generation
└── tests/
    └── test_estimator.py         # 24 unit & integration tests

sample_data/                       # CSV reference data (19 files)
```

---

## 🔄 Cost Estimation Pipeline

```
          Variant Drawing
                │
                ▼
       Feature Extraction         ← Mock AI (simulates Gemini Vision)
      (dimensions, holes, material)
                │
       ┌────────┴─────────┐
       ▼                  ▼
  Material Cost      Operation Cost
  weight × rate      time × rate
       │                  │
       └────────┬─────────┘
                ▼
         Subtotal / Unit
                │
         Pricing Template
         + overheads
         − discounts
                │
                ▼
          Final Quote
       net/unit × quantity
```

### Calculation Summary

| Step | Formula |
|------|---------|
| Blank Volume | `π/4 × (OD² − ID²) × Length` |
| Net Weight | `(blank − holes) × density × (1 + scrap%)` |
| Material Cost | `weight_kg × rate_per_kg` |
| Operation Cost | `Σ (setup + cycle) × rate_per_hour` |
| Subtotal | `material + operations` |
| Net / Unit | `subtotal + overheads − discounts` |
| **Total** | `net_per_unit × quantity` |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Financial Math | `decimal.Decimal` |
| Data Store | CSV files |
| UI | Streamlit |
| Charts | Plotly |
| Testing | pytest (24 tests) |
| Reports | HTML |

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit app

```bash
streamlit run quotai/app/streamlit_app.py
```

### 3. Run tests

```bash
pytest quotai/tests/test_estimator.py -v
```

### 4. Use as a Python module

```python
from quotai.engine.estimator import CostEstimator

estimator = CostEstimator("sample_data")
result = estimator.estimate(
    variant="bearing_ring",
    quantity=100,
    scrap_percent=5,
    effective_date="2026-03-09",
)

print(f"Net Cost / Unit: ₹{result['net_cost_per_unit']:,.2f}")
print(f"Total Cost:      ₹{result['total_cost']:,.2f}")
```

---

## 📊 Example Output

**Variant:** `bearing_ring` | **Qty:** 100 | **Scrap:** 5% | **Template:** Standard Domestic

| Metric | Value |
|--------|-------|
| Material | Stainless Steel 316 |
| Weight / Unit | ~2.5 kg |
| Material Cost | ₹ 850.00 |
| Operation Cost | ₹ 1,550.00 |
| Subtotal | ₹ 2,400.00 |
| Overheads | + ₹ 272.00 |
| Discounts | − ₹ 120.00 |
| **Net / Unit** | **₹ 2,552.00** |
| **Total (100 pcs)** | **₹ 255,200.00** |

---

## 📐 Data Model

19 CSV files model the full QuotAI architecture:

- **Organization / Users** — multi-tenant setup
- **Material & MaterialRate** — catalog with density, ₹/kg rates with effective dates
- **Operation & WorkCenter** — machining ops with hourly rates
- **ProductFamily & Variant** — part groupings with reference/variant drawings
- **VariantExtraction** — AI-extracted geometric features
- **PricingTemplate** — configurable overheads & discounts
- **CostEstimation** — frozen estimation snapshots with reports

See [`DATA_MODEL.md`](DATA_MODEL.md) for the complete entity-relationship diagram and [`data_model_flowchart.html`](data_model_flowchart.html) for an interactive visual.

---

## 🎯 Design Principles

- ✅ **Decimal arithmetic** — zero floating-point errors in money
- ✅ **Small, testable functions** — each module has a single responsibility
- ✅ **CSV transparency** — all data is human-readable and editable
- ✅ **Graceful error handling** — clear messages for missing data
- ✅ **Clean separation** — extraction → costing → pricing → reporting
- ✅ **Docstrings everywhere** — every function is documented

---

*A clean engineering prototype demonstrating variant-based manufacturing cost estimation with Python.*