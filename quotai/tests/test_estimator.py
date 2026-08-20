"""
Unit tests for the QuotAI cost estimation engine.

Run with:  pytest quotai/tests/test_estimator.py -v
"""

import os
import sys
from decimal import Decimal

import pytest

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quotai.utils.math_utils import (
    cylinder_volume_mm3,
    hole_volume_mm3,
    volume_mm3_to_kg,
    apply_scrap_percent,
    round_currency,
    to_decimal,
)
from quotai.engine.material_cost import compute_weight, compute_material_cost
from quotai.engine.operation_cost import compute_operation_time, compute_operation_cost
from quotai.engine.pricing_engine import apply_pricing_template

from quotai.engine.estimator import CostEstimator, EstimationError

SAMPLE_DATA_DIR = os.path.join(PROJECT_ROOT, "sample_data")


# ────────────────────────────────────────────────────────────────────────
# Math utilities
# ────────────────────────────────────────────────────────────────────────

class TestMathUtils:
    """Tests for math_utils helper functions."""

    def test_cylinder_volume_solid(self):
        """A solid cylinder (ID=0) should have V = π/4 × OD² × L."""
        vol = cylinder_volume_mm3(Decimal("100"), Decimal("0"), Decimal("100"))
        # π/4 × 10000 × 100 ≈ 785,398.16 mm³
        assert Decimal("785000") < vol < Decimal("786000")

    def test_cylinder_volume_hollow(self):
        """Hollow cylinder volume should be less than solid."""
        solid = cylinder_volume_mm3(Decimal("100"), Decimal("0"), Decimal("100"))
        hollow = cylinder_volume_mm3(Decimal("100"), Decimal("50"), Decimal("100"))
        assert hollow < solid

    def test_hole_volume(self):
        """A hole of 10 mm diameter and 25 mm depth."""
        vol = hole_volume_mm3(Decimal("10"), Decimal("25"))
        # π/4 × 100 × 25 ≈ 1963.5 mm³
        assert Decimal("1960") < vol < Decimal("1970")

    def test_volume_to_kg(self):
        """Convert a known volume to mass."""
        # 1,000,000 mm³ = 0.001 m³ at 8000 kg/m³ → 8 kg
        mass = volume_mm3_to_kg(Decimal("1000000"), Decimal("8000"))
        assert mass == Decimal("8")

    def test_scrap_percent(self):
        """5% scrap on 2.0 kg → 2.1 kg."""
        result = apply_scrap_percent(Decimal("2.0"), Decimal("5"))
        assert result == Decimal("2.10")

    def test_round_currency(self):
        """Test standard rounding."""
        assert round_currency(Decimal("1.235")) == Decimal("1.24")
        assert round_currency(Decimal("1.2349")) == Decimal("1.23")


# ────────────────────────────────────────────────────────────────────────
# Weight & material cost
# ────────────────────────────────────────────────────────────────────────

class TestMaterialCost:
    """Tests for material cost calculations."""

    def test_compute_weight_basic(self):
        """Weight of a simple hollow cylinder with no holes."""
        features = {
            "outer_diameter_mm": 120,
            "inner_diameter_mm": 60,
            "length_mm": 80,
            "holes": [],
        }
        weight = compute_weight(features, Decimal("8000"), Decimal("0"))
        # Should be positive and reasonable (~5–7 kg range for SS)
        assert weight > Decimal("0")
        assert weight < Decimal("20")

    def test_compute_weight_with_scrap(self):
        """Adding scrap should increase weight."""
        features = {
            "outer_diameter_mm": 100,
            "inner_diameter_mm": 50,
            "length_mm": 60,
            "holes": [],
        }
        w_no_scrap = compute_weight(features, Decimal("8000"), Decimal("0"))
        w_with_scrap = compute_weight(features, Decimal("8000"), Decimal("10"))
        assert w_with_scrap > w_no_scrap

    def test_compute_weight_with_holes(self):
        """Holes should reduce weight (before scrap)."""
        base_features = {
            "outer_diameter_mm": 120,
            "inner_diameter_mm": 60,
            "length_mm": 80,
            "holes": [],
        }
        hole_features = {
            "outer_diameter_mm": 120,
            "inner_diameter_mm": 60,
            "length_mm": 80,
            "holes": [{"diameter_mm": 10, "count": 6}],
        }
        w_solid = compute_weight(base_features, Decimal("8000"), Decimal("0"))
        w_holes = compute_weight(hole_features, Decimal("8000"), Decimal("0"))
        assert w_holes < w_solid

    def test_compute_material_cost(self):
        """2.5 kg × ₹340/kg = ₹850.00."""
        cost = compute_material_cost(Decimal("2.5"), Decimal("340"))
        assert cost == Decimal("850.00")


# ────────────────────────────────────────────────────────────────────────
# Operation cost
# ────────────────────────────────────────────────────────────────────────

class TestOperationCost:
    """Tests for operation cost calculations."""

    def test_drilling_time(self):
        """Drilling time should be positive."""
        features = {"holes": [{"diameter_mm": 10, "count": 6}]}
        setup, cycle = compute_operation_time("Drilling", features)
        assert setup > 0
        assert cycle > 0

    def test_turning_time(self):
        """Turning time should depend on OD and length."""
        features = {"outer_diameter_mm": 120, "length_mm": 80}
        setup, cycle = compute_operation_time("Turning", features)
        assert setup == Decimal("0.25")
        assert cycle > 0

    def test_compute_operation_cost(self):
        """(0.25 + 0.50) hr × ₹1100/hr = ₹825.00."""
        cost = compute_operation_cost(
            Decimal("0.25"), Decimal("0.50"), Decimal("1100")
        )
        assert cost == Decimal("825.00")

    def test_unknown_operation_defaults(self):
        """Unknown operations return safe defaults."""
        setup, cycle = compute_operation_time("Laser Cutting", {})
        assert setup == Decimal("0.10")
        assert cycle == Decimal("0.20")


# ────────────────────────────────────────────────────────────────────────
# Pricing engine
# ────────────────────────────────────────────────────────────────────────

class TestPricingEngine:
    """Tests for pricing template application."""

    def test_percentage_overhead(self):
        """8% overhead on ₹2400 subtotal → ₹192."""
        lines = [{
            "name": "Commercial Overhead",
            "category": "overhead",
            "type": "percentage",
            "value": "8",
            "apply_on": "subtotal",
        }]
        result = apply_pricing_template(
            Decimal("2400"), Decimal("850"), Decimal("1550"),
            lines, quantity=100,
        )
        assert result["total_overheads"] == Decimal("192.00")

    def test_fixed_per_unit(self):
        """Fixed ₹50/unit packaging."""
        lines = [{
            "name": "Packaging",
            "category": "overhead",
            "type": "fixed_per_unit",
            "value": "50",
            "apply_on": "subtotal",
        }]
        result = apply_pricing_template(
            Decimal("2400"), Decimal("850"), Decimal("1550"),
            lines, quantity=100,
        )
        assert result["total_overheads"] == Decimal("50.00")

    def test_discount_reduces_net(self):
        """Discount should reduce net cost."""
        lines = [
            {
                "name": "Overhead",
                "category": "overhead",
                "type": "fixed_per_unit",
                "value": "100",
                "apply_on": "subtotal",
            },
            {
                "name": "Volume Discount",
                "category": "discount",
                "type": "percentage",
                "value": "5",
                "apply_on": "subtotal",
            },
        ]
        result = apply_pricing_template(
            Decimal("2000"), Decimal("800"), Decimal("1200"),
            lines, quantity=10,
        )
        # Net = 2000 + 100 - 100 = 2000
        assert result["net_cost_per_unit"] == Decimal("2000.00")
        assert result["total_cost"] == Decimal("20000.00")


# ────────────────────────────────────────────────────────────────────────
# Integration: Full pipeline
# ────────────────────────────────────────────────────────────────────────

class TestCostEstimatorIntegration:
    """Integration tests for the full estimation pipeline."""

    @pytest.fixture
    def estimator(self):
        return CostEstimator(SAMPLE_DATA_DIR)

    @pytest.fixture
    def mock_features(self):
        return {
            "outer_diameter_mm": 100,
            "inner_diameter_mm": 50,
            "length_mm": 60,
            "holes": [],
            "material_hint": "Stainless Steel",
        }

    def test_estimate_returns_required_keys(self, estimator, mock_features):
        """Result dictionary must contain all expected keys."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="bearing_ring",
            quantity=100,
            scrap_percent=5,
            effective_date="2026-03-09",
        )
        required_keys = [
            "material_cost", "operation_cost", "subtotal",
            "overheads", "discounts", "net_cost_per_unit", "total_cost",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_total_equals_net_times_quantity(self, estimator, mock_features):
        """Total cost should equal net cost per unit × quantity."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="spacer_v1",
            quantity=50,
            scrap_percent=3,
            effective_date="2026-03-09",
        )
        expected_total = round_currency(result["net_cost_per_unit"] * Decimal("50"))
        assert result["total_cost"] == expected_total

    def test_missing_material_raises(self, estimator, mock_features):
        """Unknown material hint should raise EstimationError."""
        features = mock_features.copy()
        features["material_hint"] = "Unobtainium"
        with pytest.raises(EstimationError, match="Material not found"):
            estimator.estimate(
                features=features,
                variant_name="test_unobtainium",
                quantity=1,
                effective_date="2026-03-09",
            )

    def test_costs_are_positive(self, estimator, mock_features):
        """All cost values should be positive."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="flange_adapter",
            quantity=200,
            scrap_percent=2,
            effective_date="2026-03-09",
            template_name="Export Pricing",
        )
        assert result["material_cost"] > 0
        assert result["operation_cost"] > 0
        assert result["subtotal"] > 0
        assert result["net_cost_per_unit"] > 0
        assert result["total_cost"] > 0

    # ── 5-Step Flow Tests ──────────────────────────────────────────────

    def test_frozen_snapshot_keys(self, estimator, mock_features):
        """Frozen estimation must include all snapshot dictionaries."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="spacer_v1",
            quantity=10,
            effective_date="2026-03-09",
        )
        # CostEstimation header
        assert "estimation_id" in result
        assert "status" in result
        assert result["status"] == "draft"
        assert "created_at" in result
        assert "family_name" in result

        # Frozen snapshots
        assert "material_snapshot" in result
        assert "operation_snapshots" in result
        assert "adjustment_snapshots" in result
        assert "summary" in result

        # Material snapshot keys
        ms = result["material_snapshot"]
        for k in ("material_name", "material_grade", "weight_per_unit_kg",
                   "rate_per_kg", "cost_per_unit"):
            assert k in ms, f"material_snapshot missing key: {k}"
        # material_name and material_grade must be separate strings
        assert isinstance(ms["material_name"], str)
        assert isinstance(ms["material_grade"], str)
        assert ms["material_name"] != ms["material_grade"]

        # Summary snapshot keys
        sm = result["summary"]
        for k in ("material_cost_per_unit", "operation_cost_per_unit",
                   "subtotal_per_unit", "overhead_per_unit", "discount_per_unit",
                   "net_cost_per_unit", "total_cost", "currency"):
            assert k in sm, f"summary missing key: {k}"

    def test_family_auto_detection(self, estimator, mock_features):
        """Variant should auto-detect its parent product family."""
        # Use a variant that exists in CSV (Spacer v1 - Standard)
        result = estimator.estimate(
            features=mock_features,
            variant_name="Spacer v1 - Standard",
            quantity=1,
            effective_date="2026-03-09",
        )
        # Family should be resolved (not N/A)
        assert result["family_name"] != "N/A"

    def test_explicit_family_selection(self, estimator, mock_features):
        """Explicit family_name parameter should be used."""
        families = estimator.loader.get_family_names()
        if not families:
            pytest.skip("No families in sample data")
        family = families[0]
        variants = estimator.loader.get_variants_for_family(
            estimator.loader.get_family_by_name(family)["id"]
        )
        if not variants:
            pytest.skip("No variants in first family")
        vname = variants[0]["name"]

        result = estimator.estimate(
            features=mock_features,
            variant_name=vname,
            quantity=1,
            effective_date="2026-03-09",
            family_name=family,
        )
        assert result["family_name"] == family

    def test_operation_snapshots_have_required_fields(self, estimator, mock_features):
        """Each operation snapshot must contain rate and time fields."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="spacer_v1",
            quantity=1,
            effective_date="2026-03-09",
        )
        for op in result["operation_snapshots"]:
            for k in ("operation_name", "operation_id", "work_center_name",
                       "work_center_id", "material_name", "material_id",
                       "setup_time_hrs", "cycle_time_hrs", "rate_per_hour",
                       "cost_per_unit"):
                assert k in op, f"operation_snapshot missing key: {k}"

    def test_adjustment_snapshots_have_sort_order(self, estimator, mock_features):
        """Each adjustment snapshot must include sort_order."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="spacer_v1",
            quantity=1,
            effective_date="2026-03-09",
        )
        for adj in result["adjustment_snapshots"]:
            assert "sort_order" in adj, "adjustment_snapshot missing sort_order"
            assert isinstance(adj["sort_order"], int)

    def test_estimation_report_record(self, estimator, mock_features):
        """Frozen snapshot must include an EstimationReport record."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="spacer_v1",
            quantity=1,
            effective_date="2026-03-09",
        )
        assert "report" in result
        rpt = result["report"]
        assert "format" in rpt
        assert rpt["format"] == "html"
        assert "generated_at" in rpt

    def test_rate_missing_flagged(self, estimator, mock_features):
        """Operations with no configured rate should be flagged, not skipped."""
        result = estimator.estimate(
            features=mock_features,
            variant_name="spacer_v1",
            quantity=1,
            effective_date="2026-03-09",
        )
        # All ops should be present (flagged or costed)
        op_names = [op["operation_name"] for op in result["operation_details"]]
        # At minimum the active operations should appear
        assert len(op_names) > 0
        # Any rate_missing op should have cost = 0
        for op in result["operation_details"]:
            if op.get("rate_missing"):
                assert op["cost_per_unit"] == Decimal("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
