"""
Orchestrator to glue validation, transformation, normalization, and output.
Handles reading legacy data, applying the pipeline, enforcing idempotency,
and generating outputs for reconciliation.
"""
import csv
import logging
import os
from typing import List, Dict, Any, Tuple

from ..validation.schema_validator import validate_legacy_material, validate_legacy_material_rate
from ..validation.referential_checks import check_material_references
from .transformer import transform_material, transform_material_rate

logger = logging.getLogger(__name__)

class MigrationOrchestrator:
    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir
        
        # Idempotency tracking (mock versioning/IDs)
        # In a real system, you'd check existing DB records.
        # Here we just track what we've written this run to avoid duplicates if source has them.
        self.migrated_material_ids = set()
        self.migrated_rate_ids = set()

    def _read_csv(self, filename: str) -> List[Dict]:
        path = os.path.join(self.source_dir, filename)
        if not os.path.isfile(path):
            return []
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
            
    def _write_csv(self, filename: str, rows: List[Dict], fieldnames: List[str]):
        if not rows:
            return
        os.makedirs(self.target_dir, exist_ok=True)
        path = os.path.join(self.target_dir, filename)
        with open(path, mode="w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def run_migration(self) -> Tuple[Dict[str, int], Dict[str, int], List[Dict], Dict[str, int]]:
        """
        Executes the migration pipeline.
        Returns counts for source, valid, target, and the list of rejected records.
        """
        logger.info("Starting migration pipeline...")
        
        source_counts = {"legacy_material": 0, "legacy_material_rate": 0}
        valid_counts = {"legacy_material": 0, "legacy_material_rate": 0}
        target_counts = {"legacy_material": 0, "legacy_material_rate": 0}
        all_rejected = []
        
        # 1. Read legacy data
        materials_src = self._read_csv("legacy_material.csv")
        rates_src = self._read_csv("legacy_material_rate.csv")
        
        source_counts["legacy_material"] = len(materials_src)
        source_counts["legacy_material_rate"] = len(rates_src)
        
        # 2. Process Materials
        valid_materials_raw = []
        target_materials = []
        
        # Validation & Transformation
        for idx, row in enumerate(materials_src):
            val_res = validate_legacy_material(row, idx)
            if val_res.is_valid:
                valid_materials_raw.append(row)
                valid_counts["legacy_material"] += 1
                
                # Transform
                transformed = transform_material(row)
                
                # Idempotency Check
                if transformed["id"] not in self.migrated_material_ids:
                    target_materials.append(transformed)
                    self.migrated_material_ids.add(transformed["id"])
            else:
                all_rejected.append({
                    "record_id": val_res.record_id,
                    "dataset": val_res.dataset,
                    "error_type": val_res.error_type,
                    "error_message": val_res.message,
                    "raw_data": str(row)
                })

        # 3. Process Material Rates (with referential integrity)
        valid_rates_raw = []
        target_rates = []
        
        # Referential integrity uses valid material codes
        valid_mat_codes = {row.get("mat_code") for row in valid_materials_raw if row.get("mat_code")}
        ref_results = check_material_references(rates_src, valid_mat_codes)
        
        # Mapping legacy code to target UUID for rate transformation
        # We need this map regardless of whether materials were skipped by idempotency
        mat_uuid_map = {}
        for row in valid_materials_raw:
            transformed_mat = transform_material(row)
            mat_uuid_map[row["mat_code"]] = transformed_mat["id"]
        
        for idx, (row, ref_res) in enumerate(zip(rates_src, ref_results)):
            # Check structure first
            val_res = validate_legacy_material_rate(row, idx)
            if not val_res.is_valid:
                all_rejected.append({
                    "record_id": val_res.record_id,
                    "dataset": val_res.dataset,
                    "error_type": val_res.error_type,
                    "error_message": val_res.message,
                    "raw_data": str(row)
                })
                continue
                
            # Check referential integrity
            if not ref_res.is_valid:
                all_rejected.append({
                    "record_id": ref_res.record_id,
                    "dataset": ref_res.dataset,
                    "error_type": ref_res.error_type,
                    "error_message": ref_res.message,
                    "raw_data": str(row)
                })
                continue
                
            valid_rates_raw.append(row)
            valid_counts["legacy_material_rate"] += 1
            
            # Transform
            transformed = transform_material_rate(row, mat_uuid_map)
            
            # Idempotency Check (composite key: material_id + effective_from)
            idem_key = f"{transformed['material_id']}_{transformed['effective_from']}"
            if idem_key not in self.migrated_rate_ids:
                target_rates.append(transformed)
                self.migrated_rate_ids.add(idem_key)
                
        # 4. Output Target Data
        if target_materials:
            self._write_csv("material.csv", target_materials, list(target_materials[0].keys()))
            target_counts["legacy_material"] = len(target_materials)
            
        if target_rates:
            self._write_csv("material_rate.csv", target_rates, list(target_rates[0].keys()))
            target_counts["legacy_material_rate"] = len(target_rates)
            
        logger.info(f"Migration finished. Migrated {len(target_materials)} materials, {len(target_rates)} rates.")
        return source_counts, valid_counts, all_rejected, target_counts
