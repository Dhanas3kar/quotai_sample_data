# 🏭 QuotAI — Variant-Based Cost Estimation Prototype

A modular Python prototype demonstrating automated **manufacturing cost estimation** for product variants. Built as a clean engineering prototype to showcase a data-driven estimation pipeline with an interactive UI.

---

## 📋 Problem Statement

Manufacturing companies receive requests for quotations (RFQs) based on engineering drawings. Engineers must manually determine:

- **Material** required for the part (weight, grade, cost)
- **Machining operations** needed (turning, drilling, grinding, etc.)
- **Machine time** and hourly rates per operation
- **Business adjustments** — overheads, packaging, freight, discounts

This process is **slow**, **inconsistent** between estimators, and **prone to calculation errors**.

**QuotAI** demonstrates how a structured, data-driven pipeline can **automate** these calculations and produce **repeatable, auditable** cost estimates.

---

## 🏗️ Architecture

```
quotai/
│
├── engine/
│   ├── estimator.py              # CostEstimator — main pipeline class
│   ├── material_cost.py          # Weight & material cost calculation
│   ├── operation_cost.py         # Machining time & operation cost
│   └── pricing_engine.py         # Pricing template adjustments
│
├── data/
│   └── csv_loader.py             # CSV data loader & lookup helpers
│
├── utils/
│   └── math_utils.py             # Decimal math & geometry helpers
│
├── reports/
│   └── report_generator.py       # HTML report generation
│
├── tests/
│   └── test_estimator.py         # Unit & integration tests
│
└── README.md                     # This file
```

---

## 🔄 Cost Estimation Pipeline

```
          ┌─────────────────────┐
          │   Variant Drawing   │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   Supplied Features │
          │  (dimensions, holes)│
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
  ┌───────────────┐   ┌────────────────┐
  │ Material Cost │   │ Operation Cost │
  │ weight × rate │   │ time × rate    │
  └───────┬───────┘   └────────┬───────┘
          │                    │
          └────────┬───────────┘
                   ▼
          ┌─────────────────────┐
          │  Subtotal Per Unit  │
          │  (material + ops)   │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Pricing Template   │
          │  + overheads        │
          │  − discounts        │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │    Final Quote      │
          │  net/unit × qty     │
          └─────────────────────┘
```

### Calculation Logic

| Step | Formula |
|------|---------|
| **Blank Volume** | `π/4 × (OD² − ID²) × Length` |
| **Hole Volume** | `π/4 × D² × wall_thickness × count` |
| **Net Weight** | `(blank − holes) × density / 1e9 × (1 + scrap%)` |
| **Material Cost** | `weight_kg × rate_per_kg` |
| **Operation Cost** | `Σ (setup_hrs + cycle_hrs) × rate_per_hour` |
| **Subtotal** | `material_cost + operation_cost` |
| **Overheads** | Percentage of base or fixed per unit |
| **Discounts** | Percentage of base or fixed per unit |
| **Net / Unit** | `subtotal + overheads − discounts` |
| **Total** | `net_per_unit × quantity` |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Financial Math | `decimal.Decimal` (no float rounding errors) |
| Data Storage | CSV files (transparent, editable) |

| Visualization | Plotly (interactive pie charts) |
| Testing | pytest |
| Report | Self-contained HTML |

---

## 🚀 How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```


### 3. Run tests

```bash
cd /path/to/quotai_sample_data
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

print(f"Material Cost:    ₹{result['material_cost']:,.2f}")
print(f"Operation Cost:   ₹{result['operation_cost']:,.2f}")
print(f"Net Cost / Unit:  ₹{result['net_cost_per_unit']:,.2f}")
print(f"Total Cost:       ₹{result['total_cost']:,.2f}")
```

---

## 📊 Example Output

**Variant:** `bearing_ring` | **Quantity:** 100 | **Scrap:** 5%

```
──────────────────────────────────
  QuotAI Cost Estimation Summary
──────────────────────────────────
  Material:         Stainless Steel 316
  Weight / Unit:    2.50 kg
  Material Cost:    ₹ 850.00
  Operation Cost:   ₹ 1,550.00
  Subtotal:         ₹ 2,400.00
  Overheads:        ₹ 272.00
  Discounts:        ₹ 120.00
  ──────────────────────────────
  Net Cost / Unit:  ₹ 2,552.00
  Total (100 pcs):  ₹ 255,200.00
──────────────────────────────────
```

---

## 📐 Data Model

The CSV data model supports the full QuotAI architecture:

- **Organization** → multi-tenant company setup
- **Material** → global material catalog with density
- **MaterialRate** → tenant-specific ₹/kg with effective dates
- **Operation** → machining operations (drilling, turning, etc.)
- **WorkCenter** → machines / vendors with hourly rates
- **ProductFamily** → groups of similar parts with reference drawings
- **ProductVariant** → individual parts with uploaded drawings
- **PricingTemplate** → configurable overheads and discounts
- **CostEstimation** → frozen snapshot of a complete estimate

See `DATA_MODEL.md` for full entity-relationship details.

---

## 🎯 Design Principles

1. **Decimal arithmetic** — no floating-point errors in money
2. **Small, reusable functions** — each module has a single responsibility
3. **CSV transparency** — all data is human-readable and editable
4. **Error handling** — graceful failures with clear messages
5. **Testability** — every calculation function is independently testable
6. **Clean separation** — extraction → costing → pricing → reporting

---

## 🔮 Future Improvements

- Add multi-operation routing with sequencing
- Persist data in SQLite or PostgreSQL
- Add user authentication and role-based access
- Build REST API for async quotation requests
- Add PDF report export alongside HTML

---


