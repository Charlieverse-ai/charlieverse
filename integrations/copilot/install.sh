#!/bin/bash

CHARLIE_DIR="$(realpath $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../..)"
PROMPTS_DIR="$CHARLIE_DIR/prompts"
SHARED_DIR="$CHARLIE_DIR/integrations/shared"
INTEGRATIONS_DIR="$CHARLIE_DIR/integrations/copilot"
PLUGIN_DIR="$INTEGRATIONS_DIR/plugin/"
CHARLIE_CLI="$CHARLIE_DIR/bin/charlie"

CHARLIE_ROOT=$($CHARLIE_CLI config path)
MCP_URL=$($CHARLIE_CLI config mcp)
API_URL=$($CHARLIE_CLI config api)

JQ_CLI="jq"

# Fix 1+2: plugin.json lives at .github/plugin/plugin.json
PLUGIN_JSON="$PLUGIN_DIR/.github/plugin/plugin.json"

function bump_version() {
    TMP_PLUGIN_FILE="$PLUGIN_JSON.tmp"
    $JQ_CLI '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join("."))' "$PLUGIN_JSON" > "$TMP_PLUGIN_FILE" && mv "$TMP_PLUGIN_FILE" "$PLUGIN_JSON"
}

function verify_env() {
    if ! command -v $JQ_CLI &> /dev/null; then
        echo "$JQ_CLI not found"
        exit 1
    fi
}

function setup_plugin_json() {
    # Copy the plugin.json template if it doesn't exist yet
    TEMPLATE="$INTEGRATIONS_DIR/plugin-template/"
    if [ -d "$TEMPLATE" ]; then
        rsync -rtu "$TEMPLATE" "$PLUGIN_DIR"
    fi

    # Ensure directory exists
    mkdir -p "$(dirname "$PLUGIN_JSON")"

    # Create plugin.json if missing
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
    # Update the skills array in plugin.json to list all installed skill directories
    SKILLS_DIR="$PLUGIN_DIR/skills"
    if [ ! -d "$SKILLS_DIR" ]; then
        return
    fi

    # Build JSON array of skill paths
    SKILL_PATHS="[]"
    for skill_dir in "$SKILLS_DIR"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            SKILL_PATHS=$($JQ_CLI --arg p "./skills/$skill_name" '. + [$p]' <<< "$SKILL_PATHS")
        fi
    done

    # Update plugin.json
    TMP="$PLUGIN_JSON.tmp"
    $JQ_CLI --argjson skills "$SKILL_PATHS" '.skills = $skills' "$PLUGIN_JSON" > "$TMP" && mv "$TMP" "$PLUGIN_JSON"
}

# Fix 3: Copilot agents use .agent.md extension
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

    # Copy Charlie with .agent.md extension
    charlie_prompt > "$AGENTS_DIR/Charlie.agent.md"

    # Copy Tool Agents, renaming .md to .agent.md
    TOOL_AGENT_DIR="$AGENTS_DIR/tools/"
    mkdir -p "$TOOL_AGENT_DIR"
    for md_file in "$PROMPTS_DIR/tools/"*.md; do
        if [ -f "$md_file" ]; then
            basename=$(basename "$md_file" .md)
            cp "$md_file" "$TOOL_AGENT_DIR/${basename}.agent.md"
        fi
    done
}

# Fix 4: Copilot uses flat hook entries (no nested hooks/matcher wrapper)
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

# Fix 5: Copilot plugin .mcp.json needs mcpServers wrapper
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

    # Copy integration-specific skills if they exist
    COPILOT_SKILLS_SRC="$INTEGRATIONS_DIR/skills"
    if [ -d "$COPILOT_SKILLS_SRC" ]; then
        cp -r "$COPILOT_SKILLS_SRC/" "$SKILLS_DST/"
    fi

    # Copy shared skills from prompts/skills/
    SHARED_SKILLS_SRC="$PROMPTS_DIR/skills"
    if [ -d "$SHARED_SKILLS_SRC" ]; then
        cp -r "$SHARED_SKILLS_SRC/" "$SKILLS_DST/"
    fi

    # Remove skills that shouldn't be user-visible on Copilot
    # (user-invocable: false has no Copilot equivalent)
    rm -rf "$SKILLS_DST/charlie-import" 2>/dev/null

    # Variable replacement across all skills
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_PATH|$CHARLIE_ROOT|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_CLI|$CHARLIE_CLI|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_API|$API_URL|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_MCP|$MCP_URL|g" {} +
}

# Fix 6: Correct settings key is chat.pluginLocations (not chat.plugins.paths)
function register_plugin() {
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

    local ABSOLUTE_PLUGIN_DIR="$(realpath "$PLUGIN_DIR")"

    if [ -z "$SETTINGS_FILE" ]; then
        echo "⚠ Could not find VS Code settings.json"
        echo "  Manually add to your VS Code settings:"
        echo "  \"chat.pluginLocations\": { \"$ABSOLUTE_PLUGIN_DIR\": true }"
        echo "  \"chat.plugins.enabled\": true"
        return
    fi

    # Check if already registered
    if grep -q "$ABSOLUTE_PLUGIN_DIR" "$SETTINGS_FILE" 2>/dev/null; then
        echo "✔ 🐕 Plugin already registered in VS Code settings"
        return
    fi

    # VS Code uses JSONC (comments + trailing commas) so we can't use jq.
    echo ""
    echo "📋 Add this to your VS Code settings (Cmd+Shift+P → 'Preferences: Open User Settings (JSON)'):"
    echo ""
    echo "  \"chat.pluginLocations\": {"
    echo "    \"$ABSOLUTE_PLUGIN_DIR\": true"
    echo "  },"
    echo "  \"chat.plugins.enabled\": true"
    echo ""
}

# Integrate

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
