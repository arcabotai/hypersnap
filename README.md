# Hypersnap

Open-source operator toolkit for Hypersnap / Snapchain nodes.

This repo gives node operators two boring commands that should exist:

```bash
curl -fsSL https://hypersnap.org/install.sh | bash
hypersnap doctor
```

The goal is not to replace upstream Hypersnap. The goal is to make installation, diagnosis, safe repair, and support reports less painful.

## What is included

- `hypersnap` CLI: install/status/doctor/logs/share helpers for node operators.
- `install.sh`: one-line installer bootstrap.
- `site/`: static website intended for `hypersnap.org`.
- `tests/`: local CLI tests with no Docker dependency.

## Commands

```bash
hypersnap status                # quick operator summary
hypersnap doctor                # full checks with recommendations
hypersnap doctor --json         # machine-readable diagnostics
hypersnap doctor --fix          # safe repairs only; no data wipes
hypersnap logs                  # recent node logs
hypersnap share                 # sanitized JSON support report
hypersnap share --markdown      # sanitized Markdown support report
hypersnap install --preflight   # check host readiness before installing
hypersnap install --verify      # post-install verification
hypersnap install --print-command
hypersnap install --yes         # run upstream bootstrap after preflight
```

## Safety model

`hypersnap doctor --fix` may do low-risk fixes only:

- create a missing `HYPERSNAP_HOME` directory with restrictive permissions
- suggest package installs instead of performing them silently
- generate sanitized reports
- refuse destructive repairs by default

It will not delete node state, wipe configs, install packages, or restart containers without a future explicit command and operator intent.

It does **not** silently:

- delete chain data
- wipe snapshots
- expose Grafana publicly
- modify signer/custody keys
- open SSH to the world

Dangerous repairs should be explicit subcommands later, with warnings and backups.

## Upstream sources

- Hypersnap repo: <https://github.com/farcasterorg/hypersnap>
- Bootstrap script: <https://raw.githubusercontent.com/farcasterorg/hypersnap/refs/heads/main/scripts/hypersnap-bootstrap.sh>
- Mainnet compose: <https://raw.githubusercontent.com/farcasterorg/hypersnap/refs/heads/main/docker-compose.mainnet.yml>

## Development

```bash
python3 -m pytest -q
python3 -m hypersnap_cli doctor --json
python3 -m hypersnap_cli --help
```

For local executable testing:

```bash
./bin/hypersnap doctor
```

## Website

Static site lives in `site/`.

```bash
cd site
python3 -m http.server 8080
```

## License

MIT.
