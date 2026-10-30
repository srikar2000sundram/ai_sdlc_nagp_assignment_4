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

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]: ...


class ApproverRoleRule:
    """Only the listed roles may approve anything at all."""

    def __init__(self, allowed_roles: Sequence[str] = APPROVER_ROLES) -> None:
        self._allowed_roles = tuple(allowed_roles)

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        if attempt.approver.role not in self._allowed_roles:
            return f"Role {attempt.approver.role} is not allowed to approve invoices."
        return None


class ManagerLimitRule:
    """Above the Manager limit (and up to the Director limit) a Director must approve."""

    def __init__(self, limits: ApprovalLimits) -> None:
        self._limits = limits

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        needs_director = self._limits.manager < attempt.amount <= self._limits.director
        if needs_director and attempt.approver.role != DIRECTOR:
            return (
                f"A Manager may approve invoices up to {_money(self._limits.manager)}; "
                f"this invoice is {_money(attempt.amount)} and needs a Director."
            )
        return None


class TwoApproversNotSupportedYetRule:
    """Step 1 only: above the Director limit nobody can approve alone, and two-approver support lands in step 2."""

    def __init__(self, limits: ApprovalLimits) -> None:
        self._limits = limits

    def refusal(self, attempt: ApprovalAttempt) -> Optional[str]:
        if attempt.amount > self._limits.director:
            return (
                f"Invoices above {_money(self._limits.director)} need two approvers, which is not supported yet; "
                f"this invoice is {_money(attempt.amount)}."
            )
        return None


class ApprovalPolicy:
    """Decides whether an approval is allowed by asking each rule in order; the first objection wins."""

    def __init__(self, rules: Sequence[ApprovalRule], limits: ApprovalLimits = ApprovalLimits()) -> None:
        self._rules = tuple(rules)
        self._limits = limits

    def refusal_reason(
        self, amount: Decimal, approver: Approver, prior_approvals: Sequence[ApprovalRecord]
    ) -> Optional[str]:
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
            TwoApproversNotSupportedYetRule(limits),
        ],
        limits,
    )


# Convenience functions over the standard policy, kept so callers and tests can use the rules without building one.
_STANDARD_POLICY = standard_policy()


def required_approvals(amount: Decimal) -> int:
    return _STANDARD_POLICY.required_approvals(amount)


def rejection_reason(
    amount: Decimal, approver: Approver, prior_approvals: Sequence[ApprovalRecord]
) -> Optional[str]:
    """Why this approver may not approve now, or None when the approval is allowed."""
    return _STANDARD_POLICY.refusal_reason(amount, approver, prior_approvals)


def is_same_user(first_username: str, second_username: str) -> bool:
    return _normalize(first_username) == _normalize(second_username)


def _normalize(username: str) -> str:
    return username.strip().casefold()


def _money(amount: Decimal) -> str:
    return f"{amount:,.2f}"
