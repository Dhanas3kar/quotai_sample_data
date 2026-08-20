"""
Dataset-specific structural checks.
"""
from typing import Dict, List
from . import ValidationResult
from .validators import is_required, is_numeric, is_positive, is_valid_date

def validate_legacy_material(row: Dict[str, str], row_idx: int) -> ValidationResult:
    """Validate a legacy material record."""
    dataset = "legacy_material"
    record_id = row.get("mat_code", f"row_{row_idx}")
    
    if not is_required(row.get("mat_code", "")):
        return ValidationResult(False, record_id, dataset, "MISSING_REQUIRED", "mat_code is required")
    
    if not is_required(row.get("mat_name", "")):
        return ValidationResult(False, record_id, dataset, "MISSING_REQUIRED", "mat_name is required")
        
    density = row.get("density", "")
    if is_required(density):
        if not is_numeric(density) or not is_positive(density):
            return ValidationResult(False, record_id, dataset, "INVALID_NUMERIC", "density must be a positive number")
            
    return ValidationResult(True, record_id, dataset)

def validate_legacy_material_rate(row: Dict[str, str], row_idx: int) -> ValidationResult:
    """Validate a legacy material rate record."""
    dataset = "legacy_material_rate"
    record_id = row.get("mat_code", f"row_{row_idx}")
    
    if not is_required(row.get("mat_code", "")):
        return ValidationResult(False, record_id, dataset, "MISSING_REQUIRED", "mat_code is required")
        
    rate = row.get("rate", "")
    if not is_required(rate) or not is_numeric(rate) or not is_positive(rate):
        return ValidationResult(False, record_id, dataset, "INVALID_NUMERIC", "rate must be a positive number")
        
    eff_date = row.get("effective_dt", "")
    if not is_required(eff_date) or not is_valid_date(eff_date):
        return ValidationResult(False, record_id, dataset, "INVALID_DATE", "effective_dt must be a valid YYYY-MM-DD date")

    return ValidationResult(True, record_id, dataset)
