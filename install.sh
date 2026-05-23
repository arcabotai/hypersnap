#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${HYPERSNAP_REPO_URL:-https://github.com/arcabotai/hypersnap.git}"
INSTALL_DIR="${HYPERSNAP_INSTALL_DIR:-$HOME/.hypersnap-toolkit}"
BIN_DIR="${HYPERSNAP_BIN_DIR:-/usr/local/bin}"

need() { command -v "$1" >/dev/null 2>&1; }

if ! need git; then
  echo "git is required. Install git, then re-run this installer." >&2
  exit 1
fi
if ! need python3; then
  echo "python3 is required. Install Python 3.10+, then re-run this installer." >&2
  exit 1
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  rm -rf "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

chmod +x "$INSTALL_DIR/bin/hypersnap"

if [ -w "$BIN_DIR" ]; then
  ln -sf "$INSTALL_DIR/bin/hypersnap" "$BIN_DIR/hypersnap"
else
  echo "Need write access to $BIN_DIR. Trying sudo..."
  sudo ln -sf "$INSTALL_DIR/bin/hypersnap" "$BIN_DIR/hypersnap"
fi

echo "Installed: $(command -v hypersnap || echo "$BIN_DIR/hypersnap")"
hypersnap --version
printf '\nNext:\n  hypersnap doctor\n  hypersnap install --print-command\n'
