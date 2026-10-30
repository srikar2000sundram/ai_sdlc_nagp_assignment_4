"""The approval workflow: submit, approve and reject an invoice."""

import threading
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional, Protocol, Sequence

from .approval import ApprovalRecord, Approver
from .approval_policy import standard_policy
from .errors import ApprovalNotPermittedError, DomainValidationError, InvalidStateError, InvoiceNotFoundError
from .invoice import Invoice, utc_now
from .invoice_status import InvoiceStatus
from .repository import ApprovalStore


class ApprovalDecisions(Protocol):
    """What the service needs to know from the rules: may this approval happen, and how many are required."""

    def refusal_reason(
        self, amount: Decimal, approver: Approver, prior_approvals: Sequence[ApprovalRecord]
    ) -> Optional[str]:
        """Return why this approval is not allowed, or ``None`` when it is."""

    def required_approvals(self, amount: Decimal) -> int:
        """Return how many distinct approvals an invoice of this amount needs."""


class ApprovalService:
    """Moves an invoice through its lifecycle: Draft -> PendingApproval -> Approved or Rejected.

    The service coordinates; it does not own the limits. Who may approve is decided by the injected policy, and
    time comes from the injected clock, so both can be replaced without touching this class.
    """

    def __init__(
        self,
        store: ApprovalStore,
        policy: Optional[ApprovalDecisions] = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """Args:
            store: Finds and saves invoices (only those two operations are needed).
            policy: Decides who may approve and how many approvals are required. Defaults to the standard rules.
            clock: Returns the current time; replace it in tests to control timestamps.
        """
        self._store = store
        self._policy = policy if policy is not None else standard_policy()
        self._clock = clock
        # Check-then-mutate must be atomic. Without it two simultaneous requests from the same user can
        # both pass the "already approved" check (PR review finding F1). One lock is enough for this
        # in-memory app; a database-backed repository would use a row lock or optimistic version instead.
        self._lock = threading.Lock()

    def submit(self, invoice_id: str) -> Invoice:
        """Move a Draft invoice to PendingApproval.

        Raises:
            InvoiceNotFoundError: unknown id.
            InvalidStateError: the invoice is not a Draft.
        """
        with self._lock:
            invoice = self._find(invoice_id)

            if invoice.status != InvoiceStatus.DRAFT:
                raise InvalidStateError(
                    f"Invoice {invoice_id} is {invoice.status.value}; only drafts can be submitted."
                )

            invoice.status = InvoiceStatus.PENDING_APPROVAL
            self._store.update(invoice)
            return invoice

    def approve(self, invoice_id: str, approver: Approver) -> Invoice:
        """Record one approval; mark the invoice Approved when enough have been given.

        All checks (state, then the policy) run before anything is changed, so a refused attempt leaves the
        invoice exactly as it was.

        Raises:
            InvoiceNotFoundError: unknown id.
            InvalidStateError: the invoice is not pending.
            ApprovalNotPermittedError: the policy refuses this approver; the message is the reason.
        """
        with self._lock:
            invoice = self._find(invoice_id)
            self._ensure_pending(invoice)

            # Every check happens before the first mutation, so a refused attempt changes nothing.
            reason = self._policy.refusal_reason(invoice.amount, approver, invoice.approvals)
            if reason is not None:
                raise ApprovalNotPermittedError(reason)

            now = self._clock()
            # Assign a new list instead of appending in place: the invoice only changes after every check has passed.
            invoice.approvals = [*invoice.approvals, ApprovalRecord(approver.username, approver.role, now)]

            if len(invoice.approvals) >= self._policy.required_approvals(invoice.amount):
                invoice.status = InvoiceStatus.APPROVED
                invoice.decided_by = approver.username
                invoice.decided_at = now

            self._store.update(invoice)
            return invoice

    def reject(self, invoice_id: str, approver: str, reason: str) -> Invoice:
        """Reject a pending invoice. A reason is required.

        Raises:
            DomainValidationError: the reason is blank.
            InvoiceNotFoundError: unknown id.
            InvalidStateError: the invoice is not pending.
        """
        if not reason or not reason.strip():
            raise DomainValidationError("A reason is required to reject an invoice.")

        with self._lock:
            invoice = self._find(invoice_id)
            self._ensure_pending(invoice)

            invoice.status = InvoiceStatus.REJECTED
            invoice.decided_by = approver
            invoice.decided_at = self._clock()
            invoice.decision_note = reason
            self._store.update(invoice)
            return invoice

    def required_approvals(self, amount: Decimal) -> int:
        """Exposed so the API can show "N of M approvals" using the same policy the service enforces."""
        return self._policy.required_approvals(amount)

    def _find(self, invoice_id: str) -> Invoice:
        """Return the invoice or raise ``InvoiceNotFoundError`` naming the id."""
        invoice = self._store.get_by_id(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} was not found.")
        return invoice

    @staticmethod
    def _ensure_pending(invoice: Invoice) -> None:
        """Raise ``InvalidStateError`` unless the invoice is waiting for a decision."""
        if invoice.status != InvoiceStatus.PENDING_APPROVAL:
            raise InvalidStateError(
                f"Invoice {invoice.id} is {invoice.status.value}; only pending invoices can be decided."
            )
