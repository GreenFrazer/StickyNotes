#!/usr/bin/env bash
# Build and install Sticky Notes to /Applications (macOS one-stop deploy).
#   bash packaging/macos/deploy.sh
#   bash packaging/macos/deploy.sh --build-only
#   bash packaging/macos/deploy.sh --install-only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_NAME="Sticky Notes.app"
INSTALL_DIR="/Applications"
BUILD_ONLY=false
INSTALL_ONLY=false

usage() {
  cat <<'EOF'
Usage: bash packaging/macos/deploy.sh [options]

Build Sticky Notes and install to /Applications/Sticky Notes.app

Options:
  --build-only    Build dist/Sticky Notes.app only (no install)
  --install-only  Install existing build to /Applications (no rebuild)
  -h, --help      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-only) BUILD_ONLY=true; shift ;;
    --install-only) INSTALL_ONLY=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "$BUILD_ONLY" == true && "$INSTALL_ONLY" == true ]]; then
  echo "Error: use either --build-only or --install-only, not both." >&2
  exit 1
fi

stop_app() {
  if pgrep -f "Contents/MacOS/Sticky Notes" >/dev/null 2>&1; then
    echo "Stopping running Sticky Notes..."
    pkill -f "Contents/MacOS/Sticky Notes" || true
    sleep 1
  fi
}

install_app() {
  local src="$ROOT/dist/$APP_NAME"
  local dest="$INSTALL_DIR/$APP_NAME"

  if [[ ! -d "$src" ]]; then
    echo "Error: build not found at $src" >&2
    echo "Run: bash packaging/macos/deploy.sh --build-only" >&2
    exit 1
  fi

  stop_app

  echo "Installing to $dest ..."
  rm -rf "$dest"
  ditto "$src" "$dest"

  echo ""
  echo "Deployed: $dest"
  echo "Launch: open -a \"Sticky Notes\""
  echo ""
  echo "Grant Accessibility for global shortcuts:"
  echo "  System Settings → Privacy & Security → Accessibility → Sticky Notes"
}

if [[ "$INSTALL_ONLY" != true ]]; then
  bash "$SCRIPT_DIR/build.sh"
fi

if [[ "$BUILD_ONLY" != true ]]; then
  install_app
fi
