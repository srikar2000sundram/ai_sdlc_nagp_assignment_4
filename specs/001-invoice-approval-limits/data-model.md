# Data Model

## Approver (value object, not stored)
- `username: str` (non-blank)
- `role: str` (`Manager`, `Director`; anything else cannot approve)

## ApprovalRecord (value object, stored on the invoice)
- `username: str`
- `role: str`
- `approved_at: datetime` (UTC)

## Invoice (changed)
Existing fields plus `approvals: list[ApprovalRecord]` (ordered, oldest first).

Derived: `required_approvals = 2 if amount > 500000 else 1`.

## State transitions

```
Draft --submit--> PendingApproval --approve (count < required)--> PendingApproval
                                   --approve (count == required)--> Approved
                                   --reject(reason)--> Rejected
```

A refused approval is not a transition: no field changes.

## Limits

| Constant | Value |
| --- | --- |
| `MANAGER_LIMIT` | 50000 |
| `DIRECTOR_LIMIT` | 500000 |
