---
name: run-checks
description: The exact commands to run unit tests, mutation tests and the Playwright end-to-end test for this repo, in order, and how to read their one-line summaries. Load before claiming a change works.
---

# Run checks (in this order)

1. Unit + API tests (about 1 second):
   `python -m pytest backend/tests -q`
2. Mutation tests (needs WSL because mutmut 3 uses `fork()`; about 20 seconds):
   `wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh <label>` → writes `docs/mutation/<label>.txt`
   Survivors: `wsl -d Ubuntu-22.04 -- bash scripts/show_survivors.sh`
3. End-to-end (starts the server itself):
   `cd e2e && npm install && npx playwright install chromium && npm test`

Each run is summarised by the `check_summary.py` hook as one line:
`CHECK <name> | <metric>=<value> ... | result=<pass|fail>`

Do not report a change as working unless the matching CHECK line says `result=pass`. On Git Bash prefix `wsl` commands with `MSYS_NO_PATHCONV=1`.
