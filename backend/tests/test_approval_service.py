import copy
import threading
import time
from decimal import Decimal

import pytest

from fake_invoice_repository import FakeInvoiceRepository
from invoice_app.domain.approval import Approver
from invoice_app.domain.approval_service import ApprovalService
from invoice_app.domain.errors import (
    ApprovalNotPermittedError,
    DomainValidationError,
    InvalidStateError,
    InvoiceNotFoundError,
)
from invoice_app.domain.invoice import Invoice
from invoice_app.domain.invoice_status import InvoiceStatus

MANAGER = Approver("demo.manager", "Manager")
DIRECTOR = Approver("demo.director", "Director")
OTHER_DIRECTOR = Approver("demo.director2", "Director")
OTHER_MANAGER = Approver("manager.two", "Manager")
ADMIN = Approver("demo.admin", "Admin")


def invoice_with(invoice_id: str, status: InvoiceStatus, amount: str = "100") -> Invoice:
    return Invoice(id=invoice_id, customer_name="Test School", amount=Decimal(amount), status=status)


def pending_invoice(amount: str) -> Invoice:
    return invoice_with("INV-1", InvoiceStatus.PENDING_APPROVAL, amount)


def service_for(*invoices: Invoice) -> ApprovalService:
    return ApprovalService(FakeInvoiceRepository(*invoices))


def assert_refused_and_unchanged(service: ApprovalService, invoice: Invoice, approver: Approver) -> str:
    """The shared negative check: the attempt is refused with a reason and NOTHING on the invoice moves."""
    before = copy.deepcopy(invoice)

    with pytest.raises(ApprovalNotPermittedError) as refusal:
        service.approve(invoice.id, approver)

    assert invoice == before, "a refused approval must not change the invoice in any way"
    assert str(refusal.value), "a refused approval must explain why"
    return str(refusal.value)


# --- lifecycle (behaviour that existed before approval limits) -------------------------------------


def test_submit_moves_draft_to_pending_approval():
    invoice = invoice_with("INV-1", InvoiceStatus.DRAFT)

    result = service_for(invoice).submit("INV-1")

    assert result.status == InvoiceStatus.PENDING_APPROVAL


def test_submit_rejects_invoice_that_is_not_a_draft():
    service = service_for(invoice_with("INV-1", InvoiceStatus.APPROVED))

    with pytest.raises(InvalidStateError):
        service.submit("INV-1")


def test_approve_sets_status_approver_and_timestamp():
    service = service_for(invoice_with("INV-1", InvoiceStatus.PENDING_APPROVAL))

    result = service.approve("INV-1", MANAGER)

    assert result.status == InvoiceStatus.APPROVED
    assert result.decided_by == "demo.manager"
    assert result.decided_at is not None


def test_approve_rejects_invoice_that_is_still_a_draft():
    service = service_for(invoice_with("INV-1", InvoiceStatus.DRAFT))

    with pytest.raises(InvalidStateError):
        service.approve("INV-1", MANAGER)


def test_approve_raises_when_invoice_does_not_exist():
    service = service_for()

    with pytest.raises(InvoiceNotFoundError):
        service.approve("INV-404", MANAGER)


def test_approving_an_already_approved_invoice_is_a_state_error_and_changes_nothing():
    invoice = invoice_with("INV-1", InvoiceStatus.PENDING_APPROVAL)
    service = service_for(invoice)
    service.approve("INV-1", MANAGER)
    before = copy.deepcopy(invoice)

    with pytest.raises(InvalidStateError):
        service.approve("INV-1", DIRECTOR)

    assert invoice == before


def test_reject_records_reason_and_approver():
    service = service_for(invoice_with("INV-1", InvoiceStatus.PENDING_APPROVAL))

    result = service.reject("INV-1", "demo.manager", "Duplicate invoice")

    assert result.status == InvoiceStatus.REJECTED
    assert result.decided_by == "demo.manager"
    assert result.decision_note == "Duplicate invoice"
    assert result.decided_at is not None


def test_reject_requires_a_reason():
    invoice = invoice_with("INV-1", InvoiceStatus.PENDING_APPROVAL)
    service = service_for(invoice)

    for blank_reason in ("  ", "", None):
        with pytest.raises(ValueError):
            service.reject("INV-1", "demo.manager", blank_reason)

    assert invoice.status == InvoiceStatus.PENDING_APPROVAL
    assert invoice.decision_note is None


def test_reject_only_applies_to_pending_invoices():
    service = service_for(invoice_with("INV-1", InvoiceStatus.DRAFT))

    with pytest.raises(InvalidStateError):
        service.reject("INV-1", "demo.manager", "No")


# --- step 1: single-approver limits by role ---------------------------------------------------------


def test_manager_approves_an_invoice_at_exactly_the_manager_limit():
    invoice = pending_invoice("50000")

    result = service_for(invoice).approve("INV-1", MANAGER)

    assert result.status == InvoiceStatus.APPROVED
    assert result.decided_by == "demo.manager"
    assert [approval.username for approval in result.approvals] == ["demo.manager"]


def test_manager_is_refused_one_cent_above_the_manager_limit_and_nothing_changes():
    invoice = pending_invoice("50000.01")

    reason = assert_refused_and_unchanged(service_for(invoice), invoice, MANAGER)

    assert reason == "A Manager may approve invoices up to 50,000.00; this invoice is 50,000.01 and needs a Director."
    assert invoice.status == InvoiceStatus.PENDING_APPROVAL
    assert invoice.approvals == []
    assert invoice.decided_by is None and invoice.decided_at is None


def test_director_approves_alone_at_exactly_the_director_limit():
    invoice = pending_invoice("500000")

    result = service_for(invoice).approve("INV-1", DIRECTOR)

    assert result.status == InvoiceStatus.APPROVED
    assert len(result.approvals) == 1


def test_director_approves_alone_between_the_two_limits():
    result = service_for(pending_invoice("75000")).approve("INV-1", DIRECTOR)

    assert result.status == InvoiceStatus.APPROVED


def test_admin_cannot_approve_even_a_small_invoice_and_nothing_changes():
    invoice = pending_invoice("10")

    reason = assert_refused_and_unchanged(service_for(invoice), invoice, ADMIN)

    assert reason == "Role Admin is not allowed to approve invoices."


# --- step 2: two approvers above the director limit ---------------------------------------------------


# --- persistence, timestamps and user-facing messages ------------------------------------------------------


def repository_and_service(*invoices: Invoice) -> tuple[FakeInvoiceRepository, ApprovalService]:
    repository = FakeInvoiceRepository(*invoices)
    return repository, ApprovalService(repository)


def test_submit_persists_the_invoice():
    repository, service = repository_and_service(invoice_with("INV-1", InvoiceStatus.DRAFT))

    service.submit("INV-1")

    assert [saved.status for saved in repository.updated] == [InvoiceStatus.PENDING_APPROVAL]


def test_reject_persists_the_invoice():
    repository, service = repository_and_service(pending_invoice("100"))

    service.reject("INV-1", "demo.manager", "Duplicate")

    assert [saved.status for saved in repository.updated] == [InvoiceStatus.REJECTED]


def test_a_refused_approval_is_never_persisted():
    repository, service = repository_and_service(pending_invoice("50000.01"))

    with pytest.raises(ApprovalNotPermittedError):
        service.approve("INV-1", MANAGER)

    assert repository.updated == []


# --- wrong-state and not-found errors: right type, right words, nothing changed, nothing saved -------------------


@pytest.mark.parametrize("status", [InvoiceStatus.PENDING_APPROVAL, InvoiceStatus.APPROVED, InvoiceStatus.REJECTED])
def test_submit_refuses_every_status_except_draft_and_changes_nothing(status):
    invoice = invoice_with("INV-1", status)
    repository, service = repository_and_service(invoice)
    before = copy.deepcopy(invoice)

    with pytest.raises(InvalidStateError, match=rf"^Invoice INV-1 is {status.value}; only drafts can be submitted\.$"):
        service.submit("INV-1")

    assert invoice == before
    assert repository.updated == []


@pytest.mark.parametrize("status", [InvoiceStatus.DRAFT, InvoiceStatus.APPROVED, InvoiceStatus.REJECTED])
@pytest.mark.parametrize("action", ["approve", "reject"])
def test_deciding_a_non_pending_invoice_is_refused_and_changes_nothing(status, action):
    invoice = invoice_with("INV-1", status, "100")
    repository, service = repository_and_service(invoice)
    before = copy.deepcopy(invoice)

    with pytest.raises(
        InvalidStateError, match=rf"^Invoice INV-1 is {status.value}; only pending invoices can be decided\.$"
    ):
        if action == "approve":
            service.approve("INV-1", DIRECTOR)
        else:
            service.reject("INV-1", "demo.director", "No")

    assert invoice == before
    assert repository.updated == []


def test_state_is_checked_before_permission():
    # An Admin approving a Draft hears "wrong state", not "not allowed": the state problem is true for everyone.
    service = service_for(invoice_with("INV-1", InvoiceStatus.DRAFT))

    with pytest.raises(InvalidStateError):
        service.approve("INV-1", ADMIN)


@pytest.mark.parametrize("action", ["submit", "approve", "reject"])
def test_unknown_invoice_is_reported_by_id_and_nothing_is_saved(action):
    repository, service = repository_and_service()
    calls = {
        "submit": lambda: service.submit("INV-404"),
        "approve": lambda: service.approve("INV-404", MANAGER),
        "reject": lambda: service.reject("INV-404", "demo.manager", "No"),
    }

    with pytest.raises(InvoiceNotFoundError, match=r"^Invoice INV-404 was not found\.$"):
        calls[action]()

    assert repository.updated == []


# --- more limit combinations through the service ------------------------------------------------------------------


def test_director_alone_approves_one_cent_above_the_manager_limit_where_a_manager_is_refused():
    refused_invoice = pending_invoice("50000.01")
    assert_refused_and_unchanged(service_for(refused_invoice), refused_invoice, MANAGER)

    result = service_for(pending_invoice("50000.01")).approve("INV-1", DIRECTOR)

    assert result.status == InvoiceStatus.APPROVED
    assert len(result.approvals) == 1


# --- concurrency: check-then-record must be atomic (PR review finding F1) ---------------------------------------------


class SnapshotRepository(FakeInvoiceRepository):
    """Behaves like a database: every read is a private snapshot and a save lands a little later.

    Two unlocked requests therefore both read 'no approvals yet', both pass the checks and the second
    save overwrites the first (a lost update). Only a service that serialises check-then-save survives.
    """

    def get_by_id(self, invoice_id):
        stored = super().get_by_id(invoice_id)
        return copy.deepcopy(stored) if stored is not None else None

    def update(self, invoice):
        time.sleep(0.05)
        super().update(invoice)

    def stored(self, invoice_id):
        return super().get_by_id(invoice_id)


def run_in_parallel(*calls):
    outcomes: list = []
    gate = threading.Barrier(len(calls))

    def worker(call):
        gate.wait()
        try:
            outcomes.append(("ok", call()))
        except ApprovalNotPermittedError as refusal:
            outcomes.append(("refused", str(refusal)))

    threads = [threading.Thread(target=worker, args=(call,)) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


# --- design: collaborators are injected (SOLID) ----------------------------------------------------

from datetime import datetime, timezone  # noqa: E402


class StubPolicy:
    """A policy written for the test: proves the service asks its policy and does not hard-code the limits."""

    def __init__(self, reason=None, required=1) -> None:
        self._reason = reason
        self._required = required

    def refusal_reason(self, amount, approver, prior_approvals):
        return self._reason

    def required_approvals(self, amount):
        return self._required


class OnlyWhatApprovalNeeds:
    """A store with just two methods. If the service needed more, this would fail: interface segregation."""

    def __init__(self, invoice: Invoice) -> None:
        self.invoice = invoice

    def get_by_id(self, invoice_id):
        return self.invoice if self.invoice.id == invoice_id else None

    def update(self, invoice):
        self.invoice = invoice


def test_the_service_obeys_whatever_policy_it_is_given_and_a_refusal_still_changes_nothing():
    invoice = pending_invoice("10")
    service = ApprovalService(FakeInvoiceRepository(invoice), policy=StubPolicy(reason="the stub says no"))

    reason = assert_refused_and_unchanged(service, invoice, DIRECTOR)

    assert reason == "the stub says no"


def test_the_service_uses_the_number_of_approvals_the_policy_requires():
    invoice = pending_invoice("10")
    service = ApprovalService(FakeInvoiceRepository(invoice), policy=StubPolicy(required=3))

    service.approve("INV-1", MANAGER)
    service.approve("INV-1", DIRECTOR)
    assert invoice.status == InvoiceStatus.PENDING_APPROVAL

    service.approve("INV-1", OTHER_DIRECTOR)
    assert invoice.status == InvoiceStatus.APPROVED
    assert len(invoice.approvals) == 3


def test_the_service_stamps_approvals_and_decisions_with_the_injected_clock():
    fixed = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    approved = pending_invoice("10")
    rejected = invoice_with("INV-2", InvoiceStatus.PENDING_APPROVAL)
    service = ApprovalService(FakeInvoiceRepository(approved, rejected), clock=lambda: fixed)

    service.approve("INV-1", MANAGER)
    service.reject("INV-2", "demo.admin", "Duplicate")

    assert approved.approvals[0].approved_at == fixed
    assert approved.decided_at == fixed
    assert rejected.decided_at == fixed


def test_the_service_works_with_a_store_that_offers_only_find_and_save():
    store = OnlyWhatApprovalNeeds(pending_invoice("10"))
    service = ApprovalService(store)

    result = service.approve("INV-1", MANAGER)

    assert result.status == InvoiceStatus.APPROVED
    assert store.invoice is result


def test_the_service_reports_how_many_approvals_its_policy_requires():
    service = service_for()

    assert service.required_approvals(Decimal("500000.00")) == 1
    assert service.required_approvals(Decimal("500000.01")) == 2
    assert ApprovalService(FakeInvoiceRepository(), policy=StubPolicy(required=5)).required_approvals(Decimal("1")) == 5


# --- step 1: above the Director limit nobody can approve alone yet ---------------------------------


@pytest.mark.parametrize("approver", [MANAGER, DIRECTOR], ids=lambda approver: approver.role)
def test_above_the_director_limit_is_refused_and_nothing_changes_until_two_approvers_are_supported(approver):
    invoice = pending_invoice("500000.01")
    service = service_for(invoice)

    reason = assert_refused_and_unchanged(service, invoice, approver)

    assert "need two approvers" in reason
