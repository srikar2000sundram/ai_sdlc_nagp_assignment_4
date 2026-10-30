# Contributing

How to change this project safely. The rules for AI agents are in `AGENTS.md`; this file is the same advice for people.

## Set up

```text
pip install -e "backend[dev]"
cd e2e && npm install && npx playwright install chromium && cd ..
```

## Before you change anything

1. Read the rules table in `AGENTS.md` and the spec in `specs/001-invoice-approval-limits/spec.md`.
2. Run the checks once so you know they are green: `python -m pytest backend/tests -q` and `python scripts/try_all_cases.py`.

## Making a change

1. **Write the test first.** For a rule: a policy test, a service test using `assert_refused_and_unchanged`, and an API test.
2. **Put business rules in `domain/`.** Never in routers or `main.py`.
3. **Follow SOLID** (`docs/guides/19-solid-design.md`): add a new rule as a **new class** in `approval_policy.py` and list it in `standard_policy()`; depend on the smallest storage contract you need; pass collaborators in instead of importing concrete classes.
4. **Document as you go:** a docstring on every new module, class and function; a comment where the reason is not obvious from the code.
5. **Money is `Decimal`, never `float`.** All checks run before the first mutation, so a refused attempt changes nothing.
6. Run everything:

```text
python -m pytest backend/tests -q
python scripts/try_all_cases.py
wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh check   # then delete docs/mutation/check.txt
cd e2e && npm test
```

Triage every surviving mutant: add a test, or record why it is equivalent.

## Commits and pull requests

- Small steps, each commit standing alone, with a message that says **what changed and why**.
- In the pull request, give every review finding exactly one verdict: **fixed** (say how), **dismissed** (give a reason) or **deferred** (give a reason and where it is tracked). Format: `.claude/skills/review-findings/SKILL.md`.

## Never

- Commit real credentials, tokens or customer data. The demo accounts are local and labelled as demo.
- Add business logic to `main.py`, `error_handling.py` or a router.
- Edit an existing rule class to add a different rule; add a new class.
- Mutate an invoice before every approval check has passed.
