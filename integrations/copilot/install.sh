#!/bin/bash
#
# Charlieverse + GitHub Copilot integration installer.
# Works from both a repo checkout and a uvx/pip package install.
#

set -euo pipefail

# ── Resolve paths ─────────────────────────────────────────────────────────────
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

# Find prompts
if [ -d "$PKG_DIR/prompts" ]; then
    PROMPTS_DIR="$PKG_DIR/prompts"
elif [ -d "$SCRIPT_DIR/../../prompts" ]; then
    PROMPTS_DIR=$(cd "$SCRIPT_DIR/../../prompts" && pwd)
else
    echo "✘ Prompts directory not found"
    exit 1
fi

INTEGRATIONS_DIR="$SCRIPT_DIR"
PLUGIN_DIR="$INTEGRATIONS_DIR/plugin/"

CHARLIE_ROOT=$($CHARLIE_CLI config path)
MCP_URL=$($CHARLIE_CLI config mcp)
API_URL=$($CHARLIE_CLI config api)

JQ_CLI="jq"

PLUGIN_JSON="$PLUGIN_DIR/.github/plugin/plugin.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

function bump_version() {
    TMP_PLUGIN_FILE="$PLUGIN_JSON.tmp"
    $JQ_CLI '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join("."))' "$PLUGIN_JSON" > "$TMP_PLUGIN_FILE" && mv "$TMP_PLUGIN_FILE" "$PLUGIN_JSON"
}

function verify_env() {
    if ! command -v $JQ_CLI &> /dev/null; then
        echo "✘ $JQ_CLI not found"
        exit 1
    fi
}

# ── Steps ─────────────────────────────────────────────────────────────────────

function setup_plugin_json() {
    TEMPLATE="$INTEGRATIONS_DIR/plugin-template/"
    if [ -d "$TEMPLATE" ]; then
        rsync -rtu "$TEMPLATE" "$PLUGIN_DIR"
    fi

    mkdir -p "$(dirname "$PLUGIN_JSON")"

    if [ ! -f "$PLUGIN_JSON" ]; then
        cat > "$PLUGIN_JSON" <<PJSON
{
  "name": "charlieverse",
  "description": "Charlie from Charlieverse — your personal AI companion with persistent memory.",
  "version": "1.0.0",
  "license": "MIT",
  "author": {
    "name": "Charlieverse"
  },
  "agents": "./agents",
  "skills": []
}
PJSON
    fi
}

function update_plugin_skills_list() {
    SKILLS_DIR="$PLUGIN_DIR/skills"
    if [ ! -d "$SKILLS_DIR" ]; then
        return
    fi

    SKILL_PATHS="[]"
    for skill_dir in "$SKILLS_DIR"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            SKILL_PATHS=$($JQ_CLI --arg p "./skills/$skill_name" '. + [$p]' <<< "$SKILL_PATHS")
        fi
    done

    TMP="$PLUGIN_JSON.tmp"
    $JQ_CLI --argjson skills "$SKILL_PATHS" '.skills = $skills' "$PLUGIN_JSON" > "$TMP" && mv "$TMP" "$PLUGIN_JSON"
}

function charlie_prompt() {
cat <<PROMPT
---
name: Charlie
description: 'Charlie from Charlieverse.'
tools:
  - server/*
---
$(cat "$PROMPTS_DIR/Charlie.md")
PROMPT
}

function setup_prompts() {
    AGENTS_DIR="$PLUGIN_DIR/agents"
    mkdir -p "$AGENTS_DIR"

    charlie_prompt > "$AGENTS_DIR/Charlie.agent.md"

    TOOL_AGENT_DIR="$AGENTS_DIR/tools/"
    mkdir -p "$TOOL_AGENT_DIR"
    for md_file in "$PROMPTS_DIR/tools/"*.md; do
        if [ -f "$md_file" ]; then
            basename=$(basename "$md_file" .md)
            cp "$md_file" "$TOOL_AGENT_DIR/${basename}.agent.md"
        fi
    done
}

function setup_hooks_json() {
    HOOKS_DIR="$PLUGIN_DIR/hooks"
    mkdir -p "$HOOKS_DIR"

    function hook() {
        echo "$CHARLIE_CLI hooks $1 --source 'copilot-plugin'"
    }

    cat > "$HOOKS_DIR/hooks.json" <<HOOKS
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "$(hook session-start)"
      }
    ],
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "$(hook prompt-submit)"
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "$(hook stop)"
      }
    ],
    "PostToolUse": [
      {
        "type": "command",
        "command": "$(hook tool-use)"
      }
    ],
    "PreCompact": [
      {
        "type": "command",
        "command": "$(hook save-reminder)"
      }
    ]
  }
}
HOOKS
}

function setup_mcp_json() {
    local URL="$MCP_URL"
    cat > "$PLUGIN_DIR/.mcp.json" <<MCP
{
  "mcpServers": {
    "charlie-tools": {
      "type": "http",
      "url": "$URL"
    }
  }
}
MCP
}

function setup_skills() {
    SKILLS_DST="$PLUGIN_DIR/skills"
    mkdir -p "$SKILLS_DST"

    COPILOT_SKILLS_SRC="$INTEGRATIONS_DIR/skills"
    if [ -d "$COPILOT_SKILLS_SRC" ]; then
        cp -r "$COPILOT_SKILLS_SRC/" "$SKILLS_DST/"
    fi

    SHARED_SKILLS_SRC="$PROMPTS_DIR/skills"
    if [ -d "$SHARED_SKILLS_SRC" ]; then
        cp -r "$SHARED_SKILLS_SRC/" "$SKILLS_DST/"
    fi

    rm -rf "$SKILLS_DST/charlie-import" 2>/dev/null

    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_PATH|$CHARLIE_ROOT|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_CLI|$CHARLIE_CLI|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_API|$API_URL|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_MCP|$MCP_URL|g" {} +
}

function register_plugin() {
    local SETTINGS_CANDIDATES=(
        "$HOME/Library/Application Support/Code/User/settings.json"
        "$HOME/.config/Code/User/settings.json"
        "${APPDATA:-/dev/null}/Code/User/settings.json"
    )

    local SETTINGS_FILE=""
    for candidate in "${SETTINGS_CANDIDATES[@]}"; do
        if [ -f "$candidate" ]; then
            SETTINGS_FILE="$candidate"
            break
        fi
    done

    local ABSOLUTE_PLUGIN_DIR="$(realpath "$PLUGIN_DIR")"

    if [ -z "$SETTINGS_FILE" ]; then
        echo "⚠ Could not find VS Code settings.json"
        echo "  Manually add to your VS Code settings:"
        echo "  \"chat.pluginLocations\": { \"$ABSOLUTE_PLUGIN_DIR\": true }"
        echo "  \"chat.plugins.enabled\": true"
        return
    fi

    if grep -q "$ABSOLUTE_PLUGIN_DIR" "$SETTINGS_FILE" 2>/dev/null; then
        echo "✔ 🐕 Plugin already registered in VS Code settings"
        return
    fi

    echo ""
    echo "📋 Add this to your VS Code settings (Cmd+Shift+P → 'Preferences: Open User Settings (JSON)'):"
    echo ""
    echo "  \"chat.pluginLocations\": {"
    echo "    \"$ABSOLUTE_PLUGIN_DIR\": true"
    echo "  },"
    echo "  \"chat.plugins.enabled\": true"
    echo ""
}

# ── Run ───────────────────────────────────────────────────────────────────────

verify_env

setup_plugin_json
setup_prompts
setup_skills
setup_hooks_json
setup_mcp_json

update_plugin_skills_list
bump_version
register_plugin

echo ""
echo "🐕 Charlie + Copilot are now integrated 🤝"
