# Invoice Approval Demo App Constitution

## Core Principles

### I. Business Rules Live in the Domain Layer
Every approval rule is implemented in `backend/src/invoice_app/domain/` and nowhere else. Routers translate HTTP to domain calls and domain errors to status codes; they never decide anything. `main.py` wiring contains no business logic.

### II. Test-First for Rules, With Negative Cases (NON-NEGOTIABLE)
Every rule ships with tests written before or with the code. Each "may not" rule has a negative test that proves two things: the attempt is refused with a clear reason, **and the invoice is byte-for-byte unchanged afterwards**. A positive-path test alone never counts as covering a rule.

### III. Boundaries Are Tested On Both Sides
For each numeric limit, tests cover the value at the limit, one cent above and one cent below. Limits are `Decimal`, never `float`.

### IV. Refusals Explain Themselves
A refused action returns a human-readable reason that names the rule and the actor. Reasons are asserted in tests, so wording changes are deliberate.

### V. Mutation Score Is Evidence, Not a Target
Unit tests are judged by `mutmut` on the domain package. Surviving mutants are triaged: close the gap with a test, or record why the mutant is equivalent or cosmetic.

### VI. Small, Reviewable Steps
Features land in independent steps, each with its own tests and commit message that says what changed and why. Every review finding on a PR gets a verdict: fixed, dismissed with a reason, or deferred with a reason.

## Additional Constraints

- Stack: Python 3.10+, FastAPI, pytest, Playwright for end-to-end. In-memory storage only.
- End-to-end tests use page objects and role-based locators (`getByRole`, `getByLabel`), never CSS or XPath.
- Never commit real credentials. Demo accounts are local and documented as such.

## Development Workflow

Spec (Spec Kit) → plan → tasks → implement in steps → unit tests reviewed by the `test-reviewer` agent → mutation run → e2e → PR reviewed by the `pr-reviewer` agent. All AI interactions are logged to `logs/ai-interactions.jsonl` by project hooks.

## Governance

This constitution supersedes ad-hoc preferences. Amendments are made in a commit that states what changed and why. `AGENTS.md` is the runtime guidance file for agents and must stay consistent with this document.

**Version**: 1.0.0 | **Ratified**: 2026-10-16 | **Last Amended**: 2026-10-16
