"""
Data transformation and normalization.
"""
from typing import Dict, Any
from .schema import MATERIAL_MAPPING, MATERIAL_RATE_MAPPING
import datetime

def transform_material(row: Dict[str, str]) -> Dict[str, Any]:
    """Transform legacy material to target schema."""
    transformed = {}
    for src_col, tgt_col in MATERIAL_MAPPING.items():
        transformed[tgt_col] = row.get(src_col, "")
        
    # Normalization: Default category if empty
    if not transformed["category"]:
        transformed["category"] = "unclassified"
        
    # Normalization: Map 'Y'/'N' to 'true'/'false'
    active_val = transformed.get("is_active", "Y").upper()
    transformed["is_active"] = "true" if active_val == "Y" else "false"
    
    # Generate an ISO timestamp for created_at
    transformed["created_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # ID mapping: Prefix with 'MAT-' if it's just numbers, but legacy is already MAT-XX.
    # In target it uses UUIDs, but for this simulation we will use deterministic IDs based on legacy code.
    # We will generate a mock UUID from the material code.
    mat_code = transformed["id"]
    # E.g. MAT-01 -> 00000000-0000-0000-0000-00000000M001
    num = mat_code.split("-")[-1] if "-" in mat_code else "00"
    transformed["id"] = f"40000000-0000-0000-0000-00000000{num.zfill(4)}"
    
    return transformed

def transform_material_rate(row: Dict[str, str], material_uuid_map: Dict[str, str]) -> Dict[str, Any]:
    """Transform legacy material rate to target schema."""
    transformed = {}
    for src_col, tgt_col in MATERIAL_RATE_MAPPING.items():
        transformed[tgt_col] = row.get(src_col, "")
        
    # Map the legacy material_id (MAT-01) to the target UUID
    legacy_code = transformed["material_id"]
    transformed["material_id"] = material_uuid_map.get(legacy_code, legacy_code)
    
    # Ensure rate has exactly two decimals if possible
    try:
        rate_val = float(transformed["rate_per_kg"])
        transformed["rate_per_kg"] = f"{rate_val:.2f}"
    except ValueError:
        pass
        
    # ISO date
    dt = transformed["effective_from"]
    transformed["effective_from"] = f"{dt}T00:00:00Z"
    
    return transformed
