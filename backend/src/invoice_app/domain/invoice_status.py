"""The lifecycle states of an invoice."""

from enum import Enum


class InvoiceStatus(str, Enum):
    """Where an invoice is in its life: Draft, then PendingApproval, then Approved or Rejected.

    The string values are what the API returns and the UI shows.
    """

    DRAFT = "Draft"
    PENDING_APPROVAL = "PendingApproval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
