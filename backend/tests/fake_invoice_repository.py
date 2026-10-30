"""A test double for the invoice repository that behaves like the real one."""

import copy
from typing import Iterable, Optional

from invoice_app.domain.errors import InvoiceNotFoundError
from invoice_app.domain.invoice import Invoice


class FakeInvoiceRepository:
    """In-memory repository for unit tests.

    It must be as strict as the real store, otherwise tests could pass for the wrong reason: ``update`` records
    every save in ``updated`` (so a test can prove a refused attempt saved nothing) and raises for an unknown id.
    ``tests/test_repository_contract.py`` checks it against the same contract as the in-memory repository.
    """

    def __init__(self, *seed: Invoice) -> None:
        """Create the FakeInvoiceRepository.

        Args:
            *seed: Invoices to start with.
        """
        self._invoices: list[Invoice] = list(seed)
        self.updated: list[Invoice] = []

    def get_all(self) -> list[Invoice]:
        """Return a snapshot list of every invoice."""
        return list(self._invoices)

    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Return the invoice with this id, or ``None``."""
        return next((invoice for invoice in self._invoices if invoice.id == invoice_id), None)

    def get_by_ids(self, invoice_ids: Iterable[str]) -> list[Invoice]:
        """Return the invoices whose ids are listed; unknown ids are ignored."""
        wanted = set(invoice_ids)
        return [invoice for invoice in self._invoices if invoice.id in wanted]

    def add(self, invoice: Invoice) -> Invoice:
        """Like the real repository: an invoice without an id is given one."""
        if not invoice.id:
            invoice.id = f"INV-FAKE-{len(self._invoices) + 1}"
        self._invoices.append(invoice)
        return invoice

    def update(self, invoice: Invoice) -> None:
        """Records every update and replaces the stored invoice, like a real repository would."""
        self.updated.append(copy.deepcopy(invoice))
        for index, existing in enumerate(self._invoices):
            if existing.id == invoice.id:
                self._invoices[index] = invoice
                return
        raise InvoiceNotFoundError(f"Invoice {invoice.id} was not found.")

    def remove(self, invoice_id: str) -> bool:
        """Delete the invoice; return whether anything was removed."""
        before = len(self._invoices)
        self._invoices = [invoice for invoice in self._invoices if invoice.id != invoice_id]
        return len(self._invoices) < before
