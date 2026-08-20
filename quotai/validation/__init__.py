"""
Validation layer for QuotAI ETL pipeline.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationResult:
    """Structured result of a validation check."""
    is_valid: bool
    record_id: Optional[str]
    dataset: str
    error_type: Optional[str] = None
    message: Optional[str] = None

