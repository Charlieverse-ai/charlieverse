#!/bin/bash
#
# Charlieverse + Claude Code integration installer.
# Works from both a repo checkout and a uvx/pip package install.
#

set -euo pipefail

# ── Resolve paths ─────────────────────────────────────────────────────────────
# SCRIPT_DIR = integrations/claude/ (wherever this script lives)
# PKG_DIR    = the charlieverse package root (two levels up from integrations/claude/)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PKG_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

# Find charlie CLI: PATH first (uvx install), then bin/ in repo checkout
if command -v charlie &>/dev/null; then
    CHARLIE_CLI="charlie"
elif [ -x "$PKG_DIR/bin/charlie" ]; then
    CHARLIE_CLI="$PKG_DIR/bin/charlie"
else
    echo "✘ charlie CLI not found — install charlieverse first"
    exit 1
fi

# Find prompts: bundled in package (charlieverse/prompts/) or repo root (prompts/)
if [ -d "$PKG_DIR/prompts" ]; then
    PROMPTS_DIR="$PKG_DIR/prompts"
elif [ -d "$SCRIPT_DIR/../../prompts" ]; then
    PROMPTS_DIR=$(cd "$SCRIPT_DIR/../../prompts" && pwd)
else
    echo "✘ Prompts directory not found"
    exit 1
fi

# Find shared integration scripts
if [ -d "$SCRIPT_DIR/../shared" ]; then
    SHARED_DIR="$SCRIPT_DIR/../shared"
elif [ -d "$PKG_DIR/integrations/shared" ]; then
    SHARED_DIR="$PKG_DIR/integrations/shared"
else
    echo "✘ Shared integration scripts not found"
    exit 1
fi

MARKETPLACE_NAME="charlieverse-marketplace"
PLUGIN_NAME="Charlieverse@$MARKETPLACE_NAME"
CLAUDE_CLI="claude"
JQ_CLI="jq"

CHARLIE_ROOT=$($CHARLIE_CLI config path)
MCP_URL=$($CHARLIE_CLI config mcp)
API_URL=$($CHARLIE_CLI config api)

# Source templates from the package
CHARLIE_INTEGRATION_DIR="$SCRIPT_DIR"
# Destination: ~/.charlieverse/integrations/claude/
INTEGRATIONS_DIR="$CHARLIE_ROOT/integrations/claude"
PLUGIN_DIR="$INTEGRATIONS_DIR"

# ── Helpers ───────────────────────────────────────────────────────────────────

function bump_version() {
    PLUGIN_FILE="$PLUGIN_DIR/.claude-plugin/plugin.json"
    TMP_PLUGIN_FILE="$PLUGIN_FILE.tmp"
    $JQ_CLI '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join("."))' "$PLUGIN_FILE" > "$TMP_PLUGIN_FILE" && mv "$TMP_PLUGIN_FILE" "$PLUGIN_FILE"
}

function version() {
    PLUGIN_FILE="$PLUGIN_DIR/.claude-plugin/plugin.json"
    $JQ_CLI -r '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join(".")) | .version' "$PLUGIN_FILE"
}

# ── Steps ─────────────────────────────────────────────────────────────────────

function verify_env() {
    if ! command -v $CLAUDE_CLI &> /dev/null; then
        echo "✘ $CLAUDE_CLI not found"
        exit 1
    fi

    if ! command -v $JQ_CLI &> /dev/null; then
        echo "✘ $JQ_CLI not found"
        exit 1
    fi

    mkdir -p "$CHARLIE_ROOT"
    mkdir -p "$INTEGRATIONS_DIR"
    mkdir -p "$PLUGIN_DIR"
}

function setup_plugin_folder() {
    TEMPLATE="$CHARLIE_INTEGRATION_DIR/plugin-template/"
    rsync -av --delete "$TEMPLATE" "$INTEGRATIONS_DIR"
}

function charlie_prompt() {
cat <<JSON
---
name: Charlie
description: 'Charlie $(version)'
color: blue
---
$(cat "$PROMPTS_DIR/Charlie.md")
JSON
}

function setup_prompts() {
    AGENTS_DIR="$PLUGIN_DIR/agents"
    mkdir -p "$AGENTS_DIR"

    # Copy Charlie
    charlie_prompt > "$AGENTS_DIR/Charlie.md"

    # Copy Tool Agents
    TOOL_AGENT_DIR="$AGENTS_DIR/tools/"
    mkdir -p "$TOOL_AGENT_DIR"
    cp -r "$PROMPTS_DIR/tools/" "$TOOL_AGENT_DIR"
}

function setup_skills() {
    SKILLS_DST="$PLUGIN_DIR/skills"
    mkdir -p "$SKILLS_DST"

    # Copy integration-specific skills (session-save, charlie-import, etc.)
    SKILLS_SRC="$CHARLIE_INTEGRATION_DIR/skills"
    cp -r "$SKILLS_SRC/" "$SKILLS_DST/"

    # Copy shared skills from prompts/skills/ to the plugin
    SHARED_SKILLS_SRC="$PROMPTS_DIR/skills"
    if [ -d "$SHARED_SKILLS_SRC" ]; then
        cp -r "$SHARED_SKILLS_SRC/" "$SKILLS_DST/"
    fi

    # Clean up old user-level skills that were previously copied to ~/.claude/skills/
    # These now live exclusively in the plugin — remove duplicates from prior installs.
    CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
    LEGACY_SKILLS=("trick" "codex" "copilot")
    for skill in "${LEGACY_SKILLS[@]}"; do
        if [ -f "$CLAUDE_SKILLS_DIR/$skill/SKILL.md" ] && grep -qi "charlie" "$CLAUDE_SKILLS_DIR/$skill/SKILL.md"; then
            rm -rf "$CLAUDE_SKILLS_DIR/$skill/"
            echo "  cleaned up legacy skill: ~/.claude/skills/$skill/"
        fi
    done

    # Variable replacement across plugin skills
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_PATH|$CHARLIE_ROOT|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_CLI|$CHARLIE_CLI|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_API|$API_URL|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_MCP|$MCP_URL|g" {} +
}

function setup_hooks_json() {
    HOOKS_DIR="$PLUGIN_DIR/hooks"
    mkdir -p "$HOOKS_DIR"
    bash "$SHARED_DIR/hooks-json.sh" "$CHARLIE_CLI" "claude-plugin" > "$HOOKS_DIR/hooks.json"
}

function setup_mcp_json() {
    bash "$SHARED_DIR/mcp-json.sh" "$MCP_URL" > "$PLUGIN_DIR/.mcp.json"
}

function upsert_marketplace() {
    EXISTING=$($CLAUDE_CLI plugin marketplace list --json | jq -r ".[] | select(.name == \"$MARKETPLACE_NAME\") | .path")

    if [ ! "$EXISTING" = "$PLUGIN_DIR" ]; then
        if [ -z "$EXISTING" ]; then
            $CLAUDE_CLI plugin marketplace add "$PLUGIN_DIR/"
        else
            $CLAUDE_CLI plugin marketplace rm "$MARKETPLACE_NAME"
            $CLAUDE_CLI plugin marketplace add "$PLUGIN_DIR/"
        fi
    fi

    $CLAUDE_CLI plugin marketplace rm "$MARKETPLACE_NAME"
    OLD=$(realpath ~/.claude/plugins/cache/$MARKETPLACE_NAME 2>/dev/null || true)
    [ -n "$OLD" ] && rm -rf "$OLD"

    $CLAUDE_CLI plugin marketplace add "$PLUGIN_DIR/"
    $CLAUDE_CLI plugin marketplace update "$MARKETPLACE_NAME"
}

function upsert_plugin() {
    if $CLAUDE_CLI plugin list --json | grep -q "$PLUGIN_NAME"; then
        bump_version
        $CLAUDE_CLI plugin update "$PLUGIN_NAME"
    else
        $CLAUDE_CLI plugin install "$PLUGIN_NAME"
    fi
}

function update_claude_settings() {
    SETTINGS_FILE="$HOME/.claude/settings.json"
    PLUGIN_SETTINGS="$CHARLIE_INTEGRATION_DIR/settings.json"

    if [ ! -f "$SETTINGS_FILE" ]; then
        mkdir -p "$(dirname "$SETTINGS_FILE")"
        echo '{}' > "$SETTINGS_FILE"
    fi

    TMP="$SETTINGS_FILE.tmp"
    $JQ_CLI -s '.[0] * .[1]' "$SETTINGS_FILE" "$PLUGIN_SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"
    echo "✔ 🐕 Charlie settings applied to: $SETTINGS_FILE"
}

# ── Run ───────────────────────────────────────────────────────────────────────

verify_env
setup_plugin_folder
setup_prompts
setup_skills
setup_hooks_json
setup_mcp_json

upsert_marketplace
upsert_plugin

update_claude_settings

echo ""
echo "🐕 Charlie + Claude are now integrated 🤝"
