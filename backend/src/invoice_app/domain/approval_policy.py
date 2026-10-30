"""Approval limits by role. Pure rules: no storage, no clock, no mutation.

- A Manager may approve invoices up to 50,000 (inclusive).
- A Director may approve invoices up to 500,000 (inclusive).
- Above 500,000 two distinct approvers are needed and the second must be a Director.
- The same user never counts as both approvers (usernames compared trimmed and case-insensitively).

Design (SOLID):
- Each rule is a small class with one reason to change (single responsibility).
- A policy is an ordered list of rules. A new rule is a new class added to the list; no existing rule or the
  policy itself is edited (open/closed).
- Rules and policy share narrow contracts (`ApprovalRule`), so any rule can stand in for another (Liskov).
- Limits are data (`ApprovalLimits`), passed in rather than read from globals (dependency inversion).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Protocol, Sequence

from .approval import ApprovalRecord, Approver

MANAGER = "Manager"
DIRECTOR = "Director"
APPROVER_ROLES = (MANAGER, DIRECTOR)

MANAGER_LIMIT = Decimal("50000")
DIRECTOR_LIMIT = Decimal("500000")


@dataclass(frozen=True)
class ApprovalLimits:
    """The two amounts the rules turn on. Inclusive: an invoice equal to a limit is within it."""

    manager: Decimal = MANAGER_LIMIT
    director: Decimal = DIRECTOR_LIMIT


@dataclass(frozen=True)
class ApprovalAttempt:
    """Everything a rule may look at: the invoice amount, who is approving, and who already approved."""

    amount: Decimal
    approver: Approver
    prior_approvals: Sequence[ApprovalRecord]


class ApprovalRule(Protocol):
    """One reason an approval may be refused. Returns the reason, or None when this rule has no objection."""

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        """Return the reason this rule refuses the attempt, or ``None`` when it has no objection."""


class ApproverRoleRule:
    """Only the listed roles may approve anything at all."""

    def __init__(self, allowed_roles: Sequence[str] = APPROVER_ROLES) -> None:
        """Args:
            allowed_roles: Roles that may approve at all. Defaults to Manager and Director.
        """
        self._allowed_roles = tuple(allowed_roles)

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        """Refuse any approver whose role is not in the allowed list (for example Admin)."""
        if attempt.approver.role not in self._allowed_roles:
            return f"Role {attempt.approver.role} is not allowed to approve invoices."
        return None


class ManagerLimitRule:
    """Above the Manager limit (and up to the Director limit) a Director must approve."""

    def __init__(self, limits: ApprovalLimits) -> None:
        """Args:
            limits: The Manager and Director limits.
        """
        self._limits = limits

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        """Refuse a non-Director when the amount is above the Manager limit and up to the Director limit.

        Above the Director limit this rule is silent: the two-approver rules decide there.
        """
        needs_director = self._limits.manager < attempt.amount <= self._limits.director
        if needs_director and attempt.approver.role != DIRECTOR:
            return (
                f"A Manager may approve invoices up to {_money(self._limits.manager)}; "
                f"this invoice is {_money(attempt.amount)} and needs a Director."
            )
        return None


class DistinctApproversRule:
    """Above the Director limit the same user may not approve twice."""

    def __init__(self, limits: ApprovalLimits) -> None:
        """Args:
            limits: The Manager and Director limits.
        """
        self._limits = limits

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        """Above the Director limit, refuse an approver who has already approved this invoice."""
        if attempt.amount <= self._limits.director:
            return None
        if any(is_same_user(attempt.approver.username, prior.username) for prior in attempt.prior_approvals):
            return (
                f"{attempt.approver.username} has already approved this invoice; "
                f"invoices above {_money(self._limits.director)} need two different approvers."
            )
        return None


class SecondApproverMustBeDirectorRule:
    """Above the Director limit the second approver must be a Director."""

    def __init__(self, limits: ApprovalLimits) -> None:
        """Args:
            limits: The Manager and Director limits.
        """
        self._limits = limits

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        """Above the Director limit, refuse a second approver who is not a Director.

        The first approver may be a Manager or a Director; only a second approval is constrained.
        """
        is_second_approval = bool(attempt.prior_approvals)
        if attempt.amount > self._limits.director and is_second_approval and attempt.approver.role != DIRECTOR:
            return (
                f"The second approver on an invoice above {_money(self._limits.director)} must be a Director; "
                f"{attempt.approver.username} is a {attempt.approver.role}."
            )
        return None


class ApprovalPolicy:
    """Decides whether an approval is allowed by asking each rule in order; the first objection wins."""

    def __init__(self, rules: Sequence[ApprovalRule], limits: ApprovalLimits = ApprovalLimits()) -> None:
        """Args:
            rules: Rules in the order their reasons should be reported; the first objection wins.
            limits: Used for how many approvals an invoice needs.
        """
        self._rules = tuple(rules)
        self._limits = limits

    def refusal_reason(
        self, amount: Decimal, approver: Approver, prior_approvals: Sequence[ApprovalRecord]
    ) -> Optional[str]:
        """Ask each rule in order and return the first objection.

        Args:
            amount: The invoice amount.
            approver: Who is trying to approve.
            prior_approvals: Approvals already recorded on the invoice.

        Returns:
            The reason the approval is refused, or ``None`` when it is allowed.
        """
        attempt = ApprovalAttempt(amount, approver, tuple(prior_approvals))
        for rule in self._rules:
            reason = rule.refusal(attempt)
            if reason is not None:
                return reason
        return None

    def required_approvals(self, amount: Decimal) -> int:
        """How many distinct approvals the invoice needs before it counts as Approved."""
        return 2 if amount > self._limits.director else 1


def standard_policy(limits: ApprovalLimits = ApprovalLimits()) -> ApprovalPolicy:
    """The rules of this feature, in the order their reasons should be reported."""
    return ApprovalPolicy(
        [
            ApproverRoleRule(),
            ManagerLimitRule(limits),
            DistinctApproversRule(limits),
            SecondApproverMustBeDirectorRule(limits),
        ],
        limits,
    )


# Convenience functions over the standard policy, kept so callers and tests can use the rules without building one.
_STANDARD_POLICY = standard_policy()


def required_approvals(amount: Decimal) -> int:
    """How many distinct approvals an invoice of this amount needs: 1, or 2 above the Director limit."""
    return _STANDARD_POLICY.required_approvals(amount)


def rejection_reason(
    amount: Decimal, approver: Approver, prior_approvals: Sequence[ApprovalRecord]
) -> Optional[str]:
    """Why this approver may not approve now, or None when the approval is allowed."""
    return _STANDARD_POLICY.refusal_reason(amount, approver, prior_approvals)


def is_same_user(first_username: str, second_username: str) -> bool:
    """True when two usernames are the same person: equal after trimming spaces and ignoring case."""
    return _normalize(first_username) == _normalize(second_username)


def _normalize(username: str) -> str:
    """Canonical form of a username for comparison: no surrounding spaces, case-folded."""
    return username.strip().casefold()


def _money(amount: Decimal) -> str:
    """Format an amount for a message, with thousands separators and two decimals (``50,000.00``)."""
    return f"{amount:,.2f}"
