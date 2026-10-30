---
name: review-findings
description: The one structured format for code-review findings and the three allowed verdicts (fixed, dismissed, deferred). Load when reviewing a diff or writing a PR description.
---

# Review findings format

A reviewer answers with exactly one fenced JSON array. Keys are exactly these five:

```json
[
  {
    "id": "F1",
    "severity": "high",
    "location": "backend/src/invoice_app/domain/approval_service.py:42",
    "issue": "What is wrong and how it fails, in one or two sentences.",
    "suggestion": "The smallest change that fixes it."
  }
]
```

- `severity`: `high` (wrong behaviour or security hole), `medium` (likely bug, weak test), `low` (style, clarity).
- `location`: `path:line`.
- Use `[]` when nothing is wrong. A `SubagentStop` hook (`.claude/hooks/validate_review.py`) blocks any other shape.

# Author verdicts (added in the PR description, never by the reviewer)

Every finding gets exactly one verdict:

| Verdict | Needs |
| --- | --- |
| **fixed** | the commit or change that fixed it |
| **dismissed** | a reason why it is not a problem (cite code, spec or a test) |
| **deferred** | a reason why not now, and where it is tracked |

PR description table: `| id | severity | location | finding | verdict | reason / fix |`
