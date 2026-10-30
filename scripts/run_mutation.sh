#!/usr/bin/env bash
# Mutation testing with mutmut. mutmut 3 needs fork(), so on Windows run this inside WSL:
#   wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh <label>
# It copies backend/ to a native Linux directory (fast, avoids the OneDrive mount), runs mutmut,
# and writes a plain-text report to docs/mutation/<label>.txt.
set -euo pipefail

LABEL="${1:-run}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${MUTMUT_WORK_DIR:-$HOME/mutmut-work}"
VENV="${MUTMUT_VENV:-$HOME/mmenv}"
REPORT="$REPO_ROOT/docs/mutation/$LABEL.txt"

if [ ! -x "$VENV/bin/mutmut" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q mutmut pytest fastapi httpx uvicorn
fi

rm -rf "$WORK_DIR" && mkdir -p "$WORK_DIR"
cp -r "$REPO_ROOT/backend" "$WORK_DIR/backend"
find "$WORK_DIR" -name __pycache__ -prune -exec rm -rf {} +
cd "$WORK_DIR/backend"

"$VENV/bin/mutmut" run >/dev/null 2>&1 || true
ALL="$("$VENV/bin/mutmut" results --all true 2>/dev/null | grep ': ' || true)"

count() { printf '%s\n' "$ALL" | grep -c ": $1\$" || true; }
KILLED="$(count killed)"; SURVIVED="$(count survived)"; TIMEOUT="$(count timeout)"
SUSPICIOUS="$(count suspicious)"; SKIPPED="$(count skipped)"; NOT_CHECKED="$(count 'not checked')"
TOTAL=$((KILLED + SURVIVED + TIMEOUT + SUSPICIOUS + SKIPPED + NOT_CHECKED))
CAUGHT=$((KILLED + TIMEOUT))
SCORE="$(awk -v c="$CAUGHT" -v t="$TOTAL" 'BEGIN { printf "%.1f", (t ? 100 * c / t : 0) }')"

mkdir -p "$(dirname "$REPORT")"
{
  echo "Mutation report: $LABEL"
  echo "Tool: mutmut $("$VENV/bin/mutmut" --version 2>/dev/null | tr -d '\n')"
  echo "Scope: src/invoice_app/domain (tests: tests/test_approval_service.py tests/test_approval_policy.py if present)"
  echo
  echo "Total mutants : $TOTAL"
  echo "Killed        : $KILLED"
  echo "Timeout       : $TIMEOUT"
  echo "Survived      : $SURVIVED"
  echo "Other         : $((SUSPICIOUS + SKIPPED + NOT_CHECKED))"
  echo "Mutation score: $SCORE% (killed+timeout / total)"
  echo
  echo "Survivors:"
  printf '%s\n' "$ALL" | grep ': survived$' | sed 's/^ */  /' || true
} | tee "$REPORT"
