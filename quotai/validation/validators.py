"""
Generic validation checks.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime

def is_required(value: str) -> bool:
    """Check if value is present."""
    return value is not None and str(value).strip() != ""

def is_numeric(value: str) -> bool:
    """Check if value can be converted to Decimal."""
    try:
        if not is_required(value):
            return False
        Decimal(str(value))
        return True
    except InvalidOperation:
        return False

def is_positive(value: str) -> bool:
    """Check if value is a positive number."""
    if not is_numeric(value):
        return False
    return Decimal(str(value)) > 0

def is_valid_date(value: str, date_format: str = "%Y-%m-%d") -> bool:
    """Check if value matches the date format."""
    try:
        if not is_required(value):
            return False
        datetime.strptime(str(value), date_format)
        return True
    except ValueError:
        return False
