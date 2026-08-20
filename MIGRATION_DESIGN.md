# Migration Design

This document details the architectural rules behind the QuotAI data migration simulation. It explains how legacy CSV data is translated into normalized target models.

## 1. Source Schema
The legacy data represents unstructured or flat tables. 
- **Legacy Material**: `mat_code`, `mat_name`, `mat_grade`, `mat_cat`, `density`, `active`
- **Legacy Material Rate**: `mat_code`, `rate`, `effective_dt`

## 2. Target Schema
The target QuotAI system requires normalized types and consistent identifiers.
- **Material**: `id` (UUID-like), `name`, `grade`, `category`, `density`, `is_active` (boolean string), `created_at` (ISO timestamp)
- **Material Rate**: `material_id` (UUID-like reference), `rate_per_kg`, `effective_from` (ISO timestamp)

## 3. Mapping Rules
- `mat_code` → `id` (with UUID generation transformation)
- `mat_name` → `name`
- `rate` → `rate_per_kg` (formatted to 2 decimal places)
- `effective_dt` → `effective_from` (appended with T00:00:00Z)

## 4. Validation Rules
Validation uses a `ValidationResult` structured object.
- **Generic**: Required checks, numeric type checks, positive value checks, date formatting.
- **Dataset-specific**: Material rows must have a code and name. Rates must have a valid numerical rate.
- **Referential Integrity**: Material Rates must reference a `mat_code` that is present and valid in the Materials dataset.

## 5. Transformation Rules
- Empty categories are assigned an `unclassified` default.
- Legacy `Y`/`N` flags are explicitly converted to `true`/`false`.
- Deterministic ID resolution is used to convert legacy codes into internal UUID formats for relational mapping.

## 6. Error Handling (Quarantine)
Invalid records do not crash the pipeline and are not silently dropped. 
Instead, they generate a `ValidationResult(is_valid=False)` and are written to `output/rejected/rejected_records.csv` containing:
- Record identifier
- Error type (e.g. `MISSING_REQUIRED`, `INVALID_NUMERIC`)
- Error message
- The raw source row data

## 7. Reconciliation
A `migration_report.json` is generated to prove data isn't mysteriously disappearing.
It verifies: `source_count == valid_count + rejected_count`.

## 8. Idempotency
Executing the migration pipeline repeatedly on the same source data will not duplicate target records.
Idempotency is enforced by tracking composite keys (e.g., `material_id` + `effective_from`) during the migration run.
*(In a production system, this would be an upsert operation against a live database).*

## 9. Known Limitations
- Runs completely in-memory. Not optimized for multi-gigabyte files (would require chunking or streaming).
- Referential integrity is only checked against the data within the current migration batch, not against a persistent target database.
