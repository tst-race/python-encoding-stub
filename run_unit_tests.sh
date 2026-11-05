#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == "--real-bindings" ]]; then
    shift
    exec python3 "${SCRIPT_DIR}/test/check_bindings.py" "$@"
fi
exec python3 -m unittest discover -s "${SCRIPT_DIR}/test" -p 'test_*.py' "$@"