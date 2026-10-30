"""Value objects for approvals: who is approving, and what has been approved."""

from dataclasses import dataclass
from datetime import datetime

from .errors import DomainValidationError


@dataclass(frozen=True)
class Approver:
    """Who is trying to approve: a username and the role they signed in with."""

    username: str
    role: str

    def __post_init__(self) -> None:
        """Refuse a blank username: every approval must be attributable to someone."""
        if not self.username or not self.username.strip():
            raise DomainValidationError("An approver must have a username.")


@dataclass(frozen=True)
class ApprovalRecord:
    """One recorded approval on an invoice. Invoices above the Director limit collect two."""

    username: str
    role: str
    approved_at: datetime
