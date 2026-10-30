# Feature Specification: Approval Limits by Role

**Feature Branch**: `001-invoice-approval-limits`

**Created**: 2026-10-16

**Status**: Implemented

**Input**: User description: "Add approval limits by role to the invoice approval service. A Manager may approve invoices up to 50,000. A Director may approve invoices up to 500,000. Anything above 500,000 needs two distinct approvers, and the second approver must be a director. The same user may never count as both approvers on one invoice. A rejected attempt returns a clear reason, and nothing about the invoice changes."

## Clarifications

### Session 2026-10-16

- Q: Are the limits inclusive? → A: Yes. "Up to 50,000" means 50,000.00 is allowed and 50,000.01 is not. Likewise 500,000.00 is a single-Director invoice and 500,000.01 needs two approvers.
- Q: Who may give the *first* approval above 500,000? → A: A Manager or a Director. The requirement only constrains the second approver. (Ambiguity flagged; this is the least-restrictive reading of the text.)
- Q: What does "the same user" mean? → A: The same account, compared after trimming whitespace and ignoring case, so `Dir.One` and ` dir.one ` are one user.
- Q: Which check wins when the same Manager tries to approve twice? → A: The duplicate-user reason is reported (it is the more specific problem).
- Q: What happens to the legacy `Approver` role? → A: It is replaced by `Manager`. `Admin` keeps destructive and reject powers but has **no approval authority**.
- Q: What does "a rejected attempt" mean — the existing Reject action? → A: No. It means *an approval attempt that the rules refuse*. The existing explicit Reject action is unchanged.
- Q: Does a partial (first) approval count as a change that a later refusal might undo? → A: A refused attempt never writes anything. A first approval that was accepted stays recorded.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Limit each approver to their role's amount (Priority: P1)

A Manager can approve everyday invoices; larger ones need a Director. People should learn immediately why a request was refused.

**Why this priority**: It is the core control. Without it every approver can approve any amount.

**Independent Test**: Approve invoices of 50,000.00, 50,000.01 and 500,000.00 as a Manager and as a Director; check results and that refused attempts leave the invoice untouched.

**Acceptance Scenarios**:

1. **Given** a pending invoice of 50,000.00, **When** a Manager approves it, **Then** it becomes Approved and records the Manager as decider.
2. **Given** a pending invoice of 50,000.01, **When** a Manager approves it, **Then** the attempt is refused with a reason naming the 50,000.00 Manager limit and the invoice is unchanged.
3. **Given** a pending invoice of 500,000.00, **When** a Director approves it, **Then** it becomes Approved with that single approval.
4. **Given** a pending invoice of any amount, **When** an Admin (or any role that is not Manager/Director) tries to approve it, **Then** it is refused with a reason and nothing changes.

---

### User Story 2 - Two distinct approvers above 500,000 (Priority: P1)

Very large invoices need a second pair of eyes, who must be a Director and a different person.

**Why this priority**: Highest-risk invoices; this is where a plausible-looking implementation most often breaks (e.g. one user approving twice).

**Independent Test**: Create a 600,000.00 invoice; approve with Director A (stays Pending, one approval), approve again with Director A (refused), with a Manager (refused), then with Director B (Approved).

**Acceptance Scenarios**:

1. **Given** a pending invoice of 500,000.01, **When** a Director approves it, **Then** it stays Pending Approval with exactly one recorded approval and no decider.
2. **Given** that invoice with one approval, **When** a *different* Director approves, **Then** it becomes Approved and both approvals are recorded.
3. **Given** that invoice with one approval by user X, **When** X approves again (including `X` in different case or with surrounding spaces), **Then** it is refused with a reason and the invoice still has exactly one approval.
4. **Given** that invoice with one approval, **When** a Manager tries to give the second approval, **Then** it is refused with a reason saying the second approver must be a Director.
5. **Given** a pending invoice of 500,000.01, **When** a Manager gives the first approval and a Director the second, **Then** it becomes Approved.

---

### User Story 3 - Refusals are visible in the UI and change nothing (Priority: P2)

A user who clicks Approve on an over-limit invoice sees the reason on screen and the invoice stays pending.

**Why this priority**: The rule is only useful if people can see why; also proves the rule through the real UI.

**Independent Test**: Playwright: sign in as the demo Manager, click Approve on the 75,000.00 invoice, read the alert, confirm the invoice is still Pending Approval.

**Acceptance Scenarios**:

1. **Given** the signed-in demo Manager and a pending 75,000.00 invoice, **When** they click Approve, **Then** an alert shows the Manager-limit reason and the invoice remains in the pending list and shows "Pending Approval".
2. **Given** a pending invoice above 500,000, **When** the first approval is recorded, **Then** the pending list shows "1 of 2 approvals".

### Edge Cases

- Exactly 50,000.00, 50,000.01, 500,000.00 and 500,000.01 (inclusive limits; one cent either side).
- Same user with different case/whitespace as the second approver.
- Second approver is a Manager; first approver is a Manager.
- Approving an invoice that is already Approved, Rejected or Draft (existing state errors still apply; nothing changes).
- A refused attempt followed by a valid attempt by someone else still works.
- Explicitly rejecting a partially approved invoice still works.
- Blank username on an approver is invalid.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A Manager MUST be able to approve an invoice whose amount is ≤ 50,000.00.
- **FR-002**: A Director MUST be able to approve an invoice whose amount is ≤ 500,000.00.
- **FR-003**: An invoice with amount > 500,000.00 MUST require two approvals from two distinct users; it stays Pending Approval after the first and becomes Approved after the second.
- **FR-004**: The second approver of an invoice > 500,000.00 MUST have the Director role. The first MAY be a Manager or a Director.
- **FR-005**: The same user MUST NOT count as both approvers; usernames are compared trimmed and case-insensitively.
- **FR-006**: Roles other than Manager and Director MUST NOT be able to approve any invoice.
- **FR-007**: A refused approval MUST return a clear, specific reason (HTTP 403 with `{"error": "<reason>"}`) and MUST leave the invoice completely unchanged (status, decider, decision time, recorded approvals).
- **FR-008**: Each accepted approval MUST be recorded with the approver's username, role and a UTC timestamp.
- **FR-009**: Existing behaviours (submit, explicit reject with required reason, 404/409/400 mapping, Admin-only delete) MUST keep working.
- **FR-010**: The UI MUST show a refusal reason and, for invoices needing two approvals, how many approvals are recorded.

### Key Entities

- **Approver**: username + role of the person acting. Username must not be blank.
- **ApprovalRecord**: one accepted approval (username, role, UTC time) stored on the invoice.
- **Invoice**: existing entity, now carrying an ordered list of ApprovalRecords; `requiredApprovals` is derived from its amount.
- **ApprovalPolicy**: pure rules deciding allowed / refused-with-reason from amount, approver and earlier approvals.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every rule in FR-001..FR-007 has at least one passing positive test and, for each "MUST NOT" rule, a negative test asserting both the reason and an unchanged invoice.
- **SC-002**: All four limit boundaries (50,000.00 / .01 and 500,000.00 / .01) are covered on both sides.
- **SC-003**: Mutation score of the domain package does not regress and ends at ≥ 90% with every survivor explained.
- **SC-004**: One Playwright test demonstrates a refused over-limit approval through the UI.

## Assumptions

- Currency is a single unspecified unit; amounts are exact decimals.
- Sign-in and roles come from the existing demo accounts (`demo.manager`, `demo.director`, `demo.director2`, `demo.admin`); there is no user management.
- Storage stays in memory; concurrency beyond the existing repository lock is out of scope (see deferred review finding).
- Notification of the first approver or of Directors is out of scope.
