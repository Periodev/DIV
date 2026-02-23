#!/usr/bin/env bash
# check.sh — headless compile check for DIV Godot project
# Usage: bash check.sh
GODOT="D:/Godot/Godot_4.5.1/Godot_v4.5.1-stable_win64.exe"
PROJECT="$(cd "$(dirname "$0")" && pwd)"

"$GODOT" --headless --quit --path "$PROJECT" 2>&1
echo "Exit code: $?"
