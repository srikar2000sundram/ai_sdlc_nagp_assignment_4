"""Storage contracts, split by who needs what (interface segregation).

A consumer depends on the smallest contract that covers its needs: the approval service needs `ApprovalStore`
(find one invoice, save it), read-only endpoints need `InvoiceReader`, create and delete need `InvoiceWriter`.
`InvoiceRepository` is the full contract an implementation offers.
"""

from typing import Iterable, Optional, Protocol

from .invoice import Invoice


class InvoiceReader(Protocol):
    """Read-only access to invoices."""

    def get_all(self) -> list[Invoice]:
        """Return every invoice. The list is a snapshot: changing it does not change the store."""

    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Return the invoice with this id, or ``None`` when there is none (not an error)."""

    def get_by_ids(self, invoice_ids: Iterable[str]) -> list[Invoice]:
        """Return the invoices that exist among these ids; unknown ids are ignored."""


class InvoiceWriter(Protocol):
    """Operations that change what is stored."""

    def add(self, invoice: Invoice) -> Invoice:
        """Store a new invoice and return it. An invoice without an id is given one."""

    def update(self, invoice: Invoice) -> None:
        """Replace the stored invoice that has the same id.

        Raises:
            InvoiceNotFoundError: if no such invoice exists (never a silent no-op).
        """

    def remove(self, invoice_id: str) -> bool:
        """Delete the invoice; return ``True`` if something was removed, ``False`` if the id was unknown."""


class ApprovalStore(Protocol):
    """All the approval service needs from storage."""

    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Return the invoice with this id, or ``None``."""

    def update(self, invoice: Invoice) -> None:
        """Save the invoice. Raises ``InvoiceNotFoundError`` when it does not exist."""


class InvoiceRepository(InvoiceReader, InvoiceWriter, Protocol):
    """The full repository contract implemented by the in-memory store (and by test fakes)."""
