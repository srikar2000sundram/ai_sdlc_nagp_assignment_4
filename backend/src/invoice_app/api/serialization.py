"""Turns an Invoice into the JSON shape the web UI consumes."""

from invoice_app.domain.invoice import Invoice


def invoice_to_json(invoice: Invoice, required_approvals: int) -> dict:
    """Same camelCase shape the web UI has always consumed."""
    return {
        "id": invoice.id,
        "customerName": invoice.customer_name,
        # float is safe for display: amounts are limited to 12 integer digits and 2 decimals, which a double holds exactly (review finding F4).
        "amount": float(invoice.amount),
        "status": invoice.status.value,
        "createdAt": invoice.created_at.isoformat(),
        "decidedBy": invoice.decided_by,
        "decidedAt": invoice.decided_at.isoformat() if invoice.decided_at else None,
        "decisionNote": invoice.decision_note,
        # Passed in from the policy that is actually enforced, so what the UI shows and what the rules demand cannot disagree.
        "requiredApprovals": required_approvals,
        # One entry per accepted approval, oldest first.
        "approvals": [
            {"username": a.username, "role": a.role, "approvedAt": a.approved_at.isoformat()}
            for a in invoice.approvals
        ],
    }
