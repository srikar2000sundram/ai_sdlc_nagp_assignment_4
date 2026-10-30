"""Unit tests for the pure approval rules. Boundaries are tested on both sides, in both directions."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from invoice_app.domain import approval_policy
from invoice_app.domain.approval import ApprovalRecord, Approver
from invoice_app.domain.approval_policy import is_same_user, rejection_reason, required_approvals

MANAGER = Approver("manager.one", "Manager")
DIRECTOR = Approver("dir.one", "Director")
OTHER_DIRECTOR = Approver("dir.two", "Director")
OTHER_MANAGER = Approver("manager.two", "Manager")
ADMIN = Approver("admin.one", "Admin")

NO_APPROVALS: list[ApprovalRecord] = []


def approved_by(approver: Approver) -> list[ApprovalRecord]:
    return [ApprovalRecord(approver.username, approver.role, datetime(2026, 1, 1, tzinfo=timezone.utc))]


def amount(text: str) -> Decimal:
    return Decimal(text)


# --- single-approver limits -------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0.01", "49999.99", "50000"])
def test_manager_may_approve_up_to_and_including_the_manager_limit(value):
    assert rejection_reason(amount(value), MANAGER, NO_APPROVALS) is None


@pytest.mark.parametrize("value", ["50000.01", "75000", "500000"])
def test_manager_may_not_approve_above_the_manager_limit(value):
    reason = rejection_reason(amount(value), MANAGER, NO_APPROVALS)

    assert reason is not None
    assert "Manager may approve invoices up to 50,000.00" in reason
    assert "needs a Director" in reason


@pytest.mark.parametrize("value", ["0.01", "50000", "50000.01", "499999.99", "500000"])
def test_director_may_approve_up_to_and_including_the_director_limit(value):
    assert rejection_reason(amount(value), DIRECTOR, NO_APPROVALS) is None


@pytest.mark.parametrize("approver", [ADMIN, Approver("someone", ""), Approver("someone", "manager")])
def test_roles_other_than_manager_and_director_may_not_approve_anything(approver):
    reason = rejection_reason(amount("1"), approver, NO_APPROVALS)

    assert reason == f"Role {approver.role} is not allowed to approve invoices."


# --- how many approvals an invoice needs --------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", 1), ("50000", 1), ("50000.01", 1), ("500000", 1), ("500000.01", 2), ("2000000", 2)],
)
def test_required_approvals_steps_up_only_above_the_director_limit(value, expected):
    assert required_approvals(amount(value)) == expected


# --- two-approver rule above the director limit --------------------------------------------------


def test_second_approval_rule_does_not_apply_at_or_below_the_director_limit():
    # A Director who already approved a 500,000 invoice is not blocked by the duplicate rule:
    # such an invoice is already Approved, which the service reports as a state error instead.
    assert rejection_reason(amount("500000"), DIRECTOR, approved_by(DIRECTOR)) is None


# --- same-user comparison and approver construction ----------------------------------------------


def test_is_same_user_ignores_case_and_surrounding_whitespace_only():
    assert is_same_user("Ann", " ann ")
    assert not is_same_user("ann", "anna")
    assert not is_same_user("ann", "a nn")


@pytest.mark.parametrize("username", ["", "   "])
def test_approver_requires_a_username(username):
    with pytest.raises(ValueError, match=r"^An approver must have a username\.$"):
        Approver(username, "Director")


def test_limits_are_the_documented_amounts():
    assert approval_policy.MANAGER_LIMIT == Decimal("50000")
    assert approval_policy.DIRECTOR_LIMIT == Decimal("500000")


@pytest.mark.parametrize("role", ["director", "Director ", "DIRECTOR", " Manager", "manager"])
def test_role_names_are_matched_exactly_so_a_mistyped_role_fails_closed(role):
    reason = rejection_reason(amount("1"), Approver("someone", role), NO_APPROVALS)

    assert reason == f"Role {role} is not allowed to approve invoices."


# --- design: rules are small, replaceable parts (SOLID) --------------------------------------------


from invoice_app.domain.approval_policy import (  # noqa: E402
    ApprovalAttempt,
    ApprovalLimits,
    ApprovalPolicy,
    ApproverRoleRule,
    ManagerLimitRule,
    standard_policy,
)

LIMITS = ApprovalLimits()


class BlockedUserRule:
    """A rule written outside the policy module: adding it needs no change to any existing rule or the policy."""

    def __init__(self, blocked_username: str) -> None:
        self._blocked_username = blocked_username

    def refusal(self, attempt):
        if attempt.approver.username == self._blocked_username:
            return f"{self._blocked_username} is blocked from approving."
        return None


def test_a_new_rule_plugs_into_the_policy_without_changing_the_existing_rules():
    policy = ApprovalPolicy([ApproverRoleRule(), BlockedUserRule("manager.one")])

    assert policy.refusal_reason(amount("10"), MANAGER, NO_APPROVALS) == "manager.one is blocked from approving."
    assert policy.refusal_reason(amount("10"), DIRECTOR, NO_APPROVALS) is None


def test_a_policy_with_no_rules_allows_everything_and_the_first_objection_wins_otherwise():
    assert ApprovalPolicy([]).refusal_reason(amount("1"), ADMIN, NO_APPROVALS) is None

    first_then_second = ApprovalPolicy([ApproverRoleRule(), BlockedUserRule("admin.one")])
    assert first_then_second.refusal_reason(amount("1"), ADMIN, NO_APPROVALS) == (
        "Role Admin is not allowed to approve invoices."
    )


def test_limits_are_injected_data_not_global_constants():
    small = standard_policy(ApprovalLimits(manager=Decimal("100"), director=Decimal("1000")))

    assert small.refusal_reason(amount("100"), MANAGER, NO_APPROVALS) is None
    assert "up to 100.00" in small.refusal_reason(amount("100.01"), MANAGER, NO_APPROVALS)
    assert small.required_approvals(amount("1000")) == 1
    assert small.required_approvals(amount("1000.01")) == 2
    assert small.refusal_reason(amount("1000.01"), DIRECTOR, approved_by(DIRECTOR)) is not None


@pytest.mark.parametrize(
    ("rule", "attempt_amount", "approver", "prior", "expected_fragment"),
    [
        (ApproverRoleRule(), "10", ADMIN, NO_APPROVALS, "Role Admin is not allowed"),
        (ManagerLimitRule(LIMITS), "50000.01", MANAGER, NO_APPROVALS, "needs a Director"),
    ],
    ids=["role", "manager-limit"],
)
def test_each_rule_refuses_only_its_own_case_on_its_own(rule, attempt_amount, approver, prior, expected_fragment):
    reason = rule.refusal(ApprovalAttempt(amount(attempt_amount), approver, prior))

    assert expected_fragment in reason


@pytest.mark.parametrize(
    "rule",
    [ApproverRoleRule(), ManagerLimitRule(LIMITS)],
    ids=lambda rule: type(rule).__name__,
)
def test_every_rule_has_no_objection_to_a_plain_director_approval_so_any_can_join_any_policy(rule):
    assert rule.refusal(ApprovalAttempt(amount("1000"), DIRECTOR, NO_APPROVALS)) is None


@pytest.mark.parametrize(
    ("rule", "attempt_amount", "approver", "prior", "refuses"),
    [
        (ManagerLimitRule(LIMITS), "50000.00", MANAGER, NO_APPROVALS, False),
        (ManagerLimitRule(LIMITS), "50000.01", MANAGER, NO_APPROVALS, True),
        (ManagerLimitRule(LIMITS), "500000.00", MANAGER, NO_APPROVALS, True),
        (ManagerLimitRule(LIMITS), "500000.01", MANAGER, NO_APPROVALS, False),
    ],
)
def test_each_rule_has_its_own_boundary_one_cent_either_side(rule, attempt_amount, approver, prior, refuses):
    reason = rule.refusal(ApprovalAttempt(amount(attempt_amount), approver, prior))

    assert (reason is not None) is refuses


# --- step 1: above the Director limit nobody can approve alone yet ---------------------------------


@pytest.mark.parametrize("approver", [MANAGER, DIRECTOR], ids=lambda approver: approver.role)
def test_above_the_director_limit_is_refused_for_everyone_until_two_approvers_are_supported(approver):
    reason = rejection_reason(amount("500000.01"), approver, NO_APPROVALS)

    assert reason is not None
    assert "need two approvers" in reason
    assert "500,000.01" in reason
