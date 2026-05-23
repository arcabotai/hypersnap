from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from . import __version__
from .checks import collect_checks, overall_status, sanitize_report, redact, detect_node_dir, run

UPSTREAM_BOOTSTRAP = "https://raw.githubusercontent.com/farcasterorg/hypersnap/refs/heads/main/scripts/hypersnap-bootstrap.sh"


def print_human(checks):
    status_icon = {"ok": "✓", "warn": "!", "fail": "✗"}
    print("Hypersnap Doctor")
    print(f"Overall: {overall_status(checks)}")
    for check in checks:
        print(f"\n{status_icon.get(check.status, '?')} {check.title}: {check.summary}")
        if check.recommendation:
            print(f"  Recommendation: {check.recommendation}")


def cmd_doctor(args):
    checks = collect_checks(include_logs=not args.no_logs)
    report = {
        "tool": "hypersnap",
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall_status(checks),
        "checks": [c.to_dict() for c in checks],
    }
    report = sanitize_report(report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(checks)
    if args.fix:
        print("\n--fix is intentionally conservative in v0.1. No destructive repairs were attempted.")
        print("Safe repair commands will land as explicit subcommands after more node failure data is collected.")
    return 1 if report["overall"] == "fail" else 0


def cmd_status(args):
    checks = collect_checks(include_logs=False)
    summary = {c.id: c.status for c in checks}
    print(f"Hypersnap status: {overall_status(checks)}")
    for key in ["docker", "compose", "containers", "ports", "info_endpoint", "resources"]:
        if key in summary:
            print(f"- {key}: {summary[key]}")
    return 1 if overall_status(checks) == "fail" else 0


def cmd_logs(args):
    node_dir = detect_node_dir()
    cmd = ["docker", "compose", "logs", "--tail", str(args.tail)]
    code, out = run(cmd, timeout=30, cwd=node_dir)
    if code != 0:
        code, out = run(["docker", "logs", "--tail", str(args.tail), "hypersnap"], timeout=30)
    print(redact(out))
    return 0 if code == 0 else 1


def cmd_share(args):
    checks = collect_checks(include_logs=True)
    report = sanitize_report({
        "tool": "hypersnap",
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall_status(checks),
        "checks": [c.to_dict() for c in checks],
    })
    out_path = Path(args.output or f"hypersnap-report-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json")
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.chmod(out_path, 0o600)
    print(f"Wrote sanitized report: {out_path}")
    print("Review it before posting publicly. It should redact obvious secrets, but humans remain annoyingly creative.")
    return 0


def cmd_install(args):
    if args.print_command:
        print(f"curl -fsSL {UPSTREAM_BOOTSTRAP} | bash")
        return 0
    if not args.yes:
        print("This will run the upstream Hypersnap bootstrap script.")
        print(f"Source: {UPSTREAM_BOOTSTRAP}")
        print("Re-run with --yes to execute, or --print-command to copy the command.")
        return 2
    with urlopen(UPSTREAM_BOOTSTRAP, timeout=20) as resp:
        script = resp.read()
    proc = subprocess.run(["bash"], input=script)
    return proc.returncode


def build_parser():
    parser = argparse.ArgumentParser(prog="hypersnap", description="Install, diagnose, and support Hypersnap / Snapchain nodes.")
    parser.add_argument("--version", action="version", version=f"hypersnap {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="run diagnostics")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON")
    p.add_argument("--no-logs", action="store_true", help="skip log collection")
    p.add_argument("--fix", action="store_true", help="attempt safe fixes only")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("status", help="quick node status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("logs", help="print recent sanitized logs")
    p.add_argument("--tail", type=int, default=160)
    p.set_defaults(func=cmd_logs)

    p = sub.add_parser("share", help="write sanitized support report")
    p.add_argument("--output", "-o")
    p.set_defaults(func=cmd_share)

    p = sub.add_parser("install", help="run or print upstream bootstrap install")
    p.add_argument("--yes", action="store_true", help="execute upstream bootstrap")
    p.add_argument("--print-command", action="store_true", help="print bootstrap command only")
    p.set_defaults(func=cmd_install)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
