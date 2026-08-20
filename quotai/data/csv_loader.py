"""
CSV data loader for QuotAI sample data.

Reads all CSV reference files from the sample_data/ directory and provides
convenient lookup functions used by the estimation engine.
"""

import csv
import json
import os
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional


class CSVDataLoader:
    """Loads and indexes all CSV reference data for the estimation pipeline."""

    def __init__(self, data_dir: str) -> None:
        """
        Parameters
        ----------
        data_dir : str
            Path to the directory containing sample CSV files.

        Raises
        ------
        FileNotFoundError
            If *data_dir* does not exist.
        """
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        self.data_dir = data_dir

        # Core reference tables
        self.materials: List[Dict] = []
        self.material_rates: List[Dict] = []
        self.operations: List[Dict] = []
        self.work_centers: List[Dict] = []
        self.work_center_rates: List[Dict] = []
        self.product_families: List[Dict] = []
        self.product_variants: List[Dict] = []
        self.pricing_templates: List[Dict] = []
        self.template_line_items: List[Dict] = []
        self.organizations: List[Dict] = []
        # Frozen estimation snapshots
        self.cost_estimations: List[Dict] = []
        self.estimation_material_costs: List[Dict] = []
        self.estimation_operation_costs: List[Dict] = []
        self.estimation_adjustments: List[Dict] = []
        self.estimation_summaries: List[Dict] = []
        self.estimation_reports: List[Dict] = []

        self._load_all()

    # ------------------------------------------------------------------
    # Internal loading
    # ------------------------------------------------------------------

    def _read_csv(self, filename: str) -> List[Dict]:
        """Read a single CSV file and return a list of row dicts."""
        path = os.path.join(self.data_dir, filename)
        if not os.path.isfile(path):
            return []
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _load_all(self) -> None:
        """Load every known CSV into memory."""
        self.organizations = self._read_csv("organization.csv")
        self.materials = self._read_csv("material.csv")
        self.material_rates = self._read_csv("material_rate.csv")
        self.operations = self._read_csv("operation.csv")
        self.work_centers = self._read_csv("work_center.csv")
        self.work_center_rates = self._read_csv("work_center_rate.csv")
        self.product_families = self._read_csv("product_family.csv")
        self.product_variants = self._read_csv("product_variant.csv")
        self.pricing_templates = self._read_csv("pricing_template.csv")
        self.template_line_items = self._read_csv("template_line_item.csv")
        # Frozen estimation snapshots
        self.cost_estimations = self._read_csv("cost_estimation.csv")
        self.estimation_material_costs = self._read_csv("estimation_material_cost.csv")
        self.estimation_operation_costs = self._read_csv("estimation_operation_cost.csv")
        self.estimation_adjustments = self._read_csv("estimation_adjustment.csv")
        self.estimation_summaries = self._read_csv("estimation_summary.csv")
        self.estimation_reports = self._read_csv("estimation_report.csv")

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_variant_by_name(self, name: str) -> Optional[Dict]:
        """Find a product variant by (case-insensitive) name substring."""
        name_lower = name.lower()
        for v in self.product_variants:
            if name_lower in v["name"].lower():
                return v
        return None

    def get_variant_names(self) -> List[str]:
        """Return a list of all variant names."""
        return [v["name"] for v in self.product_variants]

    def get_material_by_name(self, name: str) -> Optional[Dict]:
        """
        Find a material by name or grade (case-insensitive substring).

        Also handles common abbreviations like "SS 316" → "Stainless Steel" grade "316".
        """
        name_lower = name.lower().strip()

        # Direct name match
        for m in self.materials:
            if name_lower in m["name"].lower():
                return m

        # Match against grade (e.g. "316" in "SS 316")
        for m in self.materials:
            if m["grade"].lower() in name_lower:
                return m

        # Common abbreviation mapping
        _ALIASES = {
            "ss": "stainless steel",
            "ms": "mild steel",
            "al": "aluminum",
        }
        for abbr, full_name in _ALIASES.items():
            if name_lower.startswith(abbr + " ") or name_lower == abbr:
                for m in self.materials:
                    if full_name in m["name"].lower():
                        return m

        return None

    def get_material_by_id(self, material_id: str) -> Optional[Dict]:
        """Find a material by its UUID."""
        for m in self.materials:
            if m["id"] == material_id:
                return m
        return None

    def get_material_rate(self, material_id: str,
                          effective_date: date) -> Optional[Decimal]:
        """
        Look up the latest material rate (₹/kg) effective on or before
        *effective_date* for the given material.
        """
        best_rate: Optional[Decimal] = None
        best_date: Optional[date] = None

        for r in self.material_rates:
            if r["material_id"] != material_id:
                continue
            eff = date.fromisoformat(r["effective_from"])
            if eff <= effective_date:
                if best_date is None or eff > best_date:
                    best_date = eff
                    best_rate = Decimal(r["rate_per_kg"])

        return best_rate

    def get_work_center_rate(self, operation_id: str,
                             material_id: Optional[str] = None) -> Optional[Dict]:
        """
        Find the work-center rate for an operation.

        Priority:
        1. Exact match on (operation_id, material_id)
        2. Fallback to (operation_id, material_id=NULL/empty)
        """
        fallback: Optional[Dict] = None

        for r in self.work_center_rates:
            if r["operation_id"] != operation_id:
                continue
            mat = r.get("material_id", "").strip()
            if material_id and mat == material_id:
                return r  # exact match
            if not mat:
                fallback = r

        return fallback

    def get_pricing_template_by_name(self, name: str) -> Optional[Dict]:
        """Find a pricing template by name (case-insensitive substring)."""
        name_lower = name.lower()
        for t in self.pricing_templates:
            if name_lower in t["name"].lower():
                return t
        return None

    def get_template_names(self) -> List[str]:
        """Return a list of all pricing template names."""
        return [t["name"] for t in self.pricing_templates]

    def get_template_line_items(self, template_id: str) -> List[Dict]:
        """Return sorted line items for a pricing template."""
        items = [
            li for li in self.template_line_items
            if li["template_id"] == template_id
        ]
        items.sort(key=lambda x: int(x.get("sort_order", 0)))
        return items

    def get_operations_list(self) -> List[Dict]:
        """Return all active operations."""
        return [op for op in self.operations if op.get("is_active") == "true"]

    # ------------------------------------------------------------------
    # Product family lookups
    # ------------------------------------------------------------------

    def get_family_names(self) -> List[str]:
        """Return a list of all product family names."""
        return [f["name"] for f in self.product_families]

    def get_family_by_name(self, name: str) -> Optional[Dict]:
        """Find a product family by name (case-insensitive substring)."""
        name_lower = name.lower()
        for f in self.product_families:
            if name_lower in f["name"].lower():
                return f
        return None

    def get_family_by_id(self, family_id: str) -> Optional[Dict]:
        """Find a product family by its UUID."""
        for f in self.product_families:
            if f["id"] == family_id:
                return f
        return None

    def get_variants_for_family(self, family_id: str) -> List[Dict]:
        """Return all variants belonging to a product family."""
        return [v for v in self.product_variants if v["family_id"] == family_id]

    def get_family_for_variant(self, variant_id: str) -> Optional[Dict]:
        """Look up the parent product family for a variant."""
        for v in self.product_variants:
            if v["id"] == variant_id:
                return self.get_family_by_id(v["family_id"])
        return None

    def get_family_ref_extraction(self, family_id: str) -> Optional[Dict]:
        """
        Return the reference drawing extraction data for a family.

        This is the AI-extracted baseline from the family's reference drawing.
        """
        family = self.get_family_by_id(family_id)
        if family and family.get("ref_extraction_data"):
            return json.loads(family["ref_extraction_data"])
        return None

    # ------------------------------------------------------------------
    # Work-center helpers
    # ------------------------------------------------------------------

    def get_work_center_by_id(self, wc_id: str) -> Optional[Dict]:
        """Find a work center by its UUID."""
        for wc in self.work_centers:
            if wc["id"] == wc_id:
                return wc
        return None
