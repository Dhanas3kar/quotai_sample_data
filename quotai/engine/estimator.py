"""
CostEstimator — the main orchestration class for QuotAI.

Implements the full 5-step estimation flow from the QuotAI data model:

1. Select a **product family** (with a reference drawing)
2. Select / upload a **variant drawing** — AI extracts features using the
   reference as grounding context
3. Look up **material rates** and **work center operation rates** from DB
4. Apply a **pricing template** (configurable overheads & discounts)
5. Produce a **frozen cost estimation** with a generated report
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from quotai.data.csv_loader import CSVDataLoader

from quotai.engine.material_cost import compute_weight, compute_material_cost
from quotai.engine.operation_cost import compute_all_operations
from quotai.engine.pricing_engine import apply_pricing_template
from quotai.utils.math_utils import to_decimal, round_currency


class EstimationError(Exception):
    """Raised when the estimation pipeline cannot proceed."""


class CostEstimator:
    """
    End-to-end manufacturing cost estimation engine.

    Follows the QuotAI data-model flow:

    1. Select a **product family** (→ loads its reference drawing extraction)
    2. Select a **variant** inside that family (→ AI extraction grounded by
       the reference baseline)
    3. Look up **material rates** (₹/kg, effective-date aware) and
       **work-center operation rates** (exact material match → fallback null)
    4. Apply a **pricing template** (overheads & discounts on subtotal /
       material / operation bases)
    5. Produce a **frozen cost estimation snapshot** — all numbers are
       snapshotted so the quote never changes even if rates are updated later

    Usage
    -----
    >>> estimator = CostEstimator("sample_data")
    >>> result = estimator.estimate(
    ...     variant="Spacer v1 - Standard",
    ...     quantity=100,
    ...     scrap_percent=5,
    ...     effective_date="2026-03-09",
    ... )
    """

    def __init__(self, data_dir: str) -> None:
        """
        Parameters
        ----------
        data_dir : str
            Path to the directory containing the CSV sample data files.
        """
        self.loader = CSVDataLoader(data_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def estimate(
        self,
        features: Dict,
        quantity: int = 1,
        scrap_percent: float = 0.0,
        effective_date: str = "2026-03-09",
        template_name: str = "Standard Domestic",
        variant_name: str = "Unknown Variant",
        family_name: Optional[str] = None,
    ) -> Dict:
        """
        Run the full estimation pipeline and return a frozen result.

        Parameters
        ----------
        features : dict
            The pre-extracted or externally supplied features (e.g., dimensions, material_hint).
        quantity : int
            Number of units to quote.
        scrap_percent : float
            Scrap allowance as a percentage (e.g. ``5`` for 5 %).
        effective_date : str
            ISO date string used for rate lookups.
        template_name : str
            Name of the pricing template to apply.
        variant_name : str
            Name or keyword identifying the product variant (for reporting).
        family_name : str | None
            If provided, selects the parent product family explicitly.

        Returns
        -------
        dict
            Frozen cost estimation snapshot.
        """
        eff_date = date.fromisoformat(effective_date)

        # ──────────────────────────────────────────────────────────────
        # STEP 1  Select product family (for snapshotting context)
        # ──────────────────────────────────────────────────────────────
        family, variant_row = self._resolve_family_and_variant(variant_name, family_name)

        # In the new architecture, features are provided directly to this engine.
        # No mock AI extraction is performed.
        
        # ──────────────────────────────────────────────────────────────
        # STEP 2  Look up material rates & work-center operation rates
        # ──────────────────────────────────────────────────────────────
        material_hint = features.get("material_hint", "Stainless Steel")
        material = self.loader.get_material_by_name(material_hint)
        if material is None:
            raise EstimationError(
                f"Material not found for hint '{material_hint}'. "
                "Check sample_data/material.csv."
            )

        density = Decimal(material["density"])

        # -- Material cost --
        weight_kg = compute_weight(features, density, to_decimal(scrap_percent))

        rate_per_kg = self.loader.get_material_rate(material["id"], eff_date)
        if rate_per_kg is None:
            raise EstimationError(
                f"No material rate found for '{material['name']}' "
                f"effective on {effective_date}. "
                "Check sample_data/material_rate.csv."
            )

        mat_cost = compute_material_cost(weight_kg, rate_per_kg)

        # -- Operation costs (uses work-center rate lookup) --
        operations = self.loader.get_operations_list()
        op_details = compute_all_operations(features, operations, self.loader)
        op_cost = sum(
            (op["cost_per_unit"] for op in op_details), Decimal("0")
        )

        subtotal = round_currency(mat_cost + op_cost)

        # ──────────────────────────────────────────────────────────────
        # STEP 4  Apply pricing template (overheads & discounts)
        # ──────────────────────────────────────────────────────────────
        template = self.loader.get_pricing_template_by_name(template_name)
        if template is None:
            raise EstimationError(
                f"Pricing template '{template_name}' not found. "
                "Check sample_data/pricing_template.csv."
            )

        line_items = self.loader.get_template_line_items(template["id"])
        pricing = apply_pricing_template(
            subtotal, mat_cost, op_cost, line_items, quantity
        )

        # ──────────────────────────────────────────────────────────────
        # STEP 5  Produce frozen cost estimation snapshot
        # ──────────────────────────────────────────────────────────────
        estimation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        family_name_snap = family["name"] if family else "N/A"

        frozen = self._build_frozen_snapshot(
            estimation_id=estimation_id,
            timestamp=now,
            variant_name=variant_name,
            family_name=family_name_snap,
            features=features,
            material=material,
            material_id=material["id"],
            weight_kg=weight_kg,
            rate_per_kg=rate_per_kg,
            mat_cost=mat_cost,
            op_details=op_details,
            op_cost=op_cost,
            subtotal=subtotal,
            pricing=pricing,
            template=template,
            quantity=quantity,
            scrap_percent=scrap_percent,
            effective_date=effective_date,
        )

        return frozen

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_family_and_variant(
        self, variant_name: str, family_name: Optional[str]
    ) -> tuple:
        """
        Resolve the product family and variant row from the CSV data.

        If *family_name* is given, look up the family first, then find the
        variant inside it.  Otherwise try to find the variant directly and
        walk up to its parent family.

        Returns ``(family_row | None, variant_row | None)``.
        """
        family = None
        variant_row = None

        if family_name:
            family = self.loader.get_family_by_name(family_name)
            if family:
                for v in self.loader.get_variants_for_family(family["id"]):
                    if variant_name.lower() in v["name"].lower():
                        variant_row = v
                        break

        if variant_row is None:
            variant_row = self.loader.get_variant_by_name(variant_name)

        if variant_row and family is None:
            family = self.loader.get_family_for_variant(variant_row["id"])

        return family, variant_row

    @staticmethod
    def _build_frozen_snapshot(
        *,
        estimation_id: str,
        timestamp: str,
        variant_name: str,
        family_name: str,
        features: Dict,
        material: Dict,
        material_id: str,
        weight_kg: Decimal,
        rate_per_kg: Decimal,
        mat_cost: Decimal,
        op_details: List[Dict],
        op_cost: Decimal,
        subtotal: Decimal,
        pricing: Dict,
        template: Dict,
        quantity: int,
        scrap_percent: float,
        effective_date: str,
    ) -> Dict:
        """
        Assemble a frozen estimation snapshot matching the data-model tables:

        - ``CostEstimation``
        - ``EstimationMaterialCost``
        - ``EstimationOperationCost``
        - ``EstimationAdjustment``
        - ``EstimationSummary``
        """
        material_name = material["name"]
        material_grade = material["grade"]
        material_display = f"{material_name} {material_grade}"

        # -- EstimationMaterialCost snapshot --
        frozen_material = {
            "material_name": material_name,
            "material_grade": material_grade,
            "material_id": material_id,
            "weight_per_unit_kg": weight_kg,
            "rate_per_kg": rate_per_kg,
            "cost_per_unit": mat_cost,
        }

        # -- EstimationOperationCost snapshots --
        frozen_operations = []
        for op in op_details:
            frozen_operations.append({
                "operation_name": op["operation_name"],
                "operation_id": op.get("operation_id", ""),
                "work_center_name": op["work_center_name"],
                "work_center_id": op.get("work_center_id", ""),
                "material_name": material_display,
                "material_id": material_id,
                "setup_time_hrs": op["setup_time_hrs"],
                "cycle_time_hrs": op["cycle_time_hrs"],
                "rate_per_hour": op["rate_per_hour"],
                "cost_per_unit": op["cost_per_unit"],
            })

        # -- EstimationAdjustment snapshots --
        frozen_adjustments = []
        for idx, adj in enumerate(pricing["adjustments"]):
            frozen_adjustments.append({
                "name": adj["name"],
                "category": adj["category"],
                "type": adj["type"],
                "value": adj["value"],
                "apply_on": adj["apply_on"],
                "computed_amount": adj["computed_amount"],
                "sort_order": idx + 1,
            })

        # -- EstimationSummary snapshot --
        frozen_summary = {
            "material_cost_per_unit": mat_cost,
            "operation_cost_per_unit": op_cost,
            "subtotal_per_unit": subtotal,
            "overhead_per_unit": pricing["total_overheads"],
            "discount_per_unit": pricing["total_discounts"],
            "net_cost_per_unit": pricing["net_cost_per_unit"],
            "total_cost": pricing["total_cost"],
            "currency": "INR",
        }

        return {
            # CostEstimation header
            "estimation_id": estimation_id,
            "status": "draft",
            "created_at": timestamp,
            "variant": variant_name,
            "family_name": family_name,
            "quantity": quantity,
            "scrap_percent": scrap_percent,
            "effective_date": effective_date,
            "template_name": template["name"],
            "template_id": template["id"],
            "currency": "INR",

            # Feature extraction context
            "features": features,


            # Frozen cost snapshots
            "material_snapshot": frozen_material,
            "operation_snapshots": frozen_operations,
            "adjustment_snapshots": frozen_adjustments,
            "summary": frozen_summary,

            # EstimationReport placeholder
            "report": {
                "report_path": None,
                "format": "html",
                "generated_at": timestamp,
            },

            # Convenience top-level accessors (for UI / reports)
            "material_name": material_display,
            "weight_kg": weight_kg,
            "rate_per_kg": rate_per_kg,
            "material_cost": mat_cost,
            "operation_details": frozen_operations,
            "operation_cost": op_cost,
            "subtotal": subtotal,
            "adjustments": frozen_adjustments,
            "overheads": pricing["total_overheads"],
            "discounts": pricing["total_discounts"],
            "net_cost_per_unit": pricing["net_cost_per_unit"],
            "total_cost": pricing["total_cost"],
        }
