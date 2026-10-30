"""One contract, every repository. Anything that claims to be an InvoiceRepository must pass these tests,
so the fake used in unit tests and the in-memory store used by the app are interchangeable (Liskov)."""

from decimal import Decimal

import pytest

from fake_invoice_repository import FakeInvoiceRepository
from invoice_app.api.in_memory_repository import InMemoryInvoiceRepository
from invoice_app.domain.errors import InvoiceNotFoundError
from invoice_app.domain.invoice import Invoice
from invoice_app.domain.invoice_status import InvoiceStatus


@pytest.fixture(params=[FakeInvoiceRepository, InMemoryInvoiceRepository], ids=["fake", "in-memory"])
def repository(request):
    """Each test runs once per repository implementation."""
    return request.param()


def invoice(invoice_id: str = "CONTRACT-1", amount: str = "10") -> Invoice:
    """Build an invoice for contract tests."""
    return Invoice(id=invoice_id, customer_name="Contract School", amount=Decimal(amount))


def test_an_unknown_id_is_none_not_an_error(repository):
    assert repository.get_by_id("NOPE-1") is None


def test_an_added_invoice_can_be_found_again_with_its_id(repository):
    added = repository.add(invoice("CONTRACT-1"))

    assert added.id == "CONTRACT-1"
    assert repository.get_by_id("CONTRACT-1") is added


def test_an_invoice_added_without_an_id_is_given_one(repository):
    added = repository.add(Invoice(customer_name="No id yet", amount=Decimal("5")))

    assert added.id
    assert repository.get_by_id(added.id) is added


def test_get_all_includes_added_invoices_and_returns_a_snapshot(repository):
    before = len(repository.get_all())
    repository.add(invoice("CONTRACT-1"))

    listing = repository.get_all()
    assert len(listing) == before + 1
    listing.clear()

    assert len(repository.get_all()) == before + 1


def test_get_by_ids_returns_the_ones_that_exist_and_ignores_the_rest(repository):
    repository.add(invoice("CONTRACT-1"))
    repository.add(invoice("CONTRACT-2"))

    found = repository.get_by_ids(["CONTRACT-1", "CONTRACT-2", "NOPE-1"])

    assert {item.id for item in found} == {"CONTRACT-1", "CONTRACT-2"}


def test_update_replaces_what_is_stored(repository):
    repository.add(invoice("CONTRACT-1"))
    changed = invoice("CONTRACT-1", "99")
    changed.status = InvoiceStatus.PENDING_APPROVAL

    repository.update(changed)

    assert repository.get_by_id("CONTRACT-1") is changed


def test_update_of_an_unknown_invoice_is_an_error_not_a_silent_no_op(repository):
    with pytest.raises(InvoiceNotFoundError):
        repository.update(invoice("NOPE-1"))


def test_remove_says_whether_anything_was_removed(repository):
    repository.add(invoice("CONTRACT-1"))

    assert repository.remove("CONTRACT-1") is True
    assert repository.get_by_id("CONTRACT-1") is None
    assert repository.remove("CONTRACT-1") is False
