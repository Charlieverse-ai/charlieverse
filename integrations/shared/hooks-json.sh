#!/bin/bash
CHARLIE_CLI=$1
SOURCE=$2

function hook() {
  echo "$CHARLIE_CLI hooks $1 --source '$SOURCE'"
}

function section_hook() {
  echo "$CHARLIE_CLI hooks session-start --source '$SOURCE' --section $1"
}

cat <<JSON
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "$(section_hook personality)",
            "type": "command"
          },
          {
            "command": "$(section_hook pinned-memories)",
            "type": "command"
          },
          {
            "command": "$(section_hook pinned-knowledge)",
            "type": "command"
          },
          {
            "command": "$(section_hook sessions)",
            "type": "command"
          },
          {
            "command": "$(section_hook moments)",
            "type": "command"
          },
          {
            "command": "$(section_hook related)",
            "type": "command"
          },
          {
            "command": "$(section_hook story)",
            "type": "command"
          },
          {
            "command": "$(section_hook messages)",
            "type": "command"
          },
            {
            "command": "$(section_hook user-hooks)",
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
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "command": "$(hook save-reminder)",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ]
  }
}
JSON