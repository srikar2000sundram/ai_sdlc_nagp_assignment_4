---
name: approval-rules
description: The invoice approval limit rules (Manager 50,000, Director 500,000, two distinct approvers above that), with boundary table and where each rule lives. Load before writing or reviewing anything that touches approvals.
---

# Approval rules

| Amount | Who may approve | Approvals needed |
| --- | --- | --- |
| ≤ 50,000.00 | Manager or Director | 1 |
| 50,000.01 – 500,000.00 | Director only | 1 |
| > 500,000.00 | first: Manager or Director; second: **Director** | 2, from two different users |

Rules that are easy to get wrong:
- Limits are **inclusive**. 50,000.00 is fine for a Manager; 50,000.01 is not. 500,000.00 needs one Director; 500,000.01 needs two approvers.
- Same user = same username after `strip().casefold()`. `Dir.One` and ` dir.one ` are one person.
- When the same user tries twice, report the duplicate-user reason (it wins over the role reason).
- Only `Manager` and `Director` roles can approve. `Admin` can reject and delete, never approve.
- A refused attempt returns a clear reason (HTTP 403 `{"error": ...}`) and changes **nothing**: check everything first, mutate after.
- The invoice stays `PendingApproval` after the first of two approvals; `decided_by`/`decided_at` are set only by the final approval.

Where things live:
- Pure rules: `backend/src/invoice_app/domain/approval_policy.py` (`rejection_reason`, `required_approvals`, `is_same_user`)
- Orchestration and state change: `backend/src/invoice_app/domain/approval_service.py`
- HTTP mapping (403): `backend/src/invoice_app/api/main.py` and `api/routers/approvals.py`
- Full spec: `specs/001-invoice-approval-limits/spec.md`
