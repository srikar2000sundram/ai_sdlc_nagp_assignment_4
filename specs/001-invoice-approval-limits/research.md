# Research & Decisions

| Decision | Choice | Rationale | Rejected alternative |
| --- | --- | --- | --- |
| Money type | `decimal.Decimal` | Exact comparison at 50,000.00 / .01 boundaries | `float` (0.01 steps are inexact) |
| Where rules live | Pure function `rejection_reason(amount, approver, prior)` | Easy to unit test and mutation-test without a repository | Logic inside `ApprovalService.approve` |
| Refusal signal | `ApprovalNotPermittedError(reason)` → 403 | Distinct from 409 (wrong state) and 400 (bad input) | Reusing `InvalidStateError` |
| No partial writes | Check first, then mutate | The in-memory repository returns the same object; mutating before checking would leak state | Roll back after failure |
| "Same user" | `strip().casefold()` | Stops `Dir.One` vs ` dir.one ` bypass | Exact string equality |
| Approvals storage | `list[ApprovalRecord]` replaced, not appended in place | A new list is assigned only after all checks pass | In-place append |
| Mutation tool | `mutmut` 3 in WSL | Needs `fork()`; unavailable natively on Windows | cosmic-ray (heavier config) |
| Python port | FastAPI | Mirrors ASP.NET controller/service split | Flask (less typing support) |
