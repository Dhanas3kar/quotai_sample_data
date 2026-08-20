import pytest
import subprocess

def test_cli_help():
    result = subprocess.run(["python", "-m", "quotai", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "migrate" in result.stdout

def test_cli_migrate(tmp_path):
    target = tmp_path / "migrated"
    report = tmp_path / "reports" / "migration_report.json"
    
    result = subprocess.run([
        "python", "-m", "quotai", "migrate",
        "--source", "sample_data/legacy",
        "--target", str(target),
        "--report", str(report)
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    assert report.exists()
