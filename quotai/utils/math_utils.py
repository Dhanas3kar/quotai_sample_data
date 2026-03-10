"""
Utility functions for precise financial and geometric calculations.

All monetary and weight values use Decimal to avoid floating-point errors
that are unacceptable in manufacturing cost estimation.
"""

from decimal import Decimal, ROUND_HALF_UP
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PI = Decimal(str(math.pi))
MM3_PER_M3 = Decimal("1e9")  # 1 m³ = 1 000 000 000 mm³
G_PER_KG = Decimal("1000")


# ---------------------------------------------------------------------------
# Rounding helpers
# ---------------------------------------------------------------------------

def round_currency(value: Decimal, places: int = 2) -> Decimal:
    """Round a Decimal value to *places* decimal digits (default 2)."""
    quantize_str = "0." + "0" * places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def to_decimal(value) -> Decimal:
    """Safely convert any numeric value to Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def cylinder_volume_mm3(outer_diameter_mm: Decimal,
                        inner_diameter_mm: Decimal,
                        length_mm: Decimal) -> Decimal:
    """
    Volume of a hollow cylinder in mm³.

    V = π / 4 × (OD² − ID²) × L
    """
    od = to_decimal(outer_diameter_mm)
    id_ = to_decimal(inner_diameter_mm)
    length = to_decimal(length_mm)
    return PI / 4 * (od ** 2 - id_ ** 2) * length


def hole_volume_mm3(diameter_mm: Decimal, depth_mm: Decimal) -> Decimal:
    """
    Volume of a single cylindrical hole in mm³.

    V = π / 4 × D² × depth
    """
    d = to_decimal(diameter_mm)
    dep = to_decimal(depth_mm)
    return PI / 4 * d ** 2 * dep


def volume_mm3_to_kg(volume_mm3: Decimal, density_kg_m3: Decimal) -> Decimal:
    """
    Convert a volume in mm³ to mass in kg given density in kg/m³.

    mass = volume_mm³ × density / 1e9
    """
    return to_decimal(volume_mm3) * to_decimal(density_kg_m3) / MM3_PER_M3


def apply_scrap_percent(weight_kg: Decimal, scrap_percent: Decimal) -> Decimal:
    """
    Increase weight by scrap percentage.

    adjusted = weight × (1 + scrap% / 100)
    """
    factor = Decimal("1") + to_decimal(scrap_percent) / Decimal("100")
    return to_decimal(weight_kg) * factor
