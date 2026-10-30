# Implementation Plan: Approval Limits by Role

**Branch**: `001-invoice-approval-limits` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-invoice-approval-limits/spec.md`

## Summary

Add a pure `approval_policy` module to the domain layer that decides, from an invoice amount, the approver and earlier approvals, whether an approval is allowed and why not. `ApprovalService.approve` calls it before mutating anything, records an `ApprovalRecord`, and only marks the invoice Approved once the required number of approvals is reached. The API maps the new `ApprovalNotPermittedError` to HTTP 403 with the reason. The UI shows approval progress.

## Technical Context

**Language/Version**: Python 3.10+ (developed on 3.13; mutation runs on 3.10 in WSL)

**Primary Dependencies**: FastAPI, uvicorn; dev: pytest, httpx, mutmut

**Storage**: In-memory repository (unchanged)

**Testing**: pytest (unit + API), mutmut (mutation), Playwright (one e2e)

**Target Platform**: Local dev server, Windows/Linux

**Project Type**: web-service with a static UI

**Performance Goals**: N/A (demo app)

**Constraints**: Domain stays free of web/storage code; refused attempts must be side-effect free

**Scale/Scope**: One service method, one policy module, one error type, one UI line

## Constitution Check

| Principle | Status |
| --- | --- |
| I. Rules in domain | Pass: `approval_policy.py` + `approval_service.py`; router only maps errors |
| II. Negative tests assert unchanged invoice | Pass: shared `assert_refused_and_unchanged` helper in service tests |
| III. Boundaries both sides | Pass: parametrized limits at ±0.01 |
| IV. Refusals explain themselves | Pass: reasons asserted verbatim |
| V. Mutation evidence | Pass: before/after in `docs/mutation/` |
| VI. Small steps | Pass: two implementation steps (single-approver, then two-approver), see tasks |

## Project Structure

### Documentation (this feature)

```text
specs/001-invoice-approval-limits/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/approvals-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── src/invoice_app/
│   ├── domain/
│   │   ├── approval.py            # Approver, ApprovalRecord (new)
│   │   ├── approval_policy.py     # pure limits + two-approver rules (new)
│   │   ├── approval_service.py    # approve() uses the policy, records approvals (changed)
│   │   ├── errors.py              # + ApprovalNotPermittedError (changed)
│   │   └── invoice.py             # + approvals list (changed)
│   └── api/
│       ├── auth/demo_users.py     # + Manager, Director accounts (changed)
│       ├── main.py                # 403 mapping (changed)
│       ├── routers/approvals.py   # passes Approver(username, role) (changed)
│       ├── serialization.py       # + approvals, requiredApprovals (changed)
│       └── wwwroot/app.js         # "1 of 2 approvals" (changed)
└── tests/
    ├── test_approval_policy.py    # pure rule tests (new)
    ├── test_approval_service.py   # service + unchanged-on-refusal tests (changed)
    └── test_api.py                # HTTP-level 403 / two-approver flow (changed)
e2e/
├── pages/{LoginPage,ApprovalsPage}.ts
└── tests/over-limit-rejection.spec.ts
```

**Structure Decision**: keep the existing Domain / Api / Tests layering of the original C# solution, ported to Python packages.

## Complexity Tracking

No constitution violations.
