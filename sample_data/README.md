# QuotAI Sample Data

Test dataset for building and validating cost estimation computation logic.

## Scenario

**Organization:** Precision Manufacturing Co. — a machining shop in India quoting hydraulic cylinder spacers in SS 316.

**Users:**
| Name | Role | Group |
|------|------|-------|
| Rajesh Kumar | org_admin | — |
| Priya Sharma | estimator | Estimators |
| Amit Patel | viewer | Shop Floor A |

**Product Family:** Hydraulic Cylinder Spacers (1 family, 2 variants)

| Variant | Length | Holes | Weight | Extra |
|---------|--------|-------|--------|-------|
| v1 - Standard | 80mm | 6x dia 10 | 2.5 kg | — |
| v2 - Extended | 130mm | 8x dia 10 | 3.8 kg | Ground faces, surface grinding |

**Material Rates (SS 316):**
- Jan 2025: INR 320/kg
- Jul 2025: INR 340/kg ← **active rate used in estimations**

**Work Center Rates:**
| Work Center | Operation | Material | Rate/hr |
|-------------|-----------|----------|---------|
| CNC Lathe #1 | Turning | (default) | 850 |
| CNC Lathe #1 | Turning | SS 316 | **1100** ← material-specific override |
| CNC Mill #2 | Drilling | (default) | 750 |
| CNC Mill #2 | Spot Facing | (default) | 800 |
| CNC Mill #2 | Surface Grinding | (default) | 900 |
| Vendor: ABC | Heat Treatment | (default) | 600 |

**Pricing Template Used:** Standard Domestic
| Line Item | Category | Type | Value | Apply On |
|-----------|----------|------|-------|----------|
| Commercial Overhead | overhead | percentage | 8% | subtotal |
| Packaging | overhead | fixed_per_unit | INR 50 | — |
| Freight | overhead | fixed_per_unit | INR 30 | — |
| Volume Discount | discount | percentage | 5% | subtotal |

---

## Estimation #1 — Spacer v1 Standard (FINALIZED)

**Customer:** Tata Hydraulics | **Qty:** 100 | **Ref:** RFQ-2025-0042

### Material Cost
| Material | Weight | Rate | Cost/Unit |
|----------|--------|------|-----------|
| SS 316 | 2.50 kg | 340.00 | **850.00** |

### Operation Costs
| Operation | Work Center | Setup | Cycle | Rate | Cost/Unit |
|-----------|------------|-------|-------|------|-----------|
| Turning | CNC Lathe #1 | 0.25 | 0.50 | 1100.00 | **825.00** |
| Drilling | CNC Mill #2 | 0.10 | 0.20 | 750.00 | **225.00** |
| Spot Facing | CNC Mill #2 | 0.10 | 0.15 | 800.00 | **200.00** |
| Heat Treatment | Vendor: ABC | 0.00 | 0.50 | 600.00 | **300.00** |
| | | | | **Total Ops:** | **1,550.00** |

### Summary
```
Material Cost/Unit:     850.00
Operation Cost/Unit:  1,550.00
                     ─────────
Subtotal/Unit:        2,400.00

+ Commercial OH (8% of 2400):   192.00
+ Packaging (fixed):              50.00
+ Freight (fixed):                30.00
                     ─────────
Total Overhead/Unit:    272.00

- Volume Discount (5% of 2400): 120.00
                     ─────────
Total Discount/Unit:    120.00

Net Cost/Unit:        2,552.00
× Quantity:                 100
                     ═════════
TOTAL COST:         255,200.00 INR
```

---

## Estimation #2 — Spacer v2 Extended (DRAFT)

**Customer:** Bharat Heavy Electricals | **Qty:** 50 | **Ref:** RFQ-2025-0067

### Material Cost
| Material | Weight | Rate | Cost/Unit |
|----------|--------|------|-----------|
| SS 316 | 3.80 kg | 340.00 | **1,292.00** |

### Operation Costs
| Operation | Work Center | Setup | Cycle | Rate | Cost/Unit |
|-----------|------------|-------|-------|------|-----------|
| Turning | CNC Lathe #1 | 0.25 | 0.75 | 1100.00 | **1,100.00** |
| Drilling | CNC Mill #2 | 0.10 | 0.30 | 750.00 | **300.00** |
| Spot Facing | CNC Mill #2 | 0.10 | 0.20 | 800.00 | **240.00** |
| Surface Grinding | CNC Mill #2 | 0.15 | 0.25 | 900.00 | **360.00** |
| Heat Treatment | Vendor: ABC | 0.00 | 0.60 | 600.00 | **360.00** |
| | | | | **Total Ops:** | **2,360.00** |

### Summary
```
Material Cost/Unit:   1,292.00
Operation Cost/Unit:  2,360.00
                     ─────────
Subtotal/Unit:        3,652.00

+ Commercial OH (8% of 3652):   292.16
+ Packaging (fixed):              50.00
+ Freight (fixed):                30.00
                     ─────────
Total Overhead/Unit:    372.16

- Volume Discount (5% of 3652): 182.60
                     ─────────
Total Discount/Unit:    182.60

Net Cost/Unit:        3,841.56
× Quantity:                  50
                     ═════════
TOTAL COST:         192,078.00 INR
```

---

## Task Brief for Developer

You are building a Python module that computes a cost estimation given the sample CSV data. The module should be testable standalone (read from CSVs, no database required).

### What to build

Implement these functions. All monetary values are `Decimal` rounded to 2 decimal places.

```python
def lookup_material_rate(org_id, material_id, as_of_date) -> Decimal:
    """
    From material_rate.csv, return rate_per_kg for the row with the
    latest effective_from <= as_of_date for the given org + material.
    Raise an error if no rate is found.
    """

def lookup_work_center_rate(work_center_id, operation_id, material_id) -> Decimal:
    """
    From work_center_rate.csv:
      1. Exact match (work_center, operation, material) → use that rate
      2. Fallback (work_center, operation, material=NULL) → default rate
      3. No match → raise an error
    """

def compute_material_costs(materials: list[dict]) -> Decimal:
    """
    Input: list of {weight_per_unit_kg, rate_per_kg}
    Returns: SUM(weight × rate) per unit
    Typically one material per estimation, but support multiple.
    """

def compute_operation_costs(operations: list[dict]) -> Decimal:
    """
    Input: list of {setup_time_hrs, cycle_time_hrs, rate_per_hour}
    Returns: SUM((setup + cycle) × rate) per unit
    """

def compute_adjustments(adjustments: list[dict], subtotal, material_cost, operation_cost) -> tuple[Decimal, Decimal]:
    """
    Input: list of {category, type, value, apply_on} sorted by sort_order
    Returns: (total_overhead_per_unit, total_discount_per_unit)

    Rules:
    - Each adjustment is computed INDEPENDENTLY against its base (not cascading)
    - For type=percentage:  computed_amount = value/100 × base
    - For type=fixed_per_unit:  computed_amount = value  (apply_on is ignored)
    - base is determined by apply_on: "subtotal" → subtotal, "material_cost" → material_cost,
      "operation_cost" → operation_cost
    - Sum all overhead computed_amounts → total_overhead
    - Sum all discount computed_amounts → total_discount
    """

def compute_summary(material_cost, operation_cost, overhead, discount, quantity) -> dict:
    """
    Returns: {
        subtotal_per_unit:  material_cost + operation_cost,
        overhead_per_unit:  overhead,
        discount_per_unit:  discount,
        net_cost_per_unit:  subtotal + overhead - discount,
        total_cost:         net_cost_per_unit × quantity,
    }
    """
```

### Rules

- **Rounding:** All monetary amounts rounded to 2 decimal places (`ROUND_HALF_UP`).
- **Adjustments are independent:** sort_order controls display order only. Each adjustment computes against the original base, NOT a running total. For example, if two overheads both `apply_on: subtotal`, they each use the same subtotal — not subtotal + first overhead.
- **`apply_on` is ignored for `fixed_per_unit`:** The value is the per-unit amount directly.
- **Rate not found = error:** If a material rate or work center rate lookup fails, raise an exception. Do not silently default to zero.

### How to validate

Load the CSVs with pandas or csv module. Run your functions against both estimations and assert the outputs match `estimation_summary.csv`:

| | Estimation #1 | Estimation #2 |
|---|---|---|
| Material Cost/Unit | 850.00 | 1,292.00 |
| Operation Cost/Unit | 1,550.00 | 2,360.00 |
| Subtotal/Unit | 2,400.00 | 3,652.00 |
| Overhead/Unit | 272.00 | 372.16 |
| Discount/Unit | 120.00 | 182.60 |
| Net Cost/Unit | 2,552.00 | 3,841.56 |
| Total Cost | 255,200.00 | 192,078.00 |

---

## Key Test Cases for Computation Logic

1. **Material rate lookup** — SS 316 has two rates (320 in Jan, 340 in Jul). Both estimations are Aug/Sep 2025, so the Jul rate (340) should be selected via `effective_from <= today` ordering.

2. **Work center rate priority** — Turning on CNC Lathe #1 has a default rate (850) AND a SS 316-specific rate (1100). The estimations use SS 316, so rate 1100 should be selected via exact material match.

3. **Operation cost formula** — `cost_per_unit = (setup_time_hrs + cycle_time_hrs) × rate_per_hour`

4. **Percentage adjustments** — `computed_amount = value% × subtotal` (when apply_on = subtotal)

5. **Fixed adjustments** — `computed_amount = value` (flat amount per unit)

6. **Summary aggregation:**
   - `subtotal = material_cost + operation_cost`
   - `overhead = sum of overhead computed_amounts`
   - `discount = sum of discount computed_amounts`
   - `net_cost_per_unit = subtotal + overhead - discount`
   - `total_cost = net_cost_per_unit × quantity`

7. **Snapshot behavior** — All names, grades, and rates in estimation tables are frozen snapshots, not live lookups.

## CSV Files (18 total)

| # | File | Records |
|---|------|---------|
| 1 | `organization.csv` | 1 |
| 2 | `user_group.csv` | 2 |
| 3 | `user.csv` | 3 |
| 4 | `material.csv` | 3 |
| 5 | `operation.csv` | 5 |
| 6 | `product_family.csv` | 1 |
| 7 | `product_variant.csv` | 2 |
| 8 | `variant_extraction.csv` | 2 |
| 9 | `material_rate.csv` | 4 |
| 10 | `work_center.csv` | 3 |
| 11 | `work_center_rate.csv` | 6 |
| 12 | `pricing_template.csv` | 2 |
| 13 | `template_line_item.csv` | 8 |
| 14 | `cost_estimation.csv` | 2 |
| 15 | `estimation_material_cost.csv` | 2 |
| 16 | `estimation_operation_cost.csv` | 9 |
| 17 | `estimation_adjustment.csv` | 8 |
| 18 | `estimation_summary.csv` | 2 |
| 19 | `estimation_report.csv` | 1 |

## UUID Prefix Convention

For readability, UUIDs follow a prefix pattern:
- `1xxxxxxx` = Organization
- `2xxxxxxx` = UserGroup
- `3xxxxxxx` = User
- `4xxxxxxx` = Material
- `5xxxxxxx` = Operation
- `6xxxxxxx` = ProductFamily
- `7xxxxxxx` = ProductVariant
- `8xxxxxxx` = VariantExtraction
- `9xxxxxxx` = MaterialRate
- `axxxxxxx` = WorkCenter
- `bxxxxxxx` = WorkCenterRate
- `cxxxxxxx` = PricingTemplate
- `dxxxxxxx` = TemplateLineItem
- `e0xxxxxx` = CostEstimation
- `e1xxxxxx` = EstimationMaterialCost
- `e2xxxxxx` = EstimationOperationCost
- `e3xxxxxx` = EstimationAdjustment
- `e4xxxxxx` = EstimationSummary
- `e5xxxxxx` = EstimationReport
