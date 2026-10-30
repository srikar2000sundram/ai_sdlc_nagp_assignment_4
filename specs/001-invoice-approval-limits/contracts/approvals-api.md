# Contract: `POST /api/approvals/{invoiceId}/approve`

Auth: bearer token. Allowed session roles at the router: `Manager`, `Director`, `Admin` (Admin is then refused by the domain with a reason).

| Outcome | Status | Body |
| --- | --- | --- |
| Approval recorded, more approvals needed | 200 | invoice JSON, `status: "PendingApproval"`, `approvals` has 1 entry, `requiredApprovals: 2` |
| Approval recorded, invoice complete | 200 | invoice JSON, `status: "Approved"`, `decidedBy` = final approver |
| Approver not allowed by the rules | 403 | `{"error": "<reason>"}`; invoice unchanged |
| Invoice not pending | 409 | `{"error": "Invoice INV-x is Approved; only pending invoices can be decided."}` |
| Unknown invoice | 404 | `{"error": "Invoice INV-x was not found."}` |
| No/invalid token | 401 | empty |

## Invoice JSON additions

```json
{
  "requiredApprovals": 2,
  "approvals": [
    { "username": "demo.director", "role": "Director", "approvedAt": "2026-10-16T10:00:00+00:00" }
  ]
}
```

## Reason texts (asserted in tests)

- `Role {role} is not allowed to approve invoices.`
- `A Manager may approve invoices up to 50,000.00; this invoice is {amount} and needs a Director.`
- `{username} has already approved this invoice; invoices above 500,000.00 need two different approvers.`
- `The second approver on an invoice above 500,000.00 must be a Director; {username} is a {role}.`
