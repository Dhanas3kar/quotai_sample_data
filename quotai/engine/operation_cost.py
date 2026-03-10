"""
Operation cost calculation module.

Estimates machining time based on part geometry and computes
cost using work-center hourly rates.
"""

from decimal import Decimal
from typing import Dict, List

from quotai.utils.math_utils import to_decimal, round_currency


# ---------------------------------------------------------------------------
# Time estimation heuristics (simplified for prototype)
# ---------------------------------------------------------------------------

def _turning_time(features: Dict) -> Decimal:
    """Estimate turning time (hours) from OD, ID, and length."""
    od = to_decimal(features["outer_diameter_mm"])
    length = to_decimal(features["length_mm"])
    # Heuristic: base setup 0.25 hr + proportional to surface area
    setup = Decimal("0.25")
    cycle = (od * length / Decimal("10000")).quantize(Decimal("0.01"))
    cycle = max(cycle, Decimal("0.20"))
    return setup, cycle


def _drilling_time(features: Dict) -> Decimal:
    """Estimate drilling time (hours) based on hole count."""
    holes = features.get("holes", [])
    total_holes = sum(h.get("count", 0) for h in holes)
    setup = Decimal("0.10")
    # ~2 minutes per hole
    cycle = (to_decimal(total_holes) * Decimal("0.033")).quantize(Decimal("0.01"))
    cycle = max(cycle, Decimal("0.05"))
    return setup, cycle


def _spot_facing_time(features: Dict) -> Decimal:
    """Estimate spot-facing time (hours) based on hole count."""
    holes = features.get("holes", [])
    total_holes = sum(h.get("count", 0) for h in holes)
    setup = Decimal("0.10")
    cycle = (to_decimal(total_holes) * Decimal("0.025")).quantize(Decimal("0.01"))
    cycle = max(cycle, Decimal("0.05"))
    return setup, cycle


def _grinding_time(features: Dict) -> Decimal:
    """Estimate surface grinding time (hours)."""
    od = to_decimal(features["outer_diameter_mm"])
    setup = Decimal("0.15")
    cycle = (od / Decimal("500")).quantize(Decimal("0.01"))
    cycle = max(cycle, Decimal("0.15"))
    return setup, cycle


def _heat_treatment_time(features: Dict) -> Decimal:
    """Estimate heat treatment time (hours)."""
    length = to_decimal(features["length_mm"])
    setup = Decimal("0.00")
    cycle = (length / Decimal("200")).quantize(Decimal("0.01"))
    cycle = max(cycle, Decimal("0.40"))
    return setup, cycle


# Map operation names to their time estimators
_TIME_ESTIMATORS = {
    "turning": _turning_time,
    "drilling": _drilling_time,
    "spot facing": _spot_facing_time,
    "surface grinding": _grinding_time,
    "heat treatment": _heat_treatment_time,
}


def compute_operation_time(operation_name: str,
                           features: Dict) -> tuple:
    """
    Estimate setup and cycle time for a given operation.

    Parameters
    ----------
    operation_name : str
        Name of the manufacturing operation (e.g. ``"Drilling"``).
    features : dict
        Geometric features of the part.

    Returns
    -------
    tuple[Decimal, Decimal]
        ``(setup_time_hrs, cycle_time_hrs)``
    """
    key = operation_name.lower().strip()
    estimator = _TIME_ESTIMATORS.get(key)
    if estimator is None:
        # Unknown operation — return conservative defaults
        return Decimal("0.10"), Decimal("0.20")
    return estimator(features)


def compute_operation_cost(setup_hrs: Decimal,
                           cycle_hrs: Decimal,
                           rate_per_hour: Decimal) -> Decimal:
    """
    Calculate total cost for a single operation.

    cost = (setup + cycle) × rate_per_hour
    """
    total_time = to_decimal(setup_hrs) + to_decimal(cycle_hrs)
    return round_currency(total_time * to_decimal(rate_per_hour))


def compute_all_operations(features: Dict,
                           operations: List[Dict],
                           loader) -> List[Dict]:
    """
    Run cost estimation for every active operation.

    Parameters
    ----------
    features : dict
        Part geometric features.
    operations : list[dict]
        List of operation rows from CSV.
    loader : CSVDataLoader
        Data loader instance for rate lookups.

    Returns
    -------
    list[dict]
        Each entry contains::

            {
                "operation_name": str,
                "work_center_name": str,
                "setup_time_hrs": Decimal,
                "cycle_time_hrs": Decimal,
                "rate_per_hour": Decimal,
                "cost_per_unit": Decimal,
            }
    """
    results: List[Dict] = []
    material_hint = features.get("material_hint", "")
    material = loader.get_material_by_name(material_hint)
    material_id = material["id"] if material else None

    for op in operations:
        op_name = op["name"]
        op_id = op["id"]

        # Get time estimate
        setup, cycle = compute_operation_time(op_name, features)

        # Look up rate (priority: exact material match → null fallback)
        rate_row = loader.get_work_center_rate(op_id, material_id)
        if rate_row is None:
            # Data-model rule: "No match → flag to user as rate not configured"
            results.append({
                "operation_name": op_name,
                "operation_id": op_id,
                "work_center_name": "— not configured —",
                "work_center_id": "",
                "setup_time_hrs": setup,
                "cycle_time_hrs": cycle,
                "rate_per_hour": Decimal("0"),
                "cost_per_unit": Decimal("0"),
                "rate_missing": True,
            })
            continue

        rate = Decimal(rate_row["rate_per_hour"])
        wc_id = rate_row["work_center_id"]

        # Resolve work center name
        wc = loader.get_work_center_by_id(wc_id)
        wc_name = wc["name"] if wc else wc_id

        cost = compute_operation_cost(setup, cycle, rate)

        results.append({
            "operation_name": op_name,
            "operation_id": op_id,
            "work_center_name": wc_name,
            "work_center_id": wc_id,
            "setup_time_hrs": setup,
            "cycle_time_hrs": cycle,
            "rate_per_hour": rate,
            "cost_per_unit": cost,
            "rate_missing": False,
        })

    return results
