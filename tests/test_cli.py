import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "hypersnap_cli", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def test_help():
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "Install, diagnose" in proc.stdout


def test_doctor_json_shape():
    proc = run_cli("doctor", "--json", "--no-logs")
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert data["tool"] == "hypersnap"
    assert data["overall"] in {"ok", "warn", "fail"}
    ids = {check["id"] for check in data["checks"]}
    assert {"host", "resources", "docker", "compose", "containers", "ports", "info_endpoint", "node_dir"} <= ids


def test_install_print_command():
    proc = run_cli("install", "--print-command")
    assert proc.returncode == 0
    assert "hypersnap-bootstrap.sh" in proc.stdout


def test_share_writes_redacted_report(tmp_path):
    out = tmp_path / "report.json"
    proc = run_cli("share", "--output", str(out))
    assert proc.returncode == 0
    data = json.loads(out.read_text())
    assert data["tool"] == "hypersnap"
    assert out.stat().st_mode & 0o077 == 0
