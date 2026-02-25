#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY=( "$PYTHON_BIN" )
elif command -v python3 >/dev/null 2>&1; then
  PY=( python3 )
elif command -v python >/dev/null 2>&1; then
  PY=( python )
elif command -v py >/dev/null 2>&1; then
  PY=( py -3 )
else
  echo "No Python found. Set PYTHON_BIN or install python3." >&2
  exit 2
fi

"${PY[@]}" tools/stress_trace_all_levels.py "$@"

