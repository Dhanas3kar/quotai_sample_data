"""
Command-line interface for QuotAI engineering workflows.
"""
import argparse
import logging
from .utils.logging_config import setup_logging
from .pipeline.orchestrator import MigrationOrchestrator
from .migration.quarantine import write_rejected_records
from .migration.reconciler import generate_reconciliation_report

logger = logging.getLogger(__name__)

import os

def handle_migrate(args):
    """Run the migration pipeline."""
    logger.info(f"Migration started. Source: {args.source}, Target: {args.target}")
    
    orchestrator = MigrationOrchestrator(args.source, args.target)
    src_counts, val_counts, rejected, tgt_counts = orchestrator.run_migration()
    
    # Write quarantine
    reports_dir = os.path.dirname(args.report)
    base_output_dir = os.path.dirname(reports_dir)
    rejected_dir = os.path.join(base_output_dir, "rejected")
    write_rejected_records(rejected, rejected_dir)
    logger.info(f"Wrote {len(rejected)} rejected records to {rejected_dir}")
    
    # Write reconciliation report
    report = generate_reconciliation_report(src_counts, val_counts, {"legacy_material": len([r for r in rejected if r["dataset"] == "legacy_material"]), "legacy_material_rate": len([r for r in rejected if r["dataset"] == "legacy_material_rate"])}, tgt_counts, reports_dir)
    
    status = report.get("overall_status")
    if status == "PASS":
        logger.info(f"Migration completed successfully. Reconciliation: {status}")
    else:
        logger.error(f"Migration completed with reconciliation failures. Reconciliation: {status}")

def handle_validate(args):
    """Run validation only (mock logic for demo)."""
    logger.info(f"Validation mode not fully standalone yet. Use migrate command.")

def handle_report(args):
    """Generate a report from an existing migration."""
    logger.info(f"Report mode not fully standalone yet. Use migrate command.")

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="QuotAI Data Processing & Migration Simulation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run the data migration pipeline")
    migrate_parser.add_argument("--source", required=True, help="Path to source legacy data directory")
    migrate_parser.add_argument("--target", required=True, help="Path to output migrated data directory")
    migrate_parser.add_argument("--report", required=True, help="Path to output migration report JSON file")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate source data (No transformation)")
    validate_parser.add_argument("--source", required=True, help="Path to source legacy data directory")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate reports for data")
    
    args = parser.parse_args()
    
    if args.command == "migrate":
        handle_migrate(args)
    elif args.command == "validate":
        handle_validate(args)
    elif args.command == "report":
        handle_report(args)

if __name__ == "__main__":
    main()
