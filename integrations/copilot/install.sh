#!/bin/bash

CHARLIE_DIR="$(realpath $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../..)"
PROMPTS_DIR="$CHARLIE_DIR/prompts"
SHARED_DIR="$CHARLIE_DIR/integrations/shared"
INTEGRATIONS_DIR="$CHARLIE_DIR/integrations/copilot"
PLUGIN_DIR="$INTEGRATIONS_DIR/plugin/"
CHARLIE_CLI="$CHARLIE_DIR/bin/charlie"

JQ_CLI="jq"

# Update the plugin version to ensure copilot updates the plugin cache
function bump_version() {
    PLUGIN_FILE="$PLUGIN_DIR/.github/plugin.json"
    TMP_PLUGIN_FILE="$PLUGIN_FILE.tmp"
    $JQ_CLI '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join("."))' "$PLUGIN_FILE" > "$TMP_PLUGIN_FILE" && mv "$TMP_PLUGIN_FILE" "$PLUGIN_FILE"
}

function verify_env() {
    if ! command -v $JQ_CLI &> /dev/null; then
        echo "$JQ_CLI not found"
        exit 1
    fi
}

# Copy the shared prompt files into agents
function charlie_prompt() {
cat <<PROMPT
---
name: Charlie
description: 'Charlie from Charlieverse.'
---
$(cat "$PROMPTS_DIR/Charlie.md")
PROMPT
}

function setup_prompts() {
    AGENTS_DIR="$PLUGIN_DIR/agents"
    mkdir -p "$AGENTS_DIR"

    # Copy Charlie with frontmatter
    charlie_prompt > "$AGENTS_DIR/Charlie.md"

    # Copy Tool Agents
    TOOL_AGENT_DIR="$AGENTS_DIR/tools/"
    mkdir -p "$TOOL_AGENT_DIR"
    cp -r "$PROMPTS_DIR/tools/" $TOOL_AGENT_DIR
}

function setup_hooks_json() {
    HOOKS_DIR="$PLUGIN_DIR/hooks"
    mkdir -p "$HOOKS_DIR"
    $SHARED_DIR/hooks-json.sh "$CHARLIE_CLI" "copilot-plugin" > "$HOOKS_DIR/hooks.json"
}

function setup_mcp_json() {
    local URL="$($CHARLIE_CLI server url)"
    $SHARED_DIR/mcp-json.sh "$URL" > "$PLUGIN_DIR/.mcp.json"
}

# Register plugin via VS Code settings (chat.plugins.paths)
function register_plugin() {
    # Try multiple possible settings locations
    local SETTINGS_CANDIDATES=(
        "$HOME/Library/Application Support/Code/User/settings.json"
        "$HOME/.config/Code/User/settings.json"
        "$APPDATA/Code/User/settings.json"
    )

    local SETTINGS_FILE=""
    for candidate in "${SETTINGS_CANDIDATES[@]}"; do
        if [ -f "$candidate" ]; then
            SETTINGS_FILE="$candidate"
            break
        fi
    done

    if [ -z "$SETTINGS_FILE" ]; then
        echo "⚠ Could not find VS Code settings.json"
        echo "  Manually add to your VS Code settings:"
        echo "  \"chat.plugins.paths\": { \"$PLUGIN_DIR\": true }"
        return
    fi

    local ABSOLUTE_PLUGIN_DIR="$(realpath "$PLUGIN_DIR")"

    # Check if already registered
    if grep -q "$ABSOLUTE_PLUGIN_DIR" "$SETTINGS_FILE" 2>/dev/null; then
        echo "✔ 🐕 Plugin already registered in VS Code settings"
        return
    fi

    # VS Code uses JSONC (comments + trailing commas) so we can't use jq.
    # Instead, just tell the user what to add.
    echo ""
    echo "📋 Add this to your VS Code settings (Cmd+Shift+P → 'Preferences: Open User Settings (JSON)'):"
    echo ""
    echo "  \"chat.plugins.paths\": {"
    echo "    \"$ABSOLUTE_PLUGIN_DIR\": true"
    echo "  }"
    echo ""
    echo "  Or run: code --add-plugin-path \"$ABSOLUTE_PLUGIN_DIR\""
}

# Integrate

verify_env

setup_prompts
setup_hooks_json
setup_mcp_json

bump_version
register_plugin

echo ""
echo "🐕 Charlie + Copilot are now integrated 🤝"
