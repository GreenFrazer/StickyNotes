#!/usr/bin/env bash
# Build Sticky Notes.app (macOS). Run from anywhere:
#   bash packaging/macos/build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"

python -m pip install --upgrade pip -q
python -m pip install -r requirements-macos.txt -q

rm -rf build dist
python packaging/macos/setup.py py2app
python packaging/macos/bundle_extras.py

echo "Built: $ROOT/dist/Sticky Notes.app"
