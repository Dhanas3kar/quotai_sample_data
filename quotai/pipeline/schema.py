"""
Explicit source-to-target mapping schemas.
"""

MATERIAL_MAPPING = {
    "mat_code": "id",
    "mat_name": "name",
    "mat_grade": "grade",
    "mat_cat": "category",
    "density": "density",
    "active": "is_active"
}

MATERIAL_RATE_MAPPING = {
    "mat_code": "material_id",
    "rate": "rate_per_kg",
    "effective_dt": "effective_from"
}
