#!/usr/bin/env bash
# Prints the diff of every surviving mutant from the last scripts/run_mutation.sh run (inside WSL).
set -uo pipefail

WORK_DIR="${MUTMUT_WORK_DIR:-$HOME/mutmut-work}"
VENV="${MUTMUT_VENV:-$HOME/mmenv}"
cd "$WORK_DIR/backend"

"$VENV/bin/mutmut" results 2>/dev/null | grep ': survived$' | sed 's/^ *//; s/: survived$//' |
while IFS= read -r mutant; do
  echo "##### $mutant"
  "$VENV/bin/mutmut" show "$mutant" 2>/dev/null | grep -E '^[-+]' | grep -vE '^(---|\+\+\+)'
done
