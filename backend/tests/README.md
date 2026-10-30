# backend/tests

pytest tests for the backend. Run from the repository root: `python -m pytest backend/tests -q`.

| File | What it tests | Style |
| --- | --- | --- |
| `test_approval_policy.py` | The pure rules: limits, boundaries one cent either side, roles, the two negative rules, each rule class on its own, plugging in a new rule | Unit |
| `test_approval_service.py` | The workflow against a fake repository: lifecycle, that a refused attempt changes nothing, state errors, concurrency, injected policy, clock and store | Unit |
| `test_repository_contract.py` | One contract run against both the fake and the in-memory repository, so they are interchangeable | Contract |
| `test_api.py` | Status codes, messages, sign-in, validation and the approval flow through the real routers | Integration |
| `fake_invoice_repository.py` | The shared fake (not a test). Records every save and raises for unknown ids, like the real store | Support |

## Conventions

- One test module per module under test, named `test_<module>.py`.
- Test names are sentences that say the behaviour, for example `test_a_manager_as_second_approver_is_refused_and_nothing_changes`.
- **Every refusal test asserts three things:** the exact reason text, that the invoice equals a deep copy taken before, and that the repository saw no save. The shared helper is `assert_refused_and_unchanged` in `test_approval_service.py`.
- Boundaries are tested one cent either side of every limit (50,000.00 / 50,000.01 / 500,000.00 / 500,000.01).
- A test must be able to fail. Judge the tests by mutation score, not line coverage: `wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh <label>`.
- Concurrency tests use `SnapshotRepository` (snapshot reads, delayed saves). Against a live-object repository they would pass even without the lock.

## Adding a test

1. Write it first and watch it fail.
2. Use `FakeInvoiceRepository` and the helpers in the module you are extending.
3. For a new rule: a policy test, a service test with `assert_refused_and_unchanged`, and an API test for the status and message.
