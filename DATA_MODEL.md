# QuotAI Data Model v1

## Overview

This data model supports the QuotAI variant-based cost estimation flow:

1. Select a **product family** (with a reference drawing)
2. Upload a **variant drawing** — AI extracts features using the reference as context
3. Look up **material rates** and **work center operation rates** from DB
4. Apply a **pricing template** (configurable overheads & discounts)
5. Produce a **frozen cost estimation** with a generated report

---

## Entity Relationship Diagram (text)

```
Organization ─┬── UserGroup
              ├── User
              ├── ProductFamily ──── ProductVariant ──── VariantExtraction
              ├── MaterialRate ────→ Material (global)
              ├── WorkCenter ────── WorkCenterRate ───→ Operation (global)
              │                                    ───→ Material  (global)
              ├── PricingTemplate ── TemplateLineItem
              └── CostEstimation ─┬─ EstimationMaterialCost
                                  ├─ EstimationOperationCost
                                  ├─ EstimationAdjustment
                                  ├─ EstimationSummary
                                  └─ EstimationReport
```

---

## 1. Multi-Tenancy & Users

### Organization
| Column     | Type      | Constraints       | Notes                    |
|------------|-----------|-------------------|--------------------------|
| id         | UUID      | PK                |                          |
| name       | string    | NOT NULL          | Company name             |
| slug       | string    | UNIQUE, NOT NULL  | URL-friendly identifier  |
| created_at | timestamp | NOT NULL          |                          |
| updated_at | timestamp | NOT NULL          |                          |

### UserGroup
| Column      | Type   | Constraints          | Notes                              |
|-------------|--------|----------------------|------------------------------------|
| id          | UUID   | PK                   |                                    |
| org_id      | UUID   | FK → Organization    |                                    |
| name        | string | NOT NULL             | e.g. "Shop Floor A", "Estimators" |
| description | string | nullable             |                                    |
| created_at  | timestamp | NOT NULL          |                                    |

### User
| Column     | Type   | Constraints           | Notes                                |
|------------|--------|-----------------------|--------------------------------------|
| id         | UUID   | PK                    |                                      |
| org_id     | UUID   | FK → Organization     |                                      |
| group_id   | UUID   | FK → UserGroup, nullable | Informational grouping            |
| email      | string | UNIQUE, NOT NULL      |                                      |
| name       | string | NOT NULL              |                                      |
| role       | enum   | NOT NULL              | org_admin, estimator, viewer         |
| created_at | timestamp | NOT NULL           |                                      |

---

## 2. Product Families & Variants

### ProductFamily
| Column                       | Type      | Constraints        | Notes                                        |
|------------------------------|-----------|--------------------|----------------------------------------------|
| id                           | UUID      | PK                 |                                              |
| org_id                       | UUID      | FK → Organization  |                                              |
| name                         | string    | NOT NULL           | e.g. "Hydraulic Cylinder Spacers"            |
| description                  | string    | nullable           |                                              |
| ref_drawing_path             | string    | NOT NULL           | File path to stored reference drawing        |
| ref_drawing_thumbnail_path   | string    | nullable           | For UI display                               |
| created_by                   | UUID      | FK → User          |                                              |
| created_at                   | timestamp | NOT NULL           |                                              |
| updated_at                   | timestamp | NOT NULL           |                                              |

One reference drawing per family. Family is tenant-scoped.

### ProductVariant
| Column       | Type      | Constraints           | Notes                            |
|--------------|-----------|-----------------------|----------------------------------|
| id           | UUID      | PK                    |                                  |
| family_id    | UUID      | FK → ProductFamily    |                                  |
| name         | string    | NOT NULL              | e.g. "Spacer v2 - Extended"     |
| description  | string    | nullable              |                                  |
| drawing_path | string    | NOT NULL              | Uploaded variant drawing         |
| created_by   | UUID      | FK → User             |                                  |
| created_at   | timestamp | NOT NULL              |                                  |



## 3. Global Catalogs (Platform Admin)

### Material
| Column     | Type    | Constraints  | Notes                                    |
|------------|---------|--------------|------------------------------------------|
| id         | UUID    | PK           |                                          |
| name       | string  | NOT NULL     | e.g. "Stainless Steel"                  |
| grade      | string  | NOT NULL     | e.g. "316", "7075-T6"                   |
| category   | string  | NOT NULL     | e.g. "ferrous", "non-ferrous", "polymer"|
| density    | decimal | nullable     | kg/m³, for automated weight estimation   |
| is_active  | boolean | NOT NULL     | Soft delete                              |
| created_at | timestamp | NOT NULL   |                                          |

UNIQUE(name, grade)

### Operation
| Column      | Type    | Constraints  | Notes                                      |
|-------------|---------|--------------|--------------------------------------------|
| id          | UUID    | PK           |                                            |
| name        | string  | NOT NULL     | e.g. "Drilling", "Spot Facing", "Turning" |
| description | string  | nullable     |                                            |
| category    | string  | NOT NULL     | e.g. "machining", "finishing", "treatment" |
| is_active   | boolean | NOT NULL     | Soft delete                                |
| created_at  | timestamp | NOT NULL   |                                            |

These are admin-managed. Tenants reference them but cannot modify them.

---

## 4. Tenant-Specific Rates

### MaterialRate
| Column         | Type    | Constraints        | Notes                                |
|----------------|---------|--------------------|--------------------------------------|
| id             | UUID    | PK                 |                                      |
| org_id         | UUID    | FK → Organization  |                                      |
| material_id    | UUID    | FK → Material      |                                      |
| rate_per_kg    | decimal | NOT NULL           |                                      |
| currency       | string  | NOT NULL, default "INR" |                                 |
| effective_from | date    | NOT NULL           | Allows rate updates without losing history |
| created_at     | timestamp | NOT NULL         |                                      |

UNIQUE(org_id, material_id, effective_from)

**Rate lookup:** For a given (org, material), pick the row with the latest `effective_from <= today`.

### WorkCenter
| Column      | Type    | Constraints                  | Notes                                   |
|-------------|---------|------------------------------|-----------------------------------------|
| id          | UUID    | PK                           |                                         |
| org_id      | UUID    | FK → Organization            |                                         |
| group_id    | UUID    | FK → UserGroup, nullable     | Informational tag only, no access control |
| name        | string  | NOT NULL                     | e.g. "CNC Lathe #3", "Vendor: ABC"     |
| type        | enum    | NOT NULL                     | in_house, vendor                        |
| description | string  | nullable                     |                                         |
| is_active   | boolean | NOT NULL                     |                                         |
| created_at  | timestamp | NOT NULL                   |                                         |

Any user in the org can use any work center regardless of group.

### WorkCenterRate
| Column         | Type    | Constraints               | Notes                                      |
|----------------|---------|---------------------------|--------------------------------------------|
| id             | UUID    | PK                        |                                            |
| work_center_id | UUID    | FK → WorkCenter           |                                            |
| operation_id   | UUID    | FK → Operation            |                                            |
| material_id    | UUID    | FK → Material, nullable   | null = default rate for any material       |
| rate_per_hour  | decimal | NOT NULL                  |                                            |
| currency       | string  | NOT NULL, default "INR"   |                                            |
| updated_at     | timestamp | NOT NULL                |                                            |

UNIQUE(work_center_id, operation_id, material_id)

**Rate lookup priority:**
1. Exact match: (work_center, operation, material) → use that rate
2. Fallback: (work_center, operation, material=NULL) → default rate
3. No match → flag to user as "rate not configured"

This lets a tenant set a general drilling rate on a CNC lathe, then override
specifically for harder materials like titanium at a higher rate.

---

## 5. Pricing Templates

### PricingTemplate
| Column      | Type      | Constraints        | Notes                                   |
|-------------|-----------|--------------------|-----------------------------------------|
| id          | UUID      | PK                 |                                         |
| org_id      | UUID      | FK → Organization  |                                         |
| name        | string    | NOT NULL           | e.g. "Standard Domestic", "Export"      |
| description | string    | nullable           |                                         |
| is_active   | boolean   | NOT NULL           |                                         |
| created_by  | UUID      | FK → User          |                                         |
| created_at  | timestamp | NOT NULL           |                                         |
| updated_at  | timestamp | NOT NULL           |                                         |

An org can have multiple active templates. User selects which to use per estimation.

### TemplateLineItem
| Column      | Type    | Constraints           | Notes                                          |
|-------------|---------|------------------------|-------------------------------------------------|
| id          | UUID    | PK                     |                                                 |
| template_id | UUID    | FK → PricingTemplate   |                                                 |
| name        | string  | NOT NULL               | e.g. "Commercial Overhead", "Volume Discount"   |
| description | string  | nullable               |                                                 |
| category    | enum    | NOT NULL               | overhead, discount                              |
| type        | enum    | NOT NULL               | percentage, fixed_per_unit                      |
| value       | decimal | NOT NULL               | The % or fixed ₹ amount                        |
| apply_on    | enum    | NOT NULL               | subtotal, material_cost, operation_cost         |
|             |         |                        | (ignored when type = fixed_per_unit)            |
| sort_order  | int     | NOT NULL               | Controls display & calculation order            |
| created_at  | timestamp | NOT NULL             |                                                 |

**Example: "Standard Domestic" template**

| name                 | category | type           | value | apply_on       |
|----------------------|----------|----------------|-------|----------------|
| Commercial Overhead  | overhead | percentage     | 8     | subtotal       |
| Packaging            | overhead | fixed_per_unit | 50    | —              |
| Freight              | overhead | fixed_per_unit | 30    | —              |
| Volume Discount      | discount | percentage     | 5     | subtotal       |

---

## 6. Cost Estimation (Snapshot)

All cost data is **snapshotted** at estimation time so that finalizing a quote freezes it
permanently, even if rates change later.

### CostEstimation
| Column        | Type      | Constraints               | Notes                              |
|---------------|-----------|---------------------------|------------------------------------|
| id            | UUID      | PK                        |                                    |
| org_id        | UUID      | FK → Organization         |                                    |
| variant_id    | UUID      | FK → ProductVariant       |                                    |
| extraction_id | UUID      | FK → VariantExtraction    |                                    |
| template_id   | UUID      | FK → PricingTemplate      | Which template seeded adjustments  |
| created_by    | UUID      | FK → User                 |                                    |
| status        | enum      | NOT NULL                  | draft, finalized                   |
| quantity      | int       | NOT NULL                  | Units being quoted                 |
| customer_name | string    | nullable                  | Free-text, searchable in app       |
| customer_ref  | string    | nullable                  | PO number, RFQ ref, etc.          |
| notes         | text      | nullable                  |                                    |
| created_at    | timestamp | NOT NULL                  |                                    |
| updated_at    | timestamp | NOT NULL                  |                                    |
| finalized_at  | timestamp | nullable                  | Set when status → finalized        |

### EstimationMaterialCost
| Column             | Type    | Constraints           | Notes                         |
|--------------------|---------|-----------------------|-------------------------------|
| id                 | UUID    | PK                    |                               |
| estimation_id      | UUID    | FK → CostEstimation   |                               |
| material_id        | UUID    | FK → Material         | Reference to catalog          |
| material_name      | string  | NOT NULL              | Snapshot                      |
| material_grade     | string  | NOT NULL              | Snapshot                      |
| weight_per_unit_kg | decimal | NOT NULL              |                               |
| rate_per_kg        | decimal | NOT NULL              | Snapshot of rate at est. time |
| cost_per_unit      | decimal | NOT NULL              | = weight × rate               |

Typically one row per estimation. Supports multiple rows for future composite parts.

### EstimationOperationCost
| Column           | Type    | Constraints           | Notes                                    |
|------------------|---------|-----------------------|------------------------------------------|
| id               | UUID    | PK                    |                                          |
| estimation_id    | UUID    | FK → CostEstimation   |                                          |
| operation_id     | UUID    | FK → Operation        | Reference to catalog                     |
| work_center_id   | UUID    | FK → WorkCenter       | Reference to tenant's machine            |
| material_id      | UUID    | FK → Material         | Material that drove the rate lookup      |
| operation_name   | string  | NOT NULL              | Snapshot                                 |
| work_center_name | string  | NOT NULL              | Snapshot                                 |
| material_name    | string  | NOT NULL              | Snapshot — e.g. "SS 316"                 |
| setup_time_hrs   | decimal | NOT NULL              |                                          |
| cycle_time_hrs   | decimal | NOT NULL              |                                          |
| rate_per_hour    | decimal | NOT NULL              | Snapshot from WorkCenterRate lookup       |
| cost_per_unit    | decimal | NOT NULL              | = (setup + cycle) × rate                 |
| notes            | string  | nullable              | e.g. "2 passes required"                 |

### EstimationAdjustment
| Column          | Type    | Constraints           | Notes                                      |
|-----------------|---------|-----------------------|--------------------------------------------|
| id              | UUID    | PK                    |                                            |
| estimation_id   | UUID    | FK → CostEstimation   |                                            |
| name            | string  | NOT NULL              | Snapshot (or user-entered for one-offs)    |
| category        | enum    | NOT NULL              | overhead, discount                         |
| type            | enum    | NOT NULL              | percentage, fixed_per_unit                 |
| value           | decimal | NOT NULL              |                                            |
| apply_on        | enum    | NOT NULL              | subtotal, material_cost, operation_cost    |
| computed_amount | decimal | NOT NULL              | Resolved ₹ per unit                       |
| sort_order      | int     | NOT NULL              |                                            |

**Seeded from the selected PricingTemplate's TemplateLineItems, but fully editable.**
User can modify values, add one-off lines (e.g. a negotiated discount), or remove
items that don't apply to this particular quote.

### EstimationSummary
| Column                  | Type    | Constraints                    | Notes                     |
|-------------------------|---------|--------------------------------|---------------------------|
| id                      | UUID    | PK                             |                           |
| estimation_id           | UUID    | FK → CostEstimation, UNIQUE    |                           |
| material_cost_per_unit  | decimal | NOT NULL                       | Sum of material costs     |
| operation_cost_per_unit | decimal | NOT NULL                       | Sum of operation costs    |
| subtotal_per_unit       | decimal | NOT NULL                       | material + operations     |
| overhead_per_unit       | decimal | NOT NULL                       | Sum of overhead amounts   |
| discount_per_unit       | decimal | NOT NULL                       | Sum of discount amounts   |
| net_cost_per_unit       | decimal | NOT NULL                       | subtotal + overhead - discount |
| total_cost              | decimal | NOT NULL                       | net × quantity            |
| currency                | string  | NOT NULL, default "INR"        |                           |

### EstimationReport
| Column        | Type      | Constraints           | Notes                         |
|---------------|-----------|-----------------------|-------------------------------|
| id            | UUID      | PK                    |                               |
| estimation_id | UUID      | FK → CostEstimation   |                               |
| report_path   | string    | NOT NULL              | File path to generated report |
| format        | enum      | NOT NULL              | pdf, xlsx                     |
| generated_by  | UUID      | FK → User             |                               |
| generated_at  | timestamp | NOT NULL              |                               |

---

## Cost Calculation Flow

```
┌──────────────────────────────────────────────────────┐
│  Material Cost (per unit)                            │
│  = SUM( weight_per_unit_kg × rate_per_kg )           │
│    (typically one material, supports multiple)        │
├──────────────────────────────────────────────────────┤
│  Operation Cost (per unit)                           │
│  = SUM( (setup_time + cycle_time) × rate_per_hour )  │
│    (one row per operation)                            │
├──────────────────────────────────────────────────────┤
│  Subtotal = Material Cost + Operation Cost           │
├──────────────────────────────────────────────────────┤
│  + Overheads                                         │
│    percentage items: value% × their apply_on base    │
│    fixed items: value per unit                       │
├──────────────────────────────────────────────────────┤
│  − Discounts                                         │
│    percentage items: value% × their apply_on base    │
│    fixed items: value per unit                       │
├──────────────────────────────────────────────────────┤
│  = Net Cost Per Unit                                 │
│  × Quantity = Total Cost                             │
└──────────────────────────────────────────────────────┘
```

---

## Indexing Recommendations

- `ProductFamily(org_id)` — list families for a tenant
- `ProductVariant(family_id)` — list variants in a family
- `MaterialRate(org_id, material_id, effective_from DESC)` — rate lookup
- `WorkCenterRate(work_center_id, operation_id, material_id)` — rate lookup
- `CostEstimation(org_id, status)` — list drafts/finalized per tenant
- `CostEstimation(org_id, customer_name)` — free-text customer search
- `TemplateLineItem(template_id, sort_order)` — ordered display
