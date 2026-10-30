"""Approval endpoints. The router lets Manager, Director and Admin in; the domain decides who may actually approve."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from invoice_app.domain.approval import Approver
from invoice_app.domain.approval_service import ApprovalService

from ..auth.dependencies import current_session, require_role
from ..auth.session_store import UserSession
from .invoices import get_approvals, present

# Manager, Director and Admin may call these endpoints. Whether the caller may actually approve a given invoice is decided by the domain.
router = APIRouter(prefix="/api/approvals", dependencies=[Depends(require_role("Manager", "Director", "Admin"))])


class RejectRequest(BaseModel):
    """Body of the reject call: the reason (required by the domain, so an empty body gives 400)."""

    reason: Optional[str] = None


@router.post("/{invoice_id}/approve")
def approve(
    invoice_id: str,
    session: UserSession = Depends(current_session),
    approvals: ApprovalService = Depends(get_approvals),
):
    """Record the signed-in user's approval. 403 with the reason when the rules refuse it; the invoice is then unchanged.
    """
    return present(approvals.approve(invoice_id, Approver(session.username, session.role)), approvals)


@router.post("/{invoice_id}/reject")
def reject(
    invoice_id: str,
    body: RejectRequest,
    session: UserSession = Depends(current_session),
    approvals: ApprovalService = Depends(get_approvals),
):
    """Reject a pending invoice with a reason."""
    return present(approvals.reject(invoice_id, session.username, body.reason or ""), approvals)
