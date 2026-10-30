"""The Invoice entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .approval import ApprovalRecord
from .invoice_status import InvoiceStatus


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    This is the domain's default clock. Services accept another clock so tests can control time.
    """
    return datetime.now(timezone.utc)


@dataclass
class Invoice:
    """An invoice moving through approval.

    Attributes:
        id: Invoice number such as ``INV-1001``; assigned by the repository when empty.
        customer_name: Who is being billed.
        amount: Money as ``Decimal`` (never ``float``) so limit comparisons are exact.
        status: Current lifecycle state.
        created_at: When the invoice was created (UTC).
        decided_by: Username of the person whose action made the final decision, if decided.
        decided_at: When the final decision was made (UTC).
        decision_note: The reason, for a rejection.
        approvals: Accepted approvals so far, oldest first. Above the Director limit two are needed.
    """

    id: str = ""
    customer_name: str = ""
    amount: Decimal = Decimal("0")
    status: InvoiceStatus = InvoiceStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_note: Optional[str] = None
    approvals: list[ApprovalRecord] = field(default_factory=list)
