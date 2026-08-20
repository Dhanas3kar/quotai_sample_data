import pytest
from quotai.pipeline.orchestrator import MigrationOrchestrator

def test_idempotency(tmp_path):
    source_dir = "sample_data/legacy" # Assuming running from project root
    target_dir = str(tmp_path / "migrated")
    
    orch = MigrationOrchestrator(source_dir, target_dir)
    src_c, val_c, rej, tgt_c = orch.run_migration()
    
    # Run a second time
    src_c2, val_c2, rej2, tgt_c2 = orch.run_migration()
    
    # Because of idempotency, the second run should produce 0 target records
    assert tgt_c2["legacy_material"] == 0
    assert tgt_c2["legacy_material_rate"] == 0
