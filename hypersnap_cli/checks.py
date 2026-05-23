from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

PORTS = [
    (3381, "tcp", "RPC / API"),
    (3382, "udp", "gossip"),
    (3383, "tcp", "peer / sync"),
]
DEFAULT_NODE_DIRS = [Path.home() / "hypersnap", Path("/opt/hypersnap"), Path("/var/lib/hypersnap")]
SECRET_PATTERNS = [
    re.compile(r"(?i)(token|secret|password|private[_-]?key|api[_-]?key)\s*[:=]\s*([^\s]+)"),
    re.compile(r"gh[opsu]_[A-Za-z0-9_]+"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
]

@dataclass
class CheckResult:
    id: str
    title: str
    status: str
    summary: str
    details: dict[str, Any]
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run(cmd: list[str], timeout: int = 8, cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, cwd=str(cwd) if cwd else None)
        return proc.returncode, proc.stdout.strip()
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        return 124, (out + "\nTIMEOUT").strip()


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 2:
            redacted = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def detect_node_dir() -> Path | None:
    env_dir = os.environ.get("HYPERSNAP_HOME")
    candidates = ([Path(env_dir)] if env_dir else []) + DEFAULT_NODE_DIRS
    for path in candidates:
        if (path / "docker-compose.yml").exists() or (path / "docker-compose.mainnet.yml").exists() or (path / "config.toml").exists():
            return path
    return None


def check_host() -> CheckResult:
    _, uname = run(["uname", "-a"])
    _, hostname = run(["hostname"])
    _, uptime = run(["uptime", "-p"])
    return CheckResult("host", "Host", "ok", f"{hostname or 'unknown host'}", {"uname": uname, "uptime": uptime})


def check_resources() -> CheckResult:
    _, disk = run(["df", "-h", "/"])
    _, mem = run(["free", "-h"])
    status = "ok"
    rec = None
    pct = None
    try:
        lines = disk.splitlines()
        pct = int(lines[1].split()[4].rstrip("%")) if len(lines) > 1 else None
        if pct is not None and pct >= 95:
            status = "fail"
            rec = "Disk is critically full. Expand the volume or clean safe logs before restarting the node."
        elif pct is not None and pct >= 85:
            status = "warn"
            rec = "Disk is getting tight. Hypersnap state can grow; plan a volume expansion."
    except Exception:
        status = "warn"
        rec = "Could not parse disk usage. Check df output manually."
    return CheckResult("resources", "Resources", status, f"root disk {pct}% used" if pct is not None else "resource check complete", {"disk": disk, "memory": mem}, rec)


def check_docker() -> CheckResult:
    docker = shutil.which("docker")
    if not docker:
        return CheckResult("docker", "Docker", "fail", "Docker is not installed", {}, "Install Docker before running a Hypersnap node.")
    code, version = run([docker, "--version"])
    code2, info = run([docker, "info", "--format", "{{.ServerVersion}}"], timeout=10)
    status = "ok" if code == 0 and code2 == 0 else "fail"
    rec = None if status == "ok" else "Docker exists but the daemon is not reachable. Start Docker and check permissions."
    return CheckResult("docker", "Docker", status, "Docker daemon reachable" if status == "ok" else "Docker daemon not reachable", {"version": version, "server": info}, rec)


def check_compose() -> CheckResult:
    code, out = run(["docker", "compose", "version"])
    if code == 0:
        return CheckResult("compose", "Docker Compose", "ok", "docker compose available", {"version": out})
    legacy = shutil.which("docker-compose")
    if legacy:
        code2, out2 = run([legacy, "--version"])
        return CheckResult("compose", "Docker Compose", "warn", "legacy docker-compose available", {"version": out2}, "Prefer Docker Compose v2: docker compose ...")
    return CheckResult("compose", "Docker Compose", "fail", "Docker Compose not found", {"error": out}, "Install Docker Compose v2.")


def check_containers() -> CheckResult:
    code, out = run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"], timeout=10)
    if code != 0:
        return CheckResult("containers", "Containers", "warn", "Could not inspect containers", {"output": out}, "Fix Docker before checking Hypersnap containers.")
    rows = [line for line in out.splitlines() if line.strip()]
    hypersnap_rows = [r for r in rows if "hypersnap" in r.lower() or "snapchain" in r.lower()]
    if not hypersnap_rows:
        return CheckResult("containers", "Containers", "warn", "No Hypersnap/Snapchain containers found", {"containers": rows}, "Run the installer or start the compose stack from your node directory.")
    bad = [r for r in hypersnap_rows if any(word in r.lower() for word in ["exited", "restarting", "dead"])]
    status = "fail" if bad else "ok"
    rec = "Check recent logs with `hypersnap logs`." if bad else None
    return CheckResult("containers", "Containers", status, f"{len(hypersnap_rows)} Hypersnap/Snapchain container(s) found", {"containers": hypersnap_rows}, rec)


def check_ports() -> CheckResult:
    code, out = run(["ss", "-tulpen"], timeout=8)
    found = {}
    for port, proto, name in PORTS:
        found[str(port)] = bool(re.search(rf":{port}\b", out))
    missing = [p for p, ok in found.items() if not ok]
    if code != 0:
        return CheckResult("ports", "Ports", "warn", "Could not inspect listening ports", {"output": out}, "Install iproute2 or check ports manually.")
    status = "ok" if not missing else "warn"
    rec = None if not missing else f"Missing listeners for: {', '.join(missing)}. Check compose ports and cloud firewall rules."
    return CheckResult("ports", "Ports", status, "required ports appear to be listening" if not missing else "some expected ports are not listening", {"expected": PORTS, "listening": found}, rec)


def check_info_endpoint() -> CheckResult:
    try:
        req = Request("http://127.0.0.1:3381/v1/info", headers={"User-Agent": "hypersnap-doctor/0.1"})
        with urlopen(req, timeout=5) as resp:
            body = resp.read(20000).decode(errors="replace")
        parsed = None
        try:
            parsed = json.loads(body)
        except Exception:
            pass
        return CheckResult("info_endpoint", "Info endpoint", "ok", "local /v1/info responded", {"body": parsed if parsed is not None else body[:2000]})
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        return CheckResult("info_endpoint", "Info endpoint", "warn", "local /v1/info did not respond", {"error": str(exc)}, "If the node is running, check whether RPC is bound to 127.0.0.1:3381 or exposed under a different port.")


def check_logs(node_dir: Path | None) -> CheckResult:
    cmd = ["docker", "compose", "logs", "--tail", "80"]
    code, out = run(cmd, timeout=15, cwd=node_dir)
    if code != 0:
        code, out = run(["docker", "logs", "--tail", "80", "hypersnap"], timeout=15)
    text = redact(out)
    scary = [line for line in text.splitlines() if re.search(r"(?i)panic|fatal|error|no space|connection refused|permission denied", line)]
    status = "warn" if scary else "ok"
    return CheckResult("logs", "Recent logs", status, f"{len(scary)} suspicious log line(s) found", {"suspicious": scary[-20:], "tail": text[-5000:]}, "Run `hypersnap logs` for a fuller view." if scary else None)


def collect_checks(include_logs: bool = True) -> list[CheckResult]:
    node_dir = detect_node_dir()
    checks = [check_host(), check_resources(), check_docker(), check_compose(), check_containers(), check_ports(), check_info_endpoint()]
    checks.append(CheckResult("node_dir", "Node directory", "ok" if node_dir else "warn", str(node_dir) if node_dir else "No node directory detected", {"detected": str(node_dir) if node_dir else None}, None if node_dir else "Set HYPERSNAP_HOME or run from the node directory."))
    if include_logs:
        checks.append(check_logs(node_dir))
    return checks


def overall_status(checks: list[CheckResult]) -> str:
    statuses = [c.status for c in checks]
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "ok"


def sanitize_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, ensure_ascii=False, default=str)
    return json.loads(redact(text))
