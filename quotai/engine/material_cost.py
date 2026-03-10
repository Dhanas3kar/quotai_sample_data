"""
Material cost calculation module.

Computes part weight from geometric features and calculates
material cost using the applicable rate per kg.
"""

from decimal import Decimal
from typing import Dict, List

from quotai.utils.math_utils import (
    to_decimal,
    cylinder_volume_mm3,
    hole_volume_mm3,
    volume_mm3_to_kg,
    apply_scrap_percent,
    round_currency,
)


def compute_weight(features: Dict,
                   density_kg_m3: Decimal,
                   scrap_percent: Decimal = Decimal("0")) -> Decimal:
    """
    Compute the net weight (kg) of a part from its geometric features.

    Steps
    -----
    1. Calculate hollow-cylinder (blank) volume.
    2. Subtract hole volumes.
    3. Convert mm³ → kg using material density.
    4. Add scrap allowance.

    Parameters
    ----------
    features : dict
        Must contain ``outer_diameter_mm``, ``inner_diameter_mm``,
        ``length_mm``, and optionally ``holes``.
    density_kg_m3 : Decimal
        Material density in kg/m³.
    scrap_percent : Decimal
        Additional scrap percentage (e.g. ``5`` for 5 %).

    Returns
    -------
    Decimal
        Weight in kg, rounded to 4 decimal places.
    """
    od = to_decimal(features["outer_diameter_mm"])
    id_ = to_decimal(features["inner_diameter_mm"])
    length = to_decimal(features["length_mm"])

    # Blank volume (hollow cylinder)
    blank_vol = cylinder_volume_mm3(od, id_, length)

    # Subtract holes
    total_hole_vol = Decimal("0")
    for hole_group in features.get("holes", []):
        h_dia = to_decimal(hole_group["diameter_mm"])
        h_count = to_decimal(hole_group["count"])
        # Assume through-holes spanning the full wall thickness
        wall_thickness = (od - id_) / 2
        single_hole = hole_volume_mm3(h_dia, wall_thickness)
        total_hole_vol += single_hole * h_count

    net_vol = blank_vol - total_hole_vol

    # Convert to mass
    weight_kg = volume_mm3_to_kg(net_vol, to_decimal(density_kg_m3))

    # Apply scrap
    weight_kg = apply_scrap_percent(weight_kg, scrap_percent)

    return weight_kg.quantize(Decimal("0.0001"))


def compute_material_cost(weight_kg: Decimal,
                          rate_per_kg: Decimal) -> Decimal:
    """
    Calculate material cost.

    Parameters
    ----------
    weight_kg : Decimal
        Part weight in kg (including scrap allowance).
    rate_per_kg : Decimal
        Material price per kg in local currency.

    Returns
    -------
    Decimal
        Material cost rounded to 2 decimal places.
    """
    return round_currency(to_decimal(weight_kg) * to_decimal(rate_per_kg))
