import pytest
from quotai.pipeline.transformer import transform_material

def test_transform_material():
    row = {
        "mat_code": "MAT-01",
        "mat_name": "Steel",
        "mat_grade": "316",
        "mat_cat": "",
        "density": "8000",
        "active": "Y"
    }
    
    tgt = transform_material(row)
    assert tgt["id"] == "40000000-0000-0000-0000-000000000001"
    assert tgt["name"] == "Steel"
    assert tgt["grade"] == "316"
    assert tgt["category"] == "unclassified" # Default value applied
    assert tgt["is_active"] == "true"
    assert "created_at" in tgt
