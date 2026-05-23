from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.request import urlopen

from . import __version__
from .checks import (
    build_report,
    collect_checks,
    diagnose,
    overall_status,
    report_to_markdown,
    redact,
    detect_node_dir,
    run,
    safe_fixes,
)

UPSTREAM_BOOTSTRAP = "https://raw.githubusercontent.com/farcasterorg/hypersnap/refs/heads/main/scripts/hypersnap-bootstrap.sh"


def print_human(checks):
    status_icon = {"ok": "✓", "warn": "!", "fail": "✗"}
    diag = diagnose(checks)
    print("Hypersnap Doctor")
    print(f"Overall: {overall_status(checks)}")
    print(f"Root cause: {diag['root_cause']}")
    print(f"Next action: {diag['recommended_next_action']}")
    for check in checks:
        print(f"\n{status_icon.get(check.status, '?')} {check.title}: {check.summary}")
        if check.recommendation:
            print(f"  Recommendation: {check.recommendation}")


def cmd_doctor(args):
    report = build_report(include_logs=not args.no_logs, version=__version__)
    checks = collect_checks(include_logs=not args.no_logs)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(checks)
    if args.fix:
        actions = safe_fixes(checks)
        print("\nSafe fixes:")
        for action in actions:
            print(f"- {action['id']}: {action['status']} — {action['summary']}")
        print("No destructive repairs were attempted. Package installs, container restarts, and data deletion require explicit manual action.")
    return 1 if report["overall"] == "fail" else 0


def cmd_status(args):
    checks = collect_checks(include_logs=False)
    summary = {c.id: c.status for c in checks}
    print(f"Hypersnap status: {overall_status(checks)}")
    print(f"Next: {diagnose(checks)['recommended_next_action']}")
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
    report = build_report(include_logs=True, version=__version__)
    suffix = "md" if args.markdown else "json"
    out_path = Path(args.output or f"hypersnap-report.{suffix}")
    if args.markdown:
        out_path.write_text(report_to_markdown(report), encoding="utf-8")
    else:
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(out_path, 0o600)
    print(f"Wrote sanitized report: {out_path}")
    print("Review it before posting publicly. It should redact obvious secrets, but humans remain annoyingly creative.")
    return 0


def _print_preflight(json_output: bool) -> int:
    report = build_report(include_logs=False, version=__version__)
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Hypersnap install preflight")
        print(f"Overall: {report['overall']}")
        print(f"Root cause: {report['diagnosis']['root_cause']}")
        print(f"Next action: {report['diagnosis']['recommended_next_action']}")
        for check in report["checks"]:
            if check["status"] != "ok":
                print(f"- {check['title']}: {check['status']} — {check['summary']}")
    return 1 if report["overall"] == "fail" else 0


def _print_verify(json_output: bool) -> int:
    report = build_report(include_logs=True, version=__version__)
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Hypersnap install verification")
        print(f"Overall: {report['overall']}")
        print(f"Root cause: {report['diagnosis']['root_cause']}")
        print(f"Next action: {report['diagnosis']['recommended_next_action']}")
    return 1 if report["overall"] == "fail" else 0


def cmd_install(args):
    if args.print_command:
        print(f"curl -fsSL {UPSTREAM_BOOTSTRAP} | bash")
        return 0
    if args.preflight:
        return _print_preflight(args.json)
    if args.verify:
        return _print_verify(args.json)
    if not args.skip_preflight:
        code = _print_preflight(False)
        if code != 0:
            print("\nPreflight failed. Fix the failing checks or rerun with --skip-preflight if you know what you are doing.")
            return code
    if not args.yes:
        print("This will run the upstream Hypersnap bootstrap script.")
        print(f"Source: {UPSTREAM_BOOTSTRAP}")
        print("Re-run with --yes to execute, --preflight to check the host, or --print-command to copy the command.")
        return 2
    with urlopen(UPSTREAM_BOOTSTRAP, timeout=20) as resp:
        script = resp.read()
    proc = subprocess.run(["bash"], input=script)
    if proc.returncode != 0:
        return proc.returncode
    print("\nRunning post-install verification...")
    return _print_verify(False)


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
    p.add_argument("--markdown", action="store_true", help="write a Markdown support report instead of JSON")
    p.set_defaults(func=cmd_share)

    p = sub.add_parser("install", help="preflight, verify, run, or print upstream bootstrap install")
    p.add_argument("--yes", action="store_true", help="execute upstream bootstrap")
    p.add_argument("--print-command", action="store_true", help="print bootstrap command only")
    p.add_argument("--preflight", action="store_true", help="check host readiness before installing")
    p.add_argument("--verify", action="store_true", help="run post-install verification checks")
    p.add_argument("--json", action="store_true", help="machine-readable output for --preflight/--verify")
    p.add_argument("--skip-preflight", action="store_true", help="skip readiness checks before --yes install")
    p.set_defaults(func=cmd_install)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
