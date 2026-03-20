#!/bin/bash

CHARLIE_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")/../..")
PROMPTS_DIR="$CHARLIE_DIR/prompts"
MARKETPLACE_NAME="charlieverse-marketplace"
PLUGIN_NAME="Charlieverse@$MARKETPLACE_NAME"
CLAUDE_CLI="claude"
CHARLIE_CLI="$CHARLIE_DIR/bin/charlie"

CHARLIE_ROOT=$($CHARLIE_CLI config path)
MCP_URL=$($CHARLIE_CLI config mcp)
API_URL=$($CHARLIE_CLI config api)

CHARLIE_INTEGRATION_DIR="$CHARLIE_DIR/integrations/claude"
INTEGRATIONS_DIR="$CHARLIE_ROOT/integrations/claude"
PLUGIN_DIR="$INTEGRATIONS_DIR"

# JQ for updating the plugin version / 
JQ_CLI="jq"

# Update the plugin version to ensure claude updates the plugin cache
function bump_version() {
    PLUGIN_FILE="$PLUGIN_DIR/.claude-plugin/plugin.json"
    TMP_PLUGIN_FILE="$PLUGIN_FILE.tmp"
    $JQ_CLI '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join("."))' "$PLUGIN_FILE" > "$TMP_PLUGIN_FILE" && mv "$TMP_PLUGIN_FILE" "$PLUGIN_FILE"
}

function version() {
    PLUGIN_FILE="$PLUGIN_DIR/.claude-plugin/plugin.json"
    $JQ_CLI -r '.version |= (split(".") | .[-1] |= (tonumber + 1 | tostring) | join(".")) | .version' "$PLUGIN_FILE"
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

    mkdir -p "$CHARLIE_ROOT"
    mkdir -p "$INTEGRATIONS_DIR"
    mkdir -p "$PLUGIN_DIR"
}

function setup_plugin_folder() {
    TEMPLATE="$CHARLIE_INTEGRATION_DIR/plugin-template/"
    rsync -rtuv "$TEMPLATE" "$INTEGRATIONS_DIR"
}

# Copy the shared prompt files into agents
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
    
    mkdir -p "$AGENTS_DIR/cli/"
    cp -r "$PROMPTS_DIR/cli/" "$AGENTS_DIR/cli"
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

    # Skills that need context: fork don't work from plugins.
    # Move them to ~/.claude/skills/ (user-level) instead.
    CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
    FORK_SKILLS=("charlie-skill" "codex" "copilot")
    for skill in "${FORK_SKILLS[@]}"; do
        if [ -d "$SKILLS_DST/$skill" ]; then
            mkdir -p "$CLAUDE_SKILLS_DIR/$skill"
            cp -r "$SKILLS_DST/$skill/" "$CLAUDE_SKILLS_DIR/$skill/"
            rm -rf "$SKILLS_DST/$skill"
        fi
    done

    # Variable replacement across plugin skills
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_PATH|$CHARLIE_ROOT|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_CLI|$CHARLIE_CLI|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_API|$API_URL|g" {} +
    find "$SKILLS_DST" -name "SKILL.md" -exec sed -i '' "s|V_MCP|$MCP_URL|g" {} +

    # Variable replacement across user-level skills too
    for skill in "${FORK_SKILLS[@]}"; do
        if [ -f "$CLAUDE_SKILLS_DIR/$skill/SKILL.md" ]; then
            sed -i '' "s|V_PATH|$CHARLIE_ROOT|g" "$CLAUDE_SKILLS_DIR/$skill/SKILL.md"
            sed -i '' "s|V_CLI|$CHARLIE_CLI|g" "$CLAUDE_SKILLS_DIR/$skill/SKILL.md"
            sed -i '' "s|V_API|$API_URL|g" "$CLAUDE_SKILLS_DIR/$skill/SKILL.md"
            sed -i '' "s|V_MCP|$MCP_URL|g" "$CLAUDE_SKILLS_DIR/$skill/SKILL.md"
        fi
    done
}

function setup_hooks_json() {
    HOOKS_DIR="$PLUGIN_DIR/hooks"
    mkdir -p "$HOOKS_DIR"
    "$CHARLIE_DIR/integrations/shared/hooks-json.sh" "$CHARLIE_CLI" "claude-plugin" > "$HOOKS_DIR/hooks.json"
}

function setup_mcp_json() {
    URL="$($CHARLIE_CLI server url)"
    "$CHARLIE_DIR/integrations/shared/mcp-json.sh" "$MCP_URL" > "$PLUGIN_DIR/.mcp.json"
}

# Install or update the local Charlieverse marketplace
function upsert_marketplace() {
    EXISTING=$($CLAUDE_CLI plugin marketplace list --json | jq -r ".[] | select(.name == \"$MARKETPLACE_NAME\") | .path")

    # If the install path is not our plugin dir
    if [ ! "$EXISTING" = "$PLUGIN_DIR" ]; then
        # If it doesn't exist at all, then add it
        if [ -z "$EXISTING" ]; then
            $CLAUDE_CLI plugin marketplace add "$PLUGIN_DIR/"
        else
            # Different install path, reset by removing
            $CLAUDE_CLI plugin marketplace rm "$MARKETPLACE_NAME"
            $CLAUDE_CLI plugin marketplace add "$PLUGIN_DIR/"
        fi
    fi

    # Update
    $CLAUDE_CLI plugin marketplace update "$MARKETPLACE_NAME"
}

# Install or update the local Charlieverse plugin
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
