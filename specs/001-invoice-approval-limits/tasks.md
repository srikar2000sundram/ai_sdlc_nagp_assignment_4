---

description: "Task list for approval limits by role"
---

# Tasks: Approval Limits by Role

**Input**: Design documents from `/specs/001-invoice-approval-limits/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (constitution principle II).

## Format: `[ID] [P?] [Story] Description`

## Phase 0: Baseline (Python port, behaviour-identical)

- [X] T001 Port Domain, Api and tests of the C# demo app to `backend/src/invoice_app` and `backend/tests`; 7 original tests pass as pytest
- [X] T002 [P] Record baseline mutation score (`docs/mutation/baseline.txt`)

## Phase 1: Foundational

- [X] T003 [P] `ApprovalNotPermittedError` in `backend/src/invoice_app/domain/errors.py`; map to 403 in `api/main.py`
- [X] T004 [P] `Approver` and `ApprovalRecord` in `backend/src/invoice_app/domain/approval.py`
- [X] T005 `Invoice.approvals` list in `domain/invoice.py`
- [X] T006 Demo accounts `demo.manager`, `demo.director`, `demo.director2` in `api/auth/demo_users.py`; router allows Manager/Director/Admin
- [X] T007 Seed `INV-2001` (75,000.00) and `INV-2002` (600,000.00) in `api/in_memory_repository.py`

## Phase 2: User Story 1 - Single-approver limits (P1) — implementation step 1

- [X] T008 [US1] Tests first: Manager at 50,000.00 ok, at 50,000.01 refused; Director at 500,000.00 ok; Admin refused; each refusal asserts reason + invoice unchanged (`tests/test_approval_policy.py`, `tests/test_approval_service.py`)
- [X] T009 [US1] `approval_policy.rejection_reason` single-approver branch + `required_approvals`
- [X] T010 [US1] `ApprovalService.approve(invoice_id, approver)` checks the policy before any mutation and records an `ApprovalRecord`
- [X] T011 [US1] API tests for 403 + reason and unchanged invoice (`tests/test_api.py`)

## Phase 3: User Story 2 - Two distinct approvers above 500,000 (P1) — implementation step 2

- [X] T012 [US2] Tests first: first approval keeps Pending; same user (incl. case/whitespace) refused; Manager as second refused; distinct Director completes; refused attempt leaves exactly one approval
- [X] T013 [US2] Extend `rejection_reason` with the duplicate-user and second-must-be-Director rules; `is_same_user` normalisation
- [X] T014 [US2] Service marks Approved only when `len(approvals) >= required_approvals(amount)`; `decided_by`/`decided_at` set on the final approval
- [X] T015 [US2] Serialize `approvals` and `requiredApprovals` in `api/serialization.py`

## Phase 4: User Story 3 - Refusal visible in the UI (P2)

- [X] T016 [US3] Show "N of M approvals" in `wwwroot/app.js`
- [X] T017 [US3] Playwright page objects `e2e/pages/*.ts` and test `e2e/tests/over-limit-rejection.spec.ts`

## Phase 5: Polish & evidence

- [X] T018 Run `test-reviewer` agent over generated tests; close gaps (non-persisting fake repository, unasserted messages and timestamps)
- [X] T019 Run mutmut again (`docs/mutation/after.txt`); triage survivors
- [X] T020 Update `AGENTS.md`, README, CI to Python
- [X] T021 Review the diff with `pr-reviewer`; record verdicts (`docs/pr-review.md`)
- [X] T021a Fix review findings F1-F3, F5, F6, F8 (atomic approvals, amount validation, `DomainValidationError`, strict `update`); tests written to fail without the fixes
- [ ] T022 Record the demo video and add its link to `ASSIGNMENT.md`
- [ ] T023 Commit in steps, push to the fork, open the PR with `docs/pr-review.md` as the description
- [ ] T024 (deferred F7) Second Playwright spec for the two-Director flow, with a reset endpoint so mutating UI tests are repeatable
- [ ] T025 (deferred F11) Session expiry and constant-time password comparison

## Dependencies

Phase 1 blocks Phases 2-3. Phase 3 builds on Phase 2. Phase 4 needs the API shape from Phase 3.
