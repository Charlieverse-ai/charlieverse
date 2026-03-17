#!/bin/bash

CHARLIE_DIR="$(realpath $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../..)"
PROMPTS_DIR="$CHARLIE_DIR/prompts"
INTEGRATIONS_DIR="$CHARLIE_DIR/integrations/claude"
PLUGIN_DIR="$INTEGRATIONS_DIR/plugin"
MARKETPLACE_NAME="charlieverse-marketplace"
PLUGIN_NAME="Charlieverse@$MARKETPLACE_NAME"
CLAUDE_CLI="claude"
CHARLIE_CLI="$CHARLIE_DIR/bin/charlie"

# JQ for updating the plugin version / 
JQ_CLI="jq"

# Update the plugin version to ensure claude updates the plugin cache
function bump_version() {
    PLUGIN_FILE="$PLUGIN_DIR/.claude-plugin/plugin.json"
    TMP_PLUGIN_FILE="$PLUGIN_FILE.tmp"
    $JQ_CLI '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join("."))' "$PLUGIN_FILE" > "$TMP_PLUGIN_FILE" && mv "$TMP_PLUGIN_FILE" "$PLUGIN_FILE"
}

# Check if claude + jq are installed
function verify_env() {
    if ! command -v $CLAUDE_CLI &> /dev/null; then
        echo "$CLAUDE_CLI not found"
        exit 1
    fi

    if ! command -v $JQ_CLI &> /dev/null; then
        echo "$JQ_CLI not found"
        exit 1
    fi
}

# Copy the shared prompt files into agents
function charlie_prompt() {
cat <<JSON
---
name: Charlie
description: 'Charlie from Charlieverse.'
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
    cp -r "$PROMPTS_DIR/tools/" $TOOL_AGENT_DIR
}

function setup_skills() {
    SKILLS_SRC="$INTEGRATIONS_DIR/skills"
    SKILLS_DST="$PLUGIN_DIR/skills"
    if [ -d "$SKILLS_SRC" ]; then
        mkdir -p "$SKILLS_DST"
        cp -r "$SKILLS_SRC"/* "$SKILLS_DST/"
    fi
}

function setup_hooks_json() {
    HOOKS_DIR="$PLUGIN_DIR/hooks"
    mkdir -p "$HOOKS_DIR"
    $CHARLIE_DIR/integrations/shared/hooks-json.sh "$CHARLIE_CLI" "claude-plugin" > "$HOOKS_DIR/hooks.json"
}

function setup_mcp_json() {
    local URL="$($CHARLIE_CLI server url)"
    $CHARLIE_DIR/integrations/shared/mcp-json.sh "$URL" > "$PLUGIN_DIR/.mcp.json"
}

# Install or update the local Charlieverse marketplace
function upsert_marketplace() {
    if $CLAUDE_CLI plugin marketplace list --json | grep -q "$MARKETPLACE_NAME"; then
        $CLAUDE_CLI plugin marketplace update "$MARKETPLACE_NAME"
    else
        $CLAUDE_CLI plugin marketplace add "$PLUGIN_DIR/"
    fi
}

# Install or update the local Charlieverse plugin
function upsert_plugin() {
    if $CLAUDE_CLI plugin list --json | grep -q "\"id\":\"$PLUGIN_NAME\""; then
        bump_version
        $CLAUDE_CLI plugin update "$PLUGIN_NAME"
    else
        $CLAUDE_CLI plugin install "$PLUGIN_NAME"
    fi
}

function update_claude_settings() {
    SETTINGS_FILE="$HOME/.claude/settings.json"
    PLUGIN_SETTINGS="$PLUGIN_DIR/settings.json"

    # Skip if plugin settings don't exist
    if [ ! -f "$PLUGIN_SETTINGS" ]; then
        echo "⚠ No plugin settings.json found, skipping settings merge"
        return
    fi

    # Create claude settings if it doesn't exist
    if [ ! -f "$SETTINGS_FILE" ]; then
        mkdir -p "$(dirname "$SETTINGS_FILE")"
        echo '{}' > "$SETTINGS_FILE"
    fi

    TMP="$SETTINGS_FILE.tmp"
    $JQ_CLI -s '.[0] * .[1]' "$SETTINGS_FILE" "$PLUGIN_SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"
    echo "✔ 🐕 Charlie settings applied to: $SETTINGS_FILE"
}

# Integrate

verify_env

setup_prompts
setup_skills
setup_hooks_json
setup_mcp_json

upsert_marketplace
upsert_plugin

update_claude_settings

echo ""
echo "🐕 Charlie + Claude are now integrated 🤝" 
