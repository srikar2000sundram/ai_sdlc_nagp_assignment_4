"""Invoice endpoints: list, get, create, submit and (Admin only) delete."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from invoice_app.domain.approval_service import ApprovalService
from invoice_app.domain.invoice import Invoice
from invoice_app.domain.invoice_status import InvoiceStatus
from invoice_app.domain.repository import InvoiceReader, InvoiceRepository, InvoiceWriter

from ..auth.dependencies import require_role
from ..serialization import invoice_to_json

router = APIRouter(prefix="/api/invoices")


class CreateInvoiceRequest(BaseModel):
    """Body of ``POST /api/invoices``. The amount must be positive with at most 2 decimals and 12 digits before the
    point.
    """

    customerName: str
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


def get_repository(request: Request) -> InvoiceRepository:
    """Dependency: the app's repository."""
    return request.app.state.repository


def get_approvals(request: Request) -> ApprovalService:
    """Dependency: the app's approval service."""
    return request.app.state.approvals


def present(invoice: Invoice, approvals: ApprovalService) -> dict:
    """The invoice as the UI sees it, with the approval count taken from the policy that is actually enforced."""
    return invoice_to_json(invoice, approvals.required_approvals(invoice.amount))


@router.get("")
def get_all(
    status: Optional[str] = None,
    reader: InvoiceReader = Depends(get_repository),
    approvals: ApprovalService = Depends(get_approvals),
):
    """List invoices, optionally filtered by ``?status=`` (case-insensitive; 400 for an unknown status)."""
    invoices = reader.get_all()

    if status:
        parsed = next((s for s in InvoiceStatus if s.value.lower() == status.lower()), None)
        if parsed is None:
            # 201 Created, with the new invoice's address in the Location header.
            return JSONResponse({"error": f"Unknown status '{status}'."}, status_code=400)
        invoices = [invoice for invoice in invoices if invoice.status == parsed]

    return [present(invoice, approvals) for invoice in invoices]


@router.get("/{invoice_id}")
def get_by_id(
    invoice_id: str,
    reader: InvoiceReader = Depends(get_repository),
    approvals: ApprovalService = Depends(get_approvals),
):
    """Return one invoice, or 404 with an empty body."""
    invoice = reader.get_by_id(invoice_id)
    if invoice is None:
        return Response(status_code=404)
    return present(invoice, approvals)


@router.post("", status_code=201)
def create(
    body: CreateInvoiceRequest,
    writer: InvoiceWriter = Depends(get_repository),
    approvals: ApprovalService = Depends(get_approvals),
):
    """Create a Draft invoice (400 for a blank customer or an unusable amount)."""
    if not body.customerName.strip():
        return JSONResponse({"error": "Customer name is required."}, status_code=400)

    invoice = writer.add(Invoice(customer_name=body.customerName.strip(), amount=body.amount))
    return JSONResponse(
        present(invoice, approvals), status_code=201, headers={"Location": f"/api/invoices/{invoice.id}"}
    )


@router.post("/{invoice_id}/submit")
def submit(invoice_id: str, approvals: ApprovalService = Depends(get_approvals)):
    """Send a Draft invoice for approval."""
    return present(approvals.submit(invoice_id), approvals)


@router.delete("/{invoice_id}", status_code=204, dependencies=[Depends(require_role("Admin"))])
def delete(invoice_id: str, writer: InvoiceWriter = Depends(get_repository)):
    """Delete an invoice. Admin only; 404 when it does not exist."""
    if not writer.remove(invoice_id):
        return Response(status_code=404)
    return Response(status_code=204)
