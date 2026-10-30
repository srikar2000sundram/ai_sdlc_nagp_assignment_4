# User Guide: Run the Project and Test Every Case

This guide shows how to start the app and how to check every approval case, in three ways that you can use separately or together:

| Way | Effort | What it proves |
| --- | --- | --- |
| **A. One command** (`scripts/try_all_cases.py`) | 30 seconds | All 25 cases pass against a real running server |
| **B. Automated test suites** (pytest, mutation, Playwright) | 2 minutes | The unit, API and UI tests pass; the tests can detect bugs |
| **C. By hand in the web UI** | 15 minutes | You can see each rule working, with your own eyes |

## 1. Before you start

You need Python 3.10 or newer (3.13 was used) and a terminal in the repository folder (the one containing `backend`, `e2e`, `scripts`, `docs`). Node.js is needed only for the Playwright test, and WSL with Ubuntu 22.04 only for the mutation test.

Install once:

```powershell
pip install -e "backend[dev]"
```

## 2. Run the project

```powershell
python -m uvicorn invoice_app.api.main:app --app-dir backend/src --port 5000
```

Wait for the line `Application startup complete`, then open <http://localhost:5000> in a browser. You should see a **Sign in** form. Stop the server with `Ctrl+C`.

Important facts:

- **Data lives in memory.** Every restart resets everything to the demo data. Restart whenever you want a clean slate.
- **Port busy?** Use another port: `--port 5001`, then open `http://localhost:5001`.
- The OpenAPI page at `/docs` lists the endpoints, but the calls need a sign-in token, so use the UI or the script for real testing.

### Demo accounts

All passwords are `ChangeMe123!`. These are local demo accounts, not real credentials.

| Username | Role | Can approve? |
| --- | --- | --- |
| `demo.manager` | Manager | Up to 50,000.00; first approval above 500,000.00 |
| `demo.director` | Director | Up to 500,000.00 alone; either approval above that |
| `demo.director2` | Director | Same as above (a second, different Director) |
| `demo.admin` | Admin | Never (can reject and delete only) |

### Demo invoices already in the app

| Invoice | Amount | Status | Good for |
| --- | --- | --- | --- |
| INV-1001, 1002, 1004 | 4,250.00; 980.50; 615.75 | Pending | Simple approve and reject |
| INV-1003 | 12,300.00 | Approved | Already finished |
| INV-1005 | 310.00 | Draft | Needs "Submit for approval" first |
| INV-2001 | 75,000.00 | Pending | Manager refused, Director allowed |
| INV-2002 | 600,000.00 | Pending | Needs two different approvers |

## 3. Way A: try every case with one command

With no server running, from the repository folder:

```powershell
python scripts/try_all_cases.py
```

The script starts its own fresh server (on port 5058), runs all 25 cases, prints one line each, stops the server, and exits with code 0 only if every case passed. Each case creates its own invoice, so the cases do not depend on each other. To use a server that is already running instead:

```powershell
python scripts/try_all_cases.py --url http://localhost:5000
```

Expected last line: `25 of 25 cases passed`. The script also checks the **exact reason text** of every refusal and that **the invoice is identical before and after** a refused attempt.

### The 25 cases and their result (last run: all passed)

| ID | Case | Expected outcome | Result |
| --- | --- | --- | --- |
| C01 | Manager approves exactly 50,000.00 | 200, Approved, decided by the Manager | PASS |
| C02 | Manager approves 50,000.01 (one cent over) | 403 Manager-limit reason; invoice unchanged | PASS |
| C03 | Director approves 50,000.01 | 200, Approved with one approval | PASS |
| C04 | Director approves exactly 500,000.00 | 200, Approved; no second approver needed | PASS |
| C05 | Manager approves exactly 500,000.00 | 403 Manager-limit reason; invoice unchanged | PASS |
| C06 | Admin approves a small invoice | 403 "Role Admin is not allowed..."; unchanged | PASS |
| C07 | Admin approves an invoice above 500,000 | 403 role reason; unchanged | PASS |
| C08 | Director gives the first approval on 500,000.01 | 200; still Pending Approval; "1 of 2"; no decider | PASS |
| C09 | The same Director approves again | 403 duplicate-user reason; still 1 approval | PASS |
| C10 | The Manager gives the second approval after a Director | 403 "second approver must be a Director"; still 1 approval | PASS |
| C11 | A different Director gives the second approval | 200, Approved, 2 approvals, decided by the second Director | PASS |
| C12 | Manager first, then a Director, on 500,000.01 | 200, Approved, 2 approvals | PASS |
| C13 | The same Manager approves twice on 500,000.01 | 403 duplicate-user reason; still 1 approval | PASS |
| C14 | A refused attempt, then a valid second approver | The valid approver still completes the invoice | PASS |
| C15 | Approve an already Approved invoice | 409 state error; unchanged | PASS |
| C16 | Approve a Draft invoice | 409 state error | PASS |
| C17 | Approve an invoice that does not exist | 404 not found | PASS |
| C18 | Reject a pending invoice with a reason | 200, Rejected, reason stored | PASS |
| C19 | Reject without a reason | 400; invoice stays pending | PASS |
| C20 | Reject an invoice that already has its first approval | 200, Rejected; first approval kept on record | PASS |
| C21 | Approve without signing in | 401 | PASS |
| C22 | Sign in with a wrong password | 401 "Invalid username or password." | PASS |
| C23 | Create invoices with 0, -5, 50000.001, 1e999999, NaN | 400 each; nothing stored; list still works | PASS |
| C24 | Delete as Manager, then as Admin | 403 for the Manager, 204 for the Admin | PASS |
| C25 | List filtered by status; unknown status | Only Approved invoices; 400 for an unknown status | PASS |

### How we know the script can fail

The script was also run against a deliberately broken rule (`<` changed to `<=` in the Manager limit rule). It then reported `24 of 25 cases passed` and failed C01 with the message "A Manager may approve invoices up to 50,000.00; this invoice is 50,000.00 and needs a Director." The file was restored and the run went back to 25 of 25.

## 4. Way B: the automated suites

Run each from the repository folder.

### B1. Unit and API tests (about 1 second)

```powershell
python -m pytest backend/tests -q
```

Expected: `177 passed`.

| Module | Tests | What it covers |
| --- | --- | --- |
| `test_approval_policy.py` | 63 | The pure rules: limits, boundaries, roles, the two negative rules, each rule class on its own |
| `test_approval_service.py` | 62 | The lifecycle, persistence, refusal leaves nothing changed, state errors, concurrency, injected policy and clock |
| `test_api.py` | 36 | Status codes, messages, sign-in, validation, JSON shape, injected collaborators |
| `test_repository_contract.py` | 16 | One contract that the fake and the in-memory repository must both pass |

To run only the two negative rules, verbosely:

```powershell
python -m pytest backend/tests/test_approval_policy.py -v -k "same_user or second_approver"
```

### B2. Which tests prove which rule

| Rule | Where it is tested |
| --- | --- |
| Manager up to and including 50,000 | `test_manager_may_approve_up_to_and_including_the_manager_limit`; service test at exactly the limit; API test for a small invoice |
| Manager refused above 50,000 | `test_manager_may_not_approve_above_the_manager_limit`; `test_manager_is_refused_one_cent_above_the_manager_limit_and_nothing_changes`; API 403 test |
| Director up to and including 500,000 | `test_director_may_approve_up_to_and_including_the_director_limit`; `test_director_approves_alone_at_exactly_the_director_limit` |
| Other roles never approve | `test_roles_other_than_manager_and_director_may_not_approve_anything`; Admin refusal tests at service and API level |
| Above 500,000 needs two approvals | `test_required_approvals_steps_up_only_above_the_director_limit`; `test_first_approval_above_the_director_limit_keeps_the_invoice_pending`; `test_second_distinct_director_completes_the_approval` |
| **Negative rule 1: same user never both approvers** | `test_same_user_cannot_be_both_approvers`; `test_same_user_is_recognised_despite_case_and_whitespace`; stored-side variants; `test_same_director_cannot_approve_twice_and_the_invoice_keeps_exactly_one_approval`; API `test_same_director_twice_gets_403_and_the_first_approval_stays_alone` |
| **Negative rule 2: second approver must be a Director** | `test_second_approver_who_is_a_manager_is_refused_with_a_reason`; `test_a_manager_as_second_approver_is_refused_and_nothing_changes`; API `test_manager_as_second_approver_gets_403` |
| Refusal changes nothing | Helper `assert_refused_and_unchanged` (reason text, invoice equals its copy, repository saw no save); `test_a_refused_approval_is_never_persisted`; API tests comparing the full invoice before and after |
| Two simultaneous approvals by one user | `test_two_simultaneous_approvals_by_the_same_user_record_exactly_one`; `test_simultaneous_double_click_by_one_director_approves_once` |
| Bad amounts rejected | `test_unusable_amounts_are_rejected_with_a_message_and_not_stored` |

### B3. Mutation tests (about 20 seconds, needs WSL)

```powershell
wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh check
Remove-Item docs\mutation\check.txt
```

Expected: `Mutation score: 100.0%`, 132 mutants, 132 killed, 0 survived. Before the feature the score was 63.9% (23 of 36 killed); see document 08 for the explanation.

### B4. End-to-end test with Playwright (about 15 seconds)

Make sure nothing is running on port 5000 first, then:

```powershell
cd e2e
npm install
npx playwright install chromium
npm test
cd ..
```

Expected: `1 passed`. To watch the browser: `npx playwright test --headed`. The test signs in as the Manager, presses Approve on the 75,000.00 invoice, expects the refusal message, and checks the invoice is still pending. It starts its own server and stops it afterwards.

## 5. Way C: try the cases by hand in the UI

Start the app fresh (`Ctrl+C`, then start it again) so the numbering below matches.

### C0. Create the test invoices once

1. Sign in as `demo.director` (password `ChangeMe123!`).
2. On the **Invoices** tab, fill **New invoice** (Customer name, Amount) and press **Create invoice**. The row appears as **Draft**.
3. Press **Submit for approval** in that row. It becomes **Pending Approval**.
4. Repeat for each invoice in this table. On a fresh server the ids are assigned in this order.

| Create this | Customer name (any) | Amount | Expected id |
| --- | --- | --- | --- |
| I1 | Case I1 | 50000.00 | INV-1006 |
| I2 | Case I2 | 50000.01 | INV-1007 |
| I3 | Case I3 | 500000.00 | INV-1008 |
| I4 | Case I4 | 500000.01 | INV-1009 |
| I5 | Case I5 | 500000.01 | INV-1010 |
| I6 | Case I6 | 500000.01 | INV-1011 |
| I7 | Case I7 | 500000.01 | INV-1012 |
| I8 | Case I8 | 100.00 | INV-1013 |

5. Press **Sign out**.

To act as a user: sign in, open the **Approvals** tab, and press **Approve** or **Reject** on the invoice. A red message appears after a refused attempt.

### C1. The cases

| # | Steps | Expected on screen |
| --- | --- | --- |
| M1 | `demo.manager`: Approve **INV-1006** (50,000.00) | Leaves the pending list; Invoices tab shows **Approved** |
| M2 | `demo.manager`: Approve **INV-1007** (50,000.01) | Red message "A Manager may approve invoices up to 50,000.00; this invoice is 50,000.01 and needs a Director."; still pending |
| M3 | `demo.director`: Approve **INV-1007** | Approved |
| M4 | `demo.manager`: Approve **INV-1008** (500,000.00); then `demo.director`: Approve it | Manager refused (same Manager-limit message); Director approves alone, Approved with no "1 of 2" |
| M5 | `demo.admin`: Approve **INV-1013** (100.00) | Red message "Role Admin is not allowed to approve invoices."; still pending |
| M6 | `demo.director`: Approve **INV-1009** | Stays in the list and shows **1 of 2 approvals** |
| M7 | Same Director: Approve **INV-1009** again | Red message "demo.director has already approved this invoice; invoices above 500,000.00 need two different approvers."; still 1 of 2 |
| M8 | `demo.manager`: Approve **INV-1009** | Red message "The second approver on an invoice above 500,000.00 must be a Director; demo.manager is a Manager."; still 1 of 2 |
| M9 | `demo.director2`: Approve **INV-1009** | Approved (this also shows a refused attempt does not block a valid one) |
| M10 | `demo.manager`: Approve **INV-1010**; then `demo.director`: Approve it | First shows 1 of 2; then Approved |
| M11 | `demo.manager`: Approve **INV-1011**; then `demo.manager`: Approve it again | First shows 1 of 2; second is refused with the duplicate-user message |
| M12 | `demo.director`: Approve **INV-1012** (1 of 2); `demo.admin`: type a reason, press **Reject** | Rejected; its first approval stays on record |
| M13 | `demo.manager`: on **INV-1013**, press **Reject** with the reason box empty | A message says a reason is required; still pending |
| M14 | Same invoice: type a reason (for example "Duplicate"), press **Reject** | Rejected |
| M15 | Open **INV-2001** (75,000.00) as `demo.manager` and approve | Refused (this is the case the Playwright test automates) |

### C2. Cases you cannot do by hand (and where they are tested)

| Case | Why not in the UI | Tested in |
| --- | --- | --- |
| Same user with different capitals or spaces (`Dir.One` versus ` dir.one `) | Usernames come from the fixed demo accounts | Policy and service unit tests (new-side and stored-side variants) |
| Two different Managers on a 500,000.01 invoice | There is only one Manager demo account | `test_two_different_managers_cannot_approve_above_the_director_limit` |
| Approve a Draft, an unknown id, or an already Approved invoice | The UI lists only pending invoices | Script cases C15 to C17; service and API tests |
| Delete an invoice; unusable amounts (0, negative, sub-cent, `1e999999`, NaN) | There is no Delete button, and the amount box rejects bad input in the browser | Script cases C23 and C24; API tests |
| Two simultaneous approvals | Needs real concurrency | Race tests (threaded) and the 4-click API test |

## 6. Checking an API call yourself (optional)

PowerShell, with the server running on port 5000:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:5000/api/auth/login -ContentType 'application/json' -Body '{"username":"demo.manager","password":"ChangeMe123!"}'
$headers = @{ Authorization = "Bearer $($login.token)" }
try { Invoke-RestMethod -Method Post -Uri http://localhost:5000/api/approvals/INV-2001/approve -Headers $headers }
catch { $_.ErrorDetails.Message }
```

The last line prints the refusal: `{"error":"A Manager may approve invoices up to 50,000.00; this invoice is 75,000.00 and needs a Director."}`.

## 7. Troubleshooting

| Problem | Fix |
| --- | --- |
| `pip install` or imports fail | Run the install command from the repository folder; use Python 3.10 or newer |
| "Address already in use" | Another server is on that port. Stop it or use `--port 5001` |
| UI shows old data or INV numbers differ from this guide | Restart the server for a fresh start |
| A manual try finds INV-2001 already approved | An earlier run approved it. Restart the server to reset the data. (The Playwright test creates its own invoice and passes regardless.) |
| Mutation run fails from Git Bash | Use PowerShell, or prefix `MSYS_NO_PATHCONV=1` |
| `try_all_cases.py` cannot start its server | Check nothing uses port 5058, or use `--port 5059`, or point it at a running server with `--url` |
| A case fails | Read the line under it starting with `->`: it shows the status and body received. Then open the matching test in the table in section 4 |

## 8. Quick checklist

- [ ] `python scripts/try_all_cases.py` gives `25 of 25 cases passed`
- [ ] `python -m pytest backend/tests -q` gives `177 passed`
- [ ] Mutation run gives `100.0%`
- [ ] `npm test` in `e2e` gives `1 passed`
- [ ] You tried M1 to M15 by hand (or at least M2, M7, M8, M9)
