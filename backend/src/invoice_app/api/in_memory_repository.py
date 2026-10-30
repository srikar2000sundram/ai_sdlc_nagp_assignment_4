"""The in-memory invoice store used by the demo app: no database, resets on restart."""

import threading
from datetime import timedelta
from decimal import Decimal
from typing import Iterable, Optional

from invoice_app.domain.errors import InvoiceNotFoundError
from invoice_app.domain.invoice import Invoice, utc_now
from invoice_app.domain.invoice_status import InvoiceStatus


class InMemoryInvoiceRepository:
    """In-memory store so the demo app runs with no database. Seeded with a few invoices."""

    def __init__(self) -> None:
        """Create the store seeded with demo invoices, including INV-2001 (75,000.00) and INV-2002 (600,000.00) for
        trying the approval limits.
        """
        # One lock guards the list so concurrent requests cannot corrupt it.
        self._lock = threading.Lock()
        # INV-1001 to INV-1005 and INV-2001/2002 are seeded below, so new invoices continue from 1006.
        self._next_number = 1006
        self._invoices: list[Invoice] = [
            Invoice("INV-1001", "Lakeside School District", Decimal("4250.00"), InvoiceStatus.PENDING_APPROVAL),
            Invoice("INV-1002", "Hilltop Academy", Decimal("980.50"), InvoiceStatus.PENDING_APPROVAL),
            Invoice(
                "INV-1003", "Riverside Charter", Decimal("12300.00"), InvoiceStatus.APPROVED,
                decided_by="demo.manager", decided_at=utc_now() - timedelta(days=2),
            ),
            Invoice("INV-1004", "Oakwood Independent", Decimal("615.75"), InvoiceStatus.PENDING_APPROVAL),
            Invoice("INV-1005", "Maple Grove Prep", Decimal("310.00"), InvoiceStatus.DRAFT),
            # INV-2001 and INV-2002 exist to try the approval limits by hand: 75,000.00 needs a Director; 600,000.00 needs two approvers.
            Invoice("INV-2001", "Summit Unified District", Decimal("75000.00"), InvoiceStatus.PENDING_APPROVAL),
            Invoice("INV-2002", "Ridgeview Education Consortium", Decimal("600000.00"), InvoiceStatus.PENDING_APPROVAL),
        ]

    def get_all(self) -> list[Invoice]:
        """Return a snapshot list of every invoice."""
        with self._lock:
            # A copy, so callers cannot change the store by editing the list they were given.
            return list(self._invoices)

    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Return the invoice with this id, or ``None``."""
        with self._lock:
            return next((invoice for invoice in self._invoices if invoice.id == invoice_id), None)

    def get_by_ids(self, invoice_ids: Iterable[str]) -> list[Invoice]:
        """Return the invoices whose ids are in the given collection; unknown ids are ignored."""
        wanted = set(invoice_ids)
        with self._lock:
            return [invoice for invoice in self._invoices if invoice.id in wanted]

    def add(self, invoice: Invoice) -> Invoice:
        """Store the invoice, giving it the next ``INV-<n>`` id when it has none."""
        with self._lock:
            if not invoice.id:
                invoice.id = f"INV-{self._next_number}"
                self._next_number += 1
            self._invoices.append(invoice)
            return invoice

    def update(self, invoice: Invoice) -> None:
        """Replace the stored invoice with the same id; raise ``InvoiceNotFoundError`` if there is none."""
        with self._lock:
            for index, existing in enumerate(self._invoices):
                if existing.id == invoice.id:
                    self._invoices[index] = invoice
                    return
            # Never a silent no-op: approving a deleted invoice must not look like success (review finding F6).
            raise InvoiceNotFoundError(f"Invoice {invoice.id} was not found.")

    def remove(self, invoice_id: str) -> bool:
        """Delete the invoice; return whether anything was removed."""
        with self._lock:
            before = len(self._invoices)
            self._invoices = [invoice for invoice in self._invoices if invoice.id != invoice_id]
            return len(self._invoices) < before
