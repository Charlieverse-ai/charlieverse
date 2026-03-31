#!/bin/sh
set -eu

main() {
echo "                                                   "
echo " ██████╗██╗  ██╗ █████╗ ██████╗ ██╗     ██╗███████╗"
echo "██╔════╝██║  ██║██╔══██╗██╔══██╗██║     ██║██╔════╝"
echo "██║     ███████║███████║██████╔╝██║     ██║█████╗  "
echo "██║     ██╔══██║██╔══██║██╔══██╗██║     ██║██╔══╝  "
echo "╚██████╗██║  ██║██║  ██║██║  ██║███████╗██║███████╗"
echo " ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝╚══════╝"
echo "                                                   "

  check_uv
  install_charlie
  run_init
  finish
}

check_uv() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi

  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Source the env so uv is available in this session
  if [ -f "$HOME/.local/bin/env" ]; then
    . "$HOME/.local/bin/env"
  elif [ -f "$HOME/.cargo/env" ]; then
    . "$HOME/.cargo/env"
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "✘ Failed to install uv. Install manually: https://docs.astral.sh/uv/"
    exit 1
  fi
}

install_charlie() {
  echo "Installing Charlieverse from PyPI..."
  uv tool install . -e

  echo "✔ Charlieverse installed"

  # Ensure uv tool bin is on PATH for this session
  UV_BIN="$HOME/.local/bin"
  case ":$PATH:" in
    *":$UV_BIN:"*) ;;
    *) export PATH="$UV_BIN:$PATH" ;;
  esac

  if ! command -v charlie >/dev/null 2>&1; then
    echo "⚠ charlie not found on PATH after install."
    echo "  Add this to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "  Then restart your terminal and run: charlie init"
    exit 1
  fi
}

run_init() {
  charlie init </dev/tty
}

finish() {
  echo ""
  echo "═══════════════════════════════════════"
  echo ""
  echo "  🐕 Charlie is ready."
  echo ""
  echo "═══════════════════════════════════════"
  echo ""
}

main
