"""
Isolate and store rejected records.
"""
import csv
import os
from typing import List, Dict

def write_rejected_records(rejected: List[Dict], output_dir: str):
    """Write rejected records to quarantine CSV."""
    if not rejected:
        return
        
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "rejected_records.csv")
    
    # We append or write new depending on idempotency/run strategy.
    # For now, we will overwrite for the current migration run.
    fieldnames = ["record_id", "dataset", "error_type", "error_message", "raw_data"]
    
    with open(out_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rejected:
            writer.writerow(r)
