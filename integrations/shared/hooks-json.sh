#!/bin/bash
CHARLIE_CLI=$1
SOURCE=$2

function hook() {
  echo "$CHARLIE_CLI hooks $1 --source '$SOURCE'"
}

cat <<JSON
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "$(hook session-start)",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "command": "$(hook prompt-submit)",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "command": "$(hook stop)",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "$(hook tool-use)",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ]
  }
}
JSON