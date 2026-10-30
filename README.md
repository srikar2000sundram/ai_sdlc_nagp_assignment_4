# Invoice Approval Demo App

A small invoice approval app used for live AI-in-SDLC demos. It is deliberately simple: a Python (FastAPI) API, a plain web UI, and an in-memory store, so it runs with one command and no database. (This is a Python port of the original ASP.NET Core 8 demo.)

## Run it

```
pip install -e "backend[dev]"
python -m uvicorn invoice_app.api.main:app --app-dir backend/src --port 5000
```

Open http://localhost:5000 and sign in:

| User | Password | Role |
| --- | --- | --- |
| `demo.manager` | `ChangeMe123!` | Manager |
| `demo.director` | `ChangeMe123!` | Director |
| `demo.director2` | `ChangeMe123!` | Director |
| `demo.admin` | `ChangeMe123!` | Admin |

These are demo accounts for a local, in-memory app. They are not real credentials.

## What it does

1. Create an invoice (it starts as a draft).
2. Submit it for approval.
3. An approver approves it, or rejects it with a reason.

Invoices move through Draft, Pending Approval, then Approved or Rejected.

### Approval limits by role

| Invoice amount | Who may approve | Approvals needed |
| --- | --- | --- |
| up to 50,000 | Manager or Director | 1 |
| up to 500,000 | Director | 1 |
| above 500,000 | first: Manager or Director, second: Director | 2 different users |

A refused attempt shows a clear reason and changes nothing. See [the spec](specs/001-invoice-approval-limits/spec.md).

## Tests

```
python -m pytest backend/tests -q                                  # unit + API tests
cd e2e && npm install && npx playwright install chromium && npm test   # Playwright
wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh after          # mutation tests (mutmut)
```

## Project layout

```
backend/
  src/invoice_app/domain   business rules (approval_policy.py, approval_service.py)
  src/invoice_app/api      routers, sign-in, web UI (wwwroot)
  tests                    pytest tests
e2e/                       Playwright test + page objects
specs/                     Spec Kit specification, plan, tasks
docs/                      use cases, mutation reports, PR review
scripts/                   mutation test helpers (run in WSL/Linux)
.claude/                   project agents, skills and logging hooks
logs/ai-interactions.jsonl AI interaction log
AGENTS.md                  conventions for AI coding agents
ASSIGNMENT.md              assignment write-up
```

## Documentation (PDF)

The full documentation set is built as PDFs in [docs/pdf](docs/pdf): one separate PDF per document (23 in total, including architecture diagrams, a reviewer guide and a UI walkthrough). Sources are Markdown in `docs/guides` and the spec files; rebuild with `pip install -e "backend[docs]" && python scripts/build_docs.py`.

Two slide decks (PowerPoint and PDF) are in [docs/presentations](docs/presentations): the reviewer walkthrough of the whole project and a screen-by-screen UI walkthrough.

## Use cases

- [UC-1 Bulk invoice approval](docs/use-cases/UC-1-bulk-approval.md)
- [UC-2 Partial approval](docs/use-cases/UC-2-partial-approval.md)
