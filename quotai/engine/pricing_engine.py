"""
Pricing engine — applies overhead and discount template line items.

Processes the pricing template to compute final adjustments on top of
the raw material + operation subtotal.
"""

from decimal import Decimal
from typing import Dict, List, Tuple

from quotai.utils.math_utils import to_decimal, round_currency


def _resolve_base(apply_on: str,
                  subtotal: Decimal,
                  material_cost: Decimal,
                  operation_cost: Decimal) -> Decimal:
    """Return the base amount that a percentage adjustment applies to."""
    mapping = {
        "subtotal": subtotal,
        "material_cost": material_cost,
        "operation_cost": operation_cost,
    }
    return mapping.get(apply_on, subtotal)


def apply_pricing_template(subtotal: Decimal,
                           material_cost: Decimal,
                           operation_cost: Decimal,
                           template_lines: List[Dict],
                           quantity: int) -> Dict:
    """
    Apply pricing template adjustments to the subtotal.

    Parameters
    ----------
    subtotal : Decimal
        Material cost + operation cost per unit.
    material_cost : Decimal
        Per-unit material cost.
    operation_cost : Decimal
        Per-unit operation cost.
    template_lines : list[dict]
        Sorted list of ``TemplateLineItem`` rows.
    quantity : int
        Number of units being quoted.

    Returns
    -------
    dict
        ::

            {
                "adjustments": [
                    {"name", "category", "type", "value",
                     "apply_on", "computed_amount"},
                    ...
                ],
                "total_overheads": Decimal,
                "total_discounts": Decimal,
                "net_cost_per_unit": Decimal,
                "total_cost": Decimal,
            }
    """
    subtotal = to_decimal(subtotal)
    material_cost = to_decimal(material_cost)
    operation_cost = to_decimal(operation_cost)

    adjustments: List[Dict] = []
    total_overheads = Decimal("0")
    total_discounts = Decimal("0")

    for line in template_lines:
        name = line["name"]
        category = line["category"]  # overhead | discount
        adj_type = line["type"]      # percentage | fixed_per_unit
        value = to_decimal(line["value"])
        apply_on = line.get("apply_on", "subtotal")

        if adj_type == "percentage":
            base = _resolve_base(apply_on, subtotal, material_cost, operation_cost)
            computed = round_currency(base * value / Decimal("100"))
        else:  # fixed_per_unit
            computed = round_currency(value)

        adjustments.append({
            "name": name,
            "category": category,
            "type": adj_type,
            "value": value,
            "apply_on": apply_on,
            "computed_amount": computed,
        })

        if category == "overhead":
            total_overheads += computed
        elif category == "discount":
            total_discounts += computed

    net_cost_per_unit = round_currency(subtotal + total_overheads - total_discounts)
    total_cost = round_currency(net_cost_per_unit * to_decimal(quantity))

    return {
        "adjustments": adjustments,
        "total_overheads": total_overheads,
        "total_discounts": total_discounts,
        "net_cost_per_unit": net_cost_per_unit,
        "total_cost": total_cost,
    }
