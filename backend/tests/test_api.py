"""HTTP-level tests: status codes, messages, sign-in, validation and the approval flow through the real routers."""

import threading

import pytest
from fastapi.testclient import TestClient

from invoice_app.api.main import create_app

PASSWORD = "ChangeMe123!"


@pytest.fixture
def client() -> TestClient:
    """A test client for a freshly built app (fresh data, no sessions)."""
    return TestClient(create_app())


def sign_in(client: TestClient, username: str) -> dict:
    """Sign in as a demo user and return the ``Authorization`` header to send."""
    response = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def get_invoice(client: TestClient, headers: dict, invoice_id: str) -> dict:
    """Fetch one invoice as JSON."""
    return client.get(f"/api/invoices/{invoice_id}", headers=headers).json()


def test_api_requires_sign_in(client):
    assert client.get("/api/invoices").status_code == 401


def test_login_rejects_bad_password(client):
    response = client.post("/api/auth/login", json={"username": "demo.admin", "password": "nope"})

    assert response.status_code == 401
    assert response.json()["error"] == "Invalid username or password."


def test_list_invoices_and_filter_by_status(client):
    headers = sign_in(client, "demo.admin")

    pending = client.get("/api/invoices?status=pendingapproval", headers=headers).json()

    assert {invoice["id"] for invoice in pending} >= {"INV-1001", "INV-1002", "INV-1004"}
    assert all(invoice["status"] == "PendingApproval" for invoice in pending)
    assert client.get("/api/invoices?status=bogus", headers=headers).status_code == 400


def test_create_invoice_validates_input(client):
    headers = sign_in(client, "demo.admin")

    assert client.post("/api/invoices", json={"customerName": " ", "amount": 5}, headers=headers).status_code == 400
    assert client.post("/api/invoices", json={"customerName": "A", "amount": 0}, headers=headers).status_code == 400

    created = client.post("/api/invoices", json={"customerName": " Acme ", "amount": 12.5}, headers=headers)
    assert created.status_code == 201
    assert created.json()["customerName"] == "Acme"
    assert created.json()["status"] == "Draft"


def test_delete_is_admin_only(client):
    manager = sign_in(client, "demo.manager")
    admin = sign_in(client, "demo.admin")

    assert client.delete("/api/invoices/INV-1005", headers=manager).status_code == 403
    assert client.delete("/api/invoices/INV-1005", headers=admin).status_code == 204
    assert client.delete("/api/invoices/INV-1005", headers=admin).status_code == 404


def test_submit_then_reject_maps_errors(client):
    headers = sign_in(client, "demo.manager")

    assert client.post("/api/invoices/INV-1005/submit", headers=headers).json()["status"] == "PendingApproval"
    assert client.post("/api/invoices/INV-1005/submit", headers=headers).status_code == 409
    assert client.post("/api/approvals/INV-1005/reject", json={"reason": " "}, headers=headers).status_code == 400
    assert client.post("/api/approvals/INV-404/approve", headers=headers).status_code == 404

    rejected = client.post("/api/approvals/INV-1005/reject", json={"reason": "Duplicate"}, headers=headers)
    assert rejected.json()["status"] == "Rejected"
    assert rejected.json()["decisionNote"] == "Duplicate"


def test_ui_is_served_without_sign_in(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Invoice Approvals" in response.text


# --- approval limits over HTTP -------------------------------------------------------------------------


def test_manager_over_limit_gets_403_with_a_reason_and_the_invoice_is_untouched(client):
    manager = sign_in(client, "demo.manager")
    before = get_invoice(client, manager, "INV-2001")

    response = client.post("/api/approvals/INV-2001/approve", headers=manager)

    assert response.status_code == 403
    assert response.json()["error"] == (
        "A Manager may approve invoices up to 50,000.00; this invoice is 75,000.00 and needs a Director."
    )
    assert get_invoice(client, manager, "INV-2001") == before


def test_manager_approves_a_small_invoice(client):
    manager = sign_in(client, "demo.manager")

    response = client.post("/api/approvals/INV-1001/approve", headers=manager)

    assert response.status_code == 200
    assert response.json()["status"] == "Approved"
    assert response.json()["decidedBy"] == "demo.manager"


def test_director_approves_between_the_limits_alone(client):
    director = sign_in(client, "demo.director")

    response = client.post("/api/approvals/INV-2001/approve", headers=director)

    assert response.status_code == 200
    assert response.json()["status"] == "Approved"
    assert response.json()["requiredApprovals"] == 1


def test_two_directors_are_needed_above_the_director_limit(client):
    director = sign_in(client, "demo.director")
    other_director = sign_in(client, "demo.director2")

    first = client.post("/api/approvals/INV-2002/approve", headers=director).json()
    assert first["status"] == "PendingApproval"
    assert first["requiredApprovals"] == 2
    assert [approval["username"] for approval in first["approvals"]] == ["demo.director"]

    second = client.post("/api/approvals/INV-2002/approve", headers=other_director).json()
    assert second["status"] == "Approved"
    assert second["decidedBy"] == "demo.director2"
    assert len(second["approvals"]) == 2


def test_same_director_twice_gets_403_and_the_first_approval_stays_alone(client):
    director = sign_in(client, "demo.director")
    client.post("/api/approvals/INV-2002/approve", headers=director)
    before = get_invoice(client, director, "INV-2002")

    response = client.post("/api/approvals/INV-2002/approve", headers=director)

    assert response.status_code == 403
    assert "already approved" in response.json()["error"]
    assert get_invoice(client, director, "INV-2002") == before


def test_manager_as_second_approver_gets_403(client):
    director = sign_in(client, "demo.director")
    manager = sign_in(client, "demo.manager")
    client.post("/api/approvals/INV-2002/approve", headers=director)

    response = client.post("/api/approvals/INV-2002/approve", headers=manager)

    assert response.status_code == 403
    assert "must be a Director" in response.json()["error"]


def test_admin_gets_a_clear_reason_when_trying_to_approve(client):
    admin = sign_in(client, "demo.admin")

    response = client.post("/api/approvals/INV-1001/approve", headers=admin)

    assert response.status_code == 403
    assert response.json()["error"] == "Role Admin is not allowed to approve invoices."


def test_admin_is_not_blocked_from_rejecting(client):
    admin = sign_in(client, "demo.admin")

    response = client.post("/api/approvals/INV-1001/reject", json={"reason": "Wrong customer"}, headers=admin)

    assert response.status_code == 200
    assert response.json()["status"] == "Rejected"


def test_approve_and_reject_require_sign_in(client):
    assert client.post("/api/approvals/INV-1001/approve").status_code == 401
    assert client.post("/api/approvals/INV-1001/reject", json={"reason": "x"}).status_code == 401


def test_admin_refusal_leaves_an_over_limit_invoice_unchanged(client):
    admin = sign_in(client, "demo.admin")
    before = get_invoice(client, admin, "INV-2002")

    assert client.post("/api/approvals/INV-2002/approve", headers=admin).status_code == 403
    assert get_invoice(client, admin, "INV-2002") == before
    assert before["approvals"] == []


def test_manager_can_give_the_first_approval_but_not_a_second_one_as_the_same_user(client):
    manager = sign_in(client, "demo.manager")

    first = client.post("/api/approvals/INV-2002/approve", headers=manager)
    assert first.status_code == 200 and first.json()["status"] == "PendingApproval"

    before = get_invoice(client, manager, "INV-2002")
    again = client.post("/api/approvals/INV-2002/approve", headers=manager)

    assert again.status_code == 403
    assert "already approved" in again.json()["error"]
    assert get_invoice(client, manager, "INV-2002") == before
    assert len(before["approvals"]) == 1


def test_simultaneous_double_click_by_one_director_approves_once(client):
    director = sign_in(client, "demo.director")
    statuses: list[int] = []
    gate = threading.Barrier(4)

    def click():
        """Wait at the barrier, then press Approve: all four clicks land together."""
        gate.wait()
        statuses.append(client.post("/api/approvals/INV-2002/approve", headers=director).status_code)

    threads = [threading.Thread(target=click) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [200, 403, 403, 403]
    invoice = get_invoice(client, director, "INV-2002")
    assert invoice["status"] == "PendingApproval"
    assert [approval["username"] for approval in invoice["approvals"]] == ["demo.director"]


# --- amounts are validated before anything is stored (PR review findings F2, F3, F4) ---------------------------------


@pytest.mark.parametrize(
    "amount",
    ["1e999999", "NaN", "Infinity", "50000.001", "0.001", "1e-30", "-5", "0", "1234567890123.00"],
)
def test_unusable_amounts_are_rejected_with_a_message_and_not_stored(client, amount):
    headers = sign_in(client, "demo.admin")
    before = client.get("/api/invoices", headers=headers).json()

    response = client.post("/api/invoices", json={"customerName": "Acme", "amount": amount}, headers=headers)

    assert response.status_code == 400
    assert response.json()["error"] == (
        "Amount must be greater than zero, with at most 2 decimal places and 12 digits before the point."
    )
    after = client.get("/api/invoices", headers=headers)
    assert after.status_code == 200
    assert after.json() == before


@pytest.mark.parametrize("amount", ["50000.00", "50000.01", "500000.00", "500000.01", "999999999999.99"])
def test_amounts_at_the_limits_round_trip_exactly(client, amount):
    headers = sign_in(client, "demo.admin")

    created = client.post("/api/invoices", json={"customerName": "Acme", "amount": amount}, headers=headers)

    assert created.status_code == 201
    assert f"{created.json()['amount']:.2f}" == amount


def test_a_malformed_body_gets_a_400_and_does_not_leak_internals(client):
    headers = sign_in(client, "demo.admin")

    response = client.post(
        "/api/invoices", content=b"not json", headers={**headers, "Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json() == {"error": "The request body is invalid."}


# --- design: the composition root accepts other implementations (SOLID) -----------------------------

from decimal import Decimal  # noqa: E402

from invoice_app.api.auth.user_directory import AuthenticatedUser  # noqa: E402
from invoice_app.domain.approval_policy import ApprovalLimits, standard_policy  # noqa: E402


class OneUserDirectory:
    """A user directory that accepts one account, to prove the login endpoint uses whatever directory it is given."""

    def authenticate(self, username, password):
        """Accept only ``only.user`` / ``pw``."""
        return AuthenticatedUser("only.user", "Admin") if (username, password) == ("only.user", "pw") else None


def test_login_uses_whichever_user_directory_the_app_was_built_with():
    client = TestClient(create_app(users=OneUserDirectory()))

    assert client.post("/api/auth/login", json={"username": "demo.admin", "password": PASSWORD}).status_code == 401
    accepted = client.post("/api/auth/login", json={"username": "only.user", "password": "pw"})

    assert accepted.status_code == 200
    assert accepted.json()["role"] == "Admin"


def test_the_approval_count_shown_to_the_ui_comes_from_the_policy_that_is_enforced():
    policy = standard_policy(ApprovalLimits(manager=Decimal("100"), director=Decimal("1000")))
    client = TestClient(create_app(policy=policy))
    headers = sign_in(client, "demo.director")

    created = client.post("/api/invoices", json={"customerName": "Small limits", "amount": 1500}, headers=headers)

    assert created.json()["requiredApprovals"] == 2
    listed = client.get("/api/invoices", headers=headers).json()
    required = {item["id"]: item["requiredApprovals"] for item in listed}
    assert required["INV-1001"] == 2  # 4,250.00 is above the injected 1,000 limit
    assert required["INV-1002"] == 1  # 980.50 is below it
