#!/usr/bin/env bash
# Run a wing's scripted playthrough headless: tests/run_playthrough.sh <wing_id>
# Exit 0 only if every check passed and the log has no script errors or leaks.
set -uo pipefail
cd "$(dirname "$0")/.."
[[ $# -ge 1 ]] || { echo "usage: tests/run_playthrough.sh <wing_id>" >&2; exit 2; }
exec tests/run_smoke.sh tests/playthrough.tscn -- "--wing=$1"
