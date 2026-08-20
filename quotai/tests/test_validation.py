import pytest
from quotai.validation.validators import is_required, is_numeric, is_positive, is_valid_date
from quotai.validation.schema_validator import validate_legacy_material

def test_is_required():
    assert is_required("value")
    assert not is_required("")
    assert not is_required(None)

def test_is_numeric():
    assert is_numeric("12.5")
    assert is_numeric("-5")
    assert not is_numeric("abc")
    assert not is_numeric("")

def test_is_positive():
    assert is_positive("12.5")
    assert not is_positive("-5")
    assert not is_positive("0")

def test_is_valid_date():
    assert is_valid_date("2024-01-01")
    assert not is_valid_date("01-01-2024")
    assert not is_valid_date("invalid")

def test_validate_legacy_material():
    valid_row = {"mat_code": "M1", "mat_name": "Steel", "density": "7800"}
    res = validate_legacy_material(valid_row, 0)
    assert res.is_valid

    invalid_row = {"mat_code": "M1", "mat_name": "", "density": "7800"}
    res = validate_legacy_material(invalid_row, 0)
    assert not res.is_valid
    assert res.error_type == "MISSING_REQUIRED"

    invalid_density = {"mat_code": "M1", "mat_name": "Steel", "density": "-1"}
    res = validate_legacy_material(invalid_density, 0)
    assert not res.is_valid
    assert res.error_type == "INVALID_NUMERIC"
