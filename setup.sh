#!/bin/bash
#
# Charlieverse Setup — from zero to running Charlie.
#
# Usage:
#   ./setup.sh           Interactive setup
#   ./setup.sh --help    Show help
#

set -euo pipefail

CHARLIE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHARLIE_CLI="$CHARLIE_DIR/bin/charlie"

# ── Colors ────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

info()  { echo -e "${BLUE}▸${RESET} $1"; }
ok()    { echo -e "${GREEN}✔${RESET} $1"; }
warn()  { echo -e "${YELLOW}⚠${RESET} $1"; }
fail()  { echo -e "${RED}✘${RESET} $1"; }
step()  { echo -e "\n${BOLD}$1${RESET}"; }

# ── Helpers ───────────────────────────────────────────────

ask_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local hint="[Y/n]"
    [[ "$default" == "n" ]] && hint="[y/N]"

    read -rp "$(echo -e "${BLUE}?${RESET} ${prompt} ${DIM}${hint}${RESET} ")" answer
    answer="${answer:-$default}"
    [[ "$answer" =~ ^[Yy] ]]
}

ask_choice() {
    local prompt="$1"
    shift
    local options=("$@")

    echo -e "${BLUE}?${RESET} ${prompt}"
    for i in "${!options[@]}"; do
        echo -e "  ${BOLD}$((i+1))${RESET}) ${options[$i]}"
    done

    while true; do
        read -rp "$(echo -e "  ${DIM}Enter number:${RESET} ")" choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
            return $((choice - 1))
        fi
        echo -e "  ${RED}Invalid choice${RESET}"
    done
}

check_command() {
    command -v "$1" &>/dev/null
}

# ── Preflight ─────────────────────────────────────────────

preflight() {
    step "🔍 Checking prerequisites"

    local missing=()

    # Python 3.12+
    if check_command python3; then
        local pyver
        pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
            ok "Python $pyver"
        else
            fail "Python $pyver (need 3.12+)"
            missing+=("python3.12+")
        fi
    else
        fail "Python not found"
        missing+=("python3.12+")
    fi

    # uv
    if check_command uv; then
        ok "uv $(uv --version 2>/dev/null | head -1)"
    else
        fail "uv not found"
        missing+=("uv")
    fi

    # jq
    if check_command jq; then
        ok "jq"
    else
        fail "jq not found"
        missing+=("jq")
    fi

    # Node/npm (optional)
    if check_command npm; then
        ok "npm $(npm --version 2>/dev/null)"
    else
        warn "npm not found — web dashboard won't be built (optional)"
    fi

    # git
    if check_command git; then
        ok "git"
    else
        fail "git not found"
        missing+=("git")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        fail "Missing required tools: ${missing[*]}"
        echo ""
        echo "Install them first:"
        for tool in "${missing[@]}"; do
            case "$tool" in
                python3.12+) echo "  brew install python@3.12" ;;
                uv)          echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
                jq)          echo "  brew install jq" ;;
                git)         echo "  brew install git" ;;
            esac
        done
        exit 1
    fi
}

# ── Install Dependencies ─────────────────────────────────

install_deps() {
    step "📦 Installing Python dependencies"
    info "Running uv sync..."
    (cd "$CHARLIE_DIR" && uv sync --quiet)
    ok "Python dependencies installed"
}

# ── Initialize ────────────────────────────────────────────

initialize() {
    step "🏗️  Initializing Charlieverse"
    (cd "$CHARLIE_DIR" && uv run python -m charlieverse.cli init)
}

# ── Start Server ──────────────────────────────────────────

start_server() {
    step "🚀 Starting Charlie server"

    # Check if already running
    if $CHARLIE_CLI server status &>/dev/null; then
        ok "Server already running"
        return
    fi

    $CHARLIE_CLI server start
    sleep 1

    if $CHARLIE_CLI server status &>/dev/null; then
        ok "Server started at $($CHARLIE_CLI server url)"
    else
        fail "Server failed to start — check ~/.charlieverse/logs/charlie.log"
        exit 1
    fi
}

# ── Install CLI ───────────────────────────────────────────

install_cli() {
    step "🔗 Installing charlie CLI"

    local target="/usr/local/bin"
    local scripts=("charlie" "charlie-commit" "charlie-claude")

    # Check if already installed and pointing to our bin
    if [[ -L "$target/charlie" ]] && [[ "$(readlink "$target/charlie")" == "$CHARLIE_DIR/bin/charlie" ]]; then
        ok "charlie CLI already installed"
        return
    fi

    if ask_yes_no "Symlink 'charlie' to /usr/local/bin?"; then
        for script in "${scripts[@]}"; do
            local src="$CHARLIE_DIR/bin/$script"
            local dest="$target/$script"
            [[ ! -f "$src" ]] && continue

            if [[ -L "$dest" || -f "$dest" ]]; then
                sudo rm -f "$dest"
            fi
            sudo ln -s "$src" "$dest"
            info "$script → $dest"
        done
        ok "charlie CLI installed"
    else
        info "Skipped — you can run charlie from: $CHARLIE_CLI"
    fi
}

# ── Provider Setup ────────────────────────────────────────

setup_provider() {
    step "🔌 Provider Integration"
    echo ""
    info "Which AI coding tool(s) do you use with Charlie?"
    echo ""

    local providers=()

    if ask_yes_no "Set up Claude Code?"; then
        providers+=("claude")
    fi

    if ask_yes_no "Set up GitHub Copilot?"; then
        providers+=("copilot")
    fi

    if [[ ${#providers[@]} -eq 0 ]]; then
        warn "No providers selected — you can run these later:"
        echo "  ./integrations/claude/install.sh"
        echo "  ./integrations/copilot/install.sh"
        return
    fi

    for provider in "${providers[@]}"; do
        echo ""
        info "Setting up ${provider}..."
        local script="$CHARLIE_DIR/integrations/$provider/install.sh"

        if [[ ! -x "$script" ]]; then
            chmod +x "$script"
        fi

        if bash "$script"; then
            ok "${provider} integration complete"
        else
            fail "${provider} integration failed"
        fi
    done
}

# ── Import History ────────────────────────────────────────

import_history() {
    step "📜 Import Conversation History"
    echo ""
    info "Charlie can import your existing conversation history from"
    info "AI coding tools so he already knows you on day one."
    echo ""
    info "Supported: Claude, GitHub Copilot (+ Insiders), Cursor, Codex"
    info "Auto-discovers local session files — nothing to configure."
    echo ""

    local import_dir="$HOME/.charlieverse/import"
    local existing_jsonl="$import_dir/conversations.jsonl"

    # Auto-detect existing JSONL from a previous extraction
    if [[ -f "$existing_jsonl" ]] && [[ -s "$existing_jsonl" ]]; then
        local line_count
        line_count=$(wc -l < "$existing_jsonl" | tr -d ' ')
        ok "Found existing import file: $existing_jsonl ($line_count entries)"

        if ask_yes_no "Import from this file?"; then
            info "Importing recent conversations (last 30 days first, rest in background)..."
            if $CHARLIE_CLI import --from-file "$existing_jsonl" --messages --recent-days 30; then
                ok "Recent history imported — older messages importing in background"
            else
                fail "Import had errors — check output above"
            fi
            return
        fi
    fi

    if ! ask_yes_no "Import conversation history?"; then
        info "Skipped — you can run this later: charlie import --messages"
        return
    fi

    echo ""
    ask_choice "Which provider(s) to import from?" "All (auto-discover everything)" "Claude only" "Copilot only" "Codex only"
    local choice=$?

    local provider_flag=""
    case $choice in
        1) provider_flag="--provider claude" ;;
        2) provider_flag="--provider copilot" ;;
        3) provider_flag="--provider codex" ;;
    esac

    info "Extracting and importing conversations (last 30 days first, rest in background)..."
    if $CHARLIE_CLI import --messages --recent-days 30 $provider_flag; then
        ok "Recent history imported — older messages importing in background"
        echo ""
        info "Charlie will use the Storyteller to process weekly summaries."
        info "This happens automatically during your first sessions."
    else
        fail "Import had errors — check output above"
    fi
}

# ── Summary ───────────────────────────────────────────────

summary() {
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}  🐕 Charlie is ready.${RESET}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    echo -e "  Server:    $($CHARLIE_CLI server url 2>/dev/null || echo 'not running')"
    echo -e "  Data:      ~/.charlieverse/"
    echo -e "  Logs:      ~/.charlieverse/logs/"
    echo -e "  CLI:       $CHARLIE_CLI"
    echo ""
    echo -e "  ${DIM}charlie server start|stop|status${RESET}"
    echo -e "  ${DIM}charlie --help${RESET}"
    echo ""
}

# ── Help ──────────────────────────────────────────────────

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Charlieverse Setup"
    echo ""
    echo "Usage: ./setup.sh"
    echo ""
    echo "Interactive setup that handles:"
    echo "  1. Prerequisite checks (Python 3.12+, uv, jq, git)"
    echo "  2. Python dependency installation"
    echo "  3. Charlieverse initialization (dirs, config, spaCy, web dashboard)"
    echo "  4. Server startup"
    echo "  5. CLI installation"
    echo "  6. Provider integration (Claude Code, GitHub Copilot)"
    exit 0
fi

# ── Main ──────────────────────────────────────────────────

echo ""
echo -e "${BOLD}🐕 Charlieverse Setup${RESET}"
echo -e "${DIM}From zero to Charlie.${RESET}"

preflight
install_deps
initialize
start_server
install_cli
setup_provider
import_history
summary
