"""Domain errors, each described in business terms.

The API layer maps them to HTTP statuses in ``api/error_handling.py``; the domain never mentions HTTP.
"""

class InvoiceNotFoundError(LookupError):
    """The invoice id does not exist. Mapped to HTTP 404."""


class InvalidStateError(Exception):
    """The invoice is in the wrong lifecycle state for the action. Mapped to HTTP 409."""


class DomainValidationError(ValueError):
    """The caller supplied unusable input (for example a blank rejection reason). Mapped to HTTP 400."""


class ApprovalNotPermittedError(Exception):
    """The approver may not approve this invoice. The message is the clear reason. Mapped to HTTP 403."""
