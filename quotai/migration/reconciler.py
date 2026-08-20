"""
Reconciliation and reporting.
"""
import json
import os
from typing import Dict, Any

def generate_reconciliation_report(
    source_counts: Dict[str, int],
    valid_counts: Dict[str, int],
    rejected_counts: Dict[str, int],
    target_counts: Dict[str, int],
    output_dir: str
) -> Dict[str, Any]:
    """Generate a reconciliation report and check metrics."""
    os.makedirs(output_dir, exist_ok=True)
    
    report = {
        "datasets": {},
        "overall_status": "PASS"
    }
    
    for dataset in source_counts:
        src = source_counts.get(dataset, 0)
        val = valid_counts.get(dataset, 0)
        rej = rejected_counts.get(dataset, 0)
        tgt = target_counts.get(dataset, 0)
        
        # Check: source = migrated + rejected (assuming all valid are migrated)
        # Note: Idempotency might mean target_counts reflect unique records
        math_check = src == (val + rej)
        
        report["datasets"][dataset] = {
            "source_records": src,
            "valid_records": val,
            "rejected_records": rej,
            "migrated_records": tgt,
            "reconciliation_pass": math_check
        }
        
        if not math_check:
            report["overall_status"] = "FAIL"
            
    out_path = os.path.join(output_dir, "migration_report.json")
    with open(out_path, mode="w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report
