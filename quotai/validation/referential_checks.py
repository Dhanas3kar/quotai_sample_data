"""
Referential integrity checks.
"""
from typing import Dict, List, Set
from . import ValidationResult

def check_material_references(rates: List[Dict[str, str]], valid_material_codes: Set[str]) -> List[ValidationResult]:
    """Ensure all rates point to a valid material code."""
    results = []
    dataset = "legacy_material_rate"
    
    for idx, row in enumerate(rates):
        record_id = row.get("mat_code", f"row_{idx}")
        if record_id not in valid_material_codes:
            results.append(ValidationResult(
                is_valid=False,
                record_id=record_id,
                dataset=dataset,
                error_type="INVALID_REFERENCE",
                message=f"Material code {record_id} does not exist in materials dataset."
            ))
        else:
            results.append(ValidationResult(True, record_id, dataset))
            
    return results
