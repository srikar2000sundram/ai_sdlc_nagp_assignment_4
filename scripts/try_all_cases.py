"""Try every approval case against a running server and print PASS / FAIL for each.

    python scripts/try_all_cases.py                       # starts its own fresh server on port 5058
    python scripts/try_all_cases.py --url http://localhost:5000   # use a server you already started

Each case creates its own invoice, so cases do not depend on each other. Exit code is 0 only if every case passes.
Uses only the standard library plus the app itself.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
PASSWORD = "ChangeMe123!"
MANAGER, DIRECTOR, DIRECTOR2, ADMIN = "demo.manager", "demo.director", "demo.director2", "demo.admin"

MANAGER_LIMIT_REASON = "A Manager may approve invoices up to 50,000.00; this invoice is {amount} and needs a Director."
DUPLICATE_REASON = "{user} has already approved this invoice; invoices above 500,000.00 need two different approvers."
SECOND_MUST_BE_DIRECTOR = "The second approver on an invoice above 500,000.00 must be a Director; {user} is a {role}."
ROLE_REASON = "Role {role} is not allowed to approve invoices."


class Api:
    """A small client for the app's JSON API: signs users in once and remembers their tokens."""

    def __init__(self, base: str):
        """Create the Api.

        Args:
            base: The server's base URL, for example ``http://127.0.0.1:5058``.
        """
        self.base = base.rstrip("/")
        self.tokens: dict[str, str] = {}

    def call(self, method: str, path: str, user: str | None = None, body=None, raw: str | None = None):
        """Send one request and return ``(status, parsed JSON or text)``; HTTP errors are returned, not raised."""
        data = raw.encode() if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = {"Content-Type": "application/json"}
        if user:
            headers["Authorization"] = "Bearer " + self.token(user)
        try:
            with urlopen(Request(self.base + path, data=data, method=method, headers=headers), timeout=15) as response:
                text = response.read().decode()
                return response.status, (json.loads(text) if text else None)
        except HTTPError as error:
            text = error.read().decode()
            try:
                return error.code, (json.loads(text) if text else None)
            except json.JSONDecodeError:
                return error.code, text

    def token(self, user: str) -> str:
        """Sign the user in on first use and return their bearer token."""
        if user not in self.tokens:
            status, body = self.call("POST", "/api/auth/login", body={"username": user, "password": PASSWORD})
            assert status == 200, f"login failed for {user}"
            self.tokens[user] = body["token"]
        return self.tokens[user]

    def new_pending(self, amount) -> str:
        """Create an invoice of this amount and submit it, so it is waiting for approval; return its id."""
        status, body = self.call("POST", "/api/invoices", DIRECTOR, {"customerName": "Case test", "amount": amount})
        assert status == 201, body
        self.call("POST", f"/api/invoices/{body['id']}/submit", DIRECTOR)
        return body["id"]

    def get(self, invoice_id: str) -> dict:
        """Fetch one invoice as JSON."""
        return self.call("GET", f"/api/invoices/{invoice_id}", DIRECTOR)[1]

    def approve(self, invoice_id: str, user: str):
        """Approve the invoice as this user; return ``(status, body)``."""
        return self.call("POST", f"/api/approvals/{invoice_id}/approve", user)


RESULTS: list[tuple[str, str, str, bool, str]] = []


def case(case_id: str, description: str, expected: str):
    """Decorator that registers a function as a numbered case and records PASS or FAIL for it."""
    def decorate(function):
        """Wrap the case function so a crash is recorded as a failure rather than stopping the run."""
        def run(api: Api):
            """Run the case against the client and append its result."""
            try:
                problem = function(api)
                ok, detail = problem is None, problem or "as expected"
            except Exception as error:  # a crashed case is a failed case, not a crashed run
                ok, detail = False, f"error: {error!r}"
            RESULTS.append((case_id, description, expected, ok, detail))
        run.case_id = case_id
        return run
    return decorate


def expect(condition: bool, message: str):
    """Return ``None`` when the condition holds, otherwise the failure message."""
    return None if condition else message


def refused(api: Api, invoice_id: str, user: str, reason: str, approvals_after: int):
    """A refusal must be 403 with the exact reason and must leave the invoice exactly as it was."""
    before = api.get(invoice_id)
    status, body = api.approve(invoice_id, user)
    after = api.get(invoice_id)
    if status != 403:
        return f"expected 403, got {status}"
    if body != {"error": reason}:
        return f"wrong reason: {body}"
    if before != after:
        return "the invoice changed after a refusal"
    return expect(len(after["approvals"]) == approvals_after, f"expected {approvals_after} approval(s), found {len(after['approvals'])}")


@case("C01", "Manager approves exactly 50,000.00", "200, Approved, decided by the Manager")
def c01(api):
    """Manager approves exactly 50,000.00.

    Expected: 200, Approved, decided by the Manager.
    """
    invoice = api.new_pending(50000.00)
    status, body = api.approve(invoice, MANAGER)
    return expect(status == 200 and body["status"] == "Approved" and body["decidedBy"] == MANAGER, f"{status} {body}")


@case("C02", "Manager approves 50,000.01 (one cent over)", "403 Manager-limit reason, invoice unchanged")
def c02(api):
    """Manager approves 50,000.01 (one cent over).

    Expected: 403 Manager-limit reason, invoice unchanged.
    """
    return refused(api, api.new_pending(50000.01), MANAGER, MANAGER_LIMIT_REASON.format(amount="50,000.01"), 0)


@case("C03", "Director approves 50,000.01", "200, Approved with one approval")
def c03(api):
    """Director approves 50,000.01.

    Expected: 200, Approved with one approval.
    """
    invoice = api.new_pending(50000.01)
    status, body = api.approve(invoice, DIRECTOR)
    return expect(status == 200 and body["status"] == "Approved" and len(body["approvals"]) == 1, f"{status} {body}")


@case("C04", "Director approves exactly 500,000.00", "200, Approved with one approval (no second approver needed)")
def c04(api):
    """Director approves exactly 500,000.00.

    Expected: 200, Approved with one approval (no second approver needed).
    """
    invoice = api.new_pending(500000.00)
    status, body = api.approve(invoice, DIRECTOR)
    return expect(status == 200 and body["status"] == "Approved" and body["requiredApprovals"] == 1, f"{status} {body}")


@case("C05", "Manager approves exactly 500,000.00", "403 Manager-limit reason, invoice unchanged")
def c05(api):
    """Manager approves exactly 500,000.00.

    Expected: 403 Manager-limit reason, invoice unchanged.
    """
    return refused(api, api.new_pending(500000.00), MANAGER, MANAGER_LIMIT_REASON.format(amount="500,000.00"), 0)


@case("C06", "Admin approves a small invoice", "403 role reason, invoice unchanged")
def c06(api):
    """Admin approves a small invoice.

    Expected: 403 role reason, invoice unchanged.
    """
    return refused(api, api.new_pending(100.00), ADMIN, ROLE_REASON.format(role="Admin"), 0)


@case("C07", "Admin approves an invoice above 500,000", "403 role reason, invoice unchanged")
def c07(api):
    """Admin approves an invoice above 500,000.

    Expected: 403 role reason, invoice unchanged.
    """
    return refused(api, api.new_pending(600000.00), ADMIN, ROLE_REASON.format(role="Admin"), 0)


@case("C08", "Director gives the first approval on 500,000.01", "200, still Pending Approval, 1 of 2, no decider yet")
def c08(api):
    """Director gives the first approval on 500,000.01.

    Expected: 200, still Pending Approval, 1 of 2, no decider yet.
    """
    invoice = api.new_pending(500000.01)
    status, body = api.approve(invoice, DIRECTOR)
    return expect(status == 200 and body["status"] == "PendingApproval" and len(body["approvals"]) == 1
                  and body["requiredApprovals"] == 2 and body["decidedBy"] is None, f"{status} {body}")


@case("C09", "The same Director approves the same 500,000.01 invoice again", "403 duplicate-user reason, still exactly 1 approval")
def c09(api):
    """The same Director approves the same 500,000.01 invoice again.

    Expected: 403 duplicate-user reason, still exactly 1 approval.
    """
    invoice = api.new_pending(500000.01)
    api.approve(invoice, DIRECTOR)
    return refused(api, invoice, DIRECTOR, DUPLICATE_REASON.format(user=DIRECTOR), 1)


@case("C10", "The Manager gives the second approval after a Director", "403 second approver must be a Director, still 1 approval")
def c10(api):
    """The Manager gives the second approval after a Director.

    Expected: 403 second approver must be a Director, still 1 approval.
    """
    invoice = api.new_pending(600000.00)
    api.approve(invoice, DIRECTOR)
    return refused(api, invoice, MANAGER, SECOND_MUST_BE_DIRECTOR.format(user=MANAGER, role="Manager"), 1)


@case("C11", "A different Director gives the second approval", "200, Approved, 2 approvals, decided by the second Director")
def c11(api):
    """A different Director gives the second approval.

    Expected: 200, Approved, 2 approvals, decided by the second Director.
    """
    invoice = api.new_pending(600000.00)
    api.approve(invoice, DIRECTOR)
    status, body = api.approve(invoice, DIRECTOR2)
    return expect(status == 200 and body["status"] == "Approved" and len(body["approvals"]) == 2 and body["decidedBy"] == DIRECTOR2, f"{status} {body}")


@case("C12", "Manager first, then a Director, on 500,000.01", "200, Approved, 2 approvals")
def c12(api):
    """Manager first, then a Director, on 500,000.01.

    Expected: 200, Approved, 2 approvals.
    """
    invoice = api.new_pending(500000.01)
    first = api.approve(invoice, MANAGER)
    status, body = api.approve(invoice, DIRECTOR)
    return expect(first[0] == 200 and first[1]["status"] == "PendingApproval" and status == 200 and body["status"] == "Approved"
                  and len(body["approvals"]) == 2, f"{first[0]} then {status} {body}")


@case("C13", "The same Manager approves twice on 500,000.01", "403 duplicate-user reason, still 1 approval")
def c13(api):
    """The same Manager approves twice on 500,000.01.

    Expected: 403 duplicate-user reason, still 1 approval.
    """
    invoice = api.new_pending(500000.01)
    api.approve(invoice, MANAGER)
    return refused(api, invoice, MANAGER, DUPLICATE_REASON.format(user=MANAGER), 1)


@case("C14", "A refused attempt does not block a valid one afterwards", "after C10-style refusal, a different Director still completes it")
def c14(api):
    """A refused attempt does not block a valid one afterwards.

    Expected: after C10-style refusal, a different Director still completes it.
    """
    invoice = api.new_pending(600000.00)
    api.approve(invoice, DIRECTOR)
    api.approve(invoice, MANAGER)  # refused
    status, body = api.approve(invoice, DIRECTOR2)
    return expect(status == 200 and body["status"] == "Approved" and len(body["approvals"]) == 2, f"{status} {body}")


@case("C15", "Approve an invoice that is already Approved", "409 state error, invoice unchanged")
def c15(api):
    """Approve an invoice that is already Approved.

    Expected: 409 state error, invoice unchanged.
    """
    invoice = api.new_pending(10.00)
    api.approve(invoice, MANAGER)
    before = api.get(invoice)
    status, body = api.approve(invoice, DIRECTOR)
    return expect(status == 409 and "only pending invoices can be decided" in body["error"] and api.get(invoice) == before, f"{status} {body}")


@case("C16", "Approve a Draft invoice (never submitted)", "409 state error")
def c16(api):
    """Approve a Draft invoice (never submitted).

    Expected: 409 state error.
    """
    _, created = api.call("POST", "/api/invoices", DIRECTOR, {"customerName": "Draft", "amount": 10})
    status, body = api.approve(created["id"], DIRECTOR)
    return expect(status == 409, f"{status} {body}")


@case("C17", "Approve an invoice that does not exist", "404 not found")
def c17(api):
    """Approve an invoice that does not exist.

    Expected: 404 not found.
    """
    status, body = api.approve("INV-9999", DIRECTOR)
    return expect(status == 404 and "not found" in body["error"], f"{status} {body}")


@case("C18", "Reject a pending invoice with a reason", "200, Rejected, reason stored")
def c18(api):
    """Reject a pending invoice with a reason.

    Expected: 200, Rejected, reason stored.
    """
    invoice = api.new_pending(200.00)
    status, body = api.call("POST", f"/api/approvals/{invoice}/reject", MANAGER, {"reason": "Duplicate invoice"})
    return expect(status == 200 and body["status"] == "Rejected" and body["decisionNote"] == "Duplicate invoice", f"{status} {body}")


@case("C19", "Reject without a reason", "400, invoice stays pending")
def c19(api):
    """Reject without a reason.

    Expected: 400, invoice stays pending.
    """
    invoice = api.new_pending(200.00)
    status, body = api.call("POST", f"/api/approvals/{invoice}/reject", MANAGER, {"reason": "  "})
    return expect(status == 400 and api.get(invoice)["status"] == "PendingApproval", f"{status} {body}")


@case("C20", "Reject an invoice that already has its first approval", "200, Rejected, first approval kept on record")
def c20(api):
    """Reject an invoice that already has its first approval.

    Expected: 200, Rejected, first approval kept on record.
    """
    invoice = api.new_pending(600000.00)
    api.approve(invoice, DIRECTOR)
    status, body = api.call("POST", f"/api/approvals/{invoice}/reject", ADMIN, {"reason": "Wrong supplier"})
    return expect(status == 200 and body["status"] == "Rejected" and len(body["approvals"]) == 1, f"{status} {body}")


@case("C21", "Call the approve endpoint without signing in", "401")
def c21(api):
    """Call the approve endpoint without signing in.

    Expected: 401.
    """
    status, _ = api.call("POST", "/api/approvals/INV-1001/approve")
    return expect(status == 401, f"got {status}")


@case("C22", "Sign in with a wrong password", "401 invalid username or password")
def c22(api):
    """Sign in with a wrong password.

    Expected: 401 invalid username or password.
    """
    status, body = api.call("POST", "/api/auth/login", body={"username": MANAGER, "password": "wrong"})
    return expect(status == 401 and body == {"error": "Invalid username or password."}, f"{status} {body}")


@case("C23", "Create invoices with unusable amounts (0, -5, 50000.001, 1e999999, NaN)", "400 each, nothing stored")
def c23(api):
    """Create invoices with unusable amounts (0, -5, 50000.001, 1e999999, NaN).

    Expected: 400 each, nothing stored.
    """
    before = len(api.call("GET", "/api/invoices", DIRECTOR)[1])
    for raw in ('0', '-5', '50000.001', '1e999999', '"NaN"'):
        status, body = api.call("POST", "/api/invoices", DIRECTOR, raw=f'{{"customerName":"Bad","amount":{raw}}}')
        if status != 400:
            return f"amount {raw}: expected 400, got {status} {body}"
    after = api.call("GET", "/api/invoices", DIRECTOR)
    return expect(after[0] == 200 and len(after[1]) == before, "an invalid invoice was stored or the list broke")


@case("C24", "Delete an invoice as Manager, then as Admin", "403 for the Manager, 204 for the Admin")
def c24(api):
    """Delete an invoice as Manager, then as Admin.

    Expected: 403 for the Manager, 204 for the Admin.
    """
    invoice = api.new_pending(5.00)
    denied = api.call("DELETE", f"/api/invoices/{invoice}", MANAGER)[0]
    allowed = api.call("DELETE", f"/api/invoices/{invoice}", ADMIN)[0]
    return expect(denied == 403 and allowed == 204, f"manager {denied}, admin {allowed}")


@case("C25", "List invoices filtered by status", "only Approved invoices; an unknown status gives 400")
def c25(api):
    """List invoices filtered by status.

    Expected: only Approved invoices; an unknown status gives 400.
    """
    status, body = api.call("GET", "/api/invoices?status=approved", DIRECTOR)
    bad = api.call("GET", "/api/invoices?status=nonsense", DIRECTOR)[0]
    return expect(status == 200 and body and all(i["status"] == "Approved" for i in body) and bad == 400, f"{status} bad={bad}")


CASES = [c01, c02, c03, c04, c05, c06, c07, c08, c09, c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25]


def start_server(port: int):
    """Start a fresh app server on this port and wait until it answers; exit if it never does."""
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "invoice_app.api.main:app", "--app-dir", str(ROOT / "backend" / "src"),
         "--host", "127.0.0.1", "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            return process
        except (URLError, OSError):
            time.sleep(0.25)
    process.terminate()
    raise SystemExit("the server did not start")


def main() -> int:
    """Run every case, print one line each and a total, and return the exit code."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="use a server that is already running (it should be freshly started)")
    parser.add_argument("--port", type=int, default=5058)
    arguments = parser.parse_args()

    process = None if arguments.url else start_server(arguments.port)
    api = Api(arguments.url or f"http://127.0.0.1:{arguments.port}")
    try:
        for run in CASES:
            run(api)
    finally:
        if process:
            process.terminate()

    width = max(len(description) for _, description, *_ in RESULTS)
    print(f"{'ID':<4}  {'RESULT':<6}  {'CASE':<{width}}  EXPECTED")
    for case_id, description, expected, ok, detail in RESULTS:
        print(f"{case_id:<4}  {'PASS' if ok else 'FAIL':<6}  {description:<{width}}  {expected}")
        if not ok:
            print(f"      -> {detail}")
    failed = [r for r in RESULTS if not r[3]]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
