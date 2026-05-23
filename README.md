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
hypersnap status          # quick operator summary
hypersnap doctor          # full checks with recommendations
hypersnap doctor --json   # machine-readable diagnostics
hypersnap doctor --fix    # safe repairs only; no data wipes
hypersnap logs            # recent node logs
hypersnap share           # sanitized support report
hypersnap install         # run upstream bootstrap/install flow
```

## Safety model

`hypersnap doctor --fix` may do low-risk fixes only:

- create missing config directories
- suggest package installs
- restart an unhealthy container if explicitly allowed
- generate sanitized reports

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
