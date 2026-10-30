# Changelog

All notable changes, newest first.

## Unreleased: design and documentation

- Architecture diagrams (system, request sequence, rule decision flow, approval bands, invoice lifecycle, AI workflow, test layers) drawn from the code by `scripts/make_diagrams.py`; a reviewer guide; a UI walkthrough with cropped screenshots (`scripts/ui_screens.py`); two slide decks as PowerPoint and PDF (`scripts/make_decks.py`).

- Refactored to follow SOLID with no change in behaviour: one class per approval rule combined by `ApprovalPolicy`; small storage contracts (`ApprovalStore`, `InvoiceReader`, `InvoiceWriter`); policy, clock, store and user directory injected; `main.py` split into `main.py`, `error_handling.py` and `auth/middleware.py`.
- Added tests for the design: plugging in a new rule, injected limits, policy, clock and store, a repository contract run against both repositories, and per-rule boundaries. 177 tests, mutation score 100% (132 of 132).
- Documentation at every level: docstrings on every module, class and function; "why" comments; commented web UI, end-to-end tests and configuration; a README for each folder; `CONTRIBUTING.md`; a generated code reference; PDF guides.

## Approval limits by role

- A Manager may approve invoices up to and including 50,000.00; a Director up to and including 500,000.00.
- Above 500,000.00 two different users must approve and the second must be a Director. The same user never counts twice (usernames compared trimmed and case-insensitively).
- A refused approval returns HTTP 403 with a specific reason and changes nothing.
- Invoices expose `requiredApprovals` and `approvals`; the UI shows "N of M approvals".
- New demo accounts `demo.manager`, `demo.director`, `demo.director2`; seed invoices INV-2001 (75,000.00) and INV-2002 (600,000.00). The old `Approver` role became `Manager`; `Admin` can reject and delete but never approve.
- Review fixes: a lock around approvals (concurrent double approval), validation of invoice amounts, a narrower 400 mapping, a strict repository `update`.

## Python port

- The ASP.NET Core backend became Python/FastAPI with the same layers (domain, api, tests), endpoints and web UI. The seven original tests were ported and kept green.
- Playwright end-to-end setup now starts the Python server.
