# .claude

Everything that configures AI coding agents for this project.

| Path | What it is |
| --- | --- |
| `settings.json` | Wires the hooks to Claude Code events |
| `agents/` | Five project agents: `spec-writer`, `implementer`, `test-reviewer`, `pr-reviewer`, `mutation-analyst` |
| `skills/` | `approval-rules`, `review-findings`, `run-checks` and the Spec Kit `speckit-*` skills |
| `hooks/` | Python hooks that log every interaction and check outputs |

## Agents

| Agent | Access | Job |
| --- | --- | --- |
| `spec-writer` | read, write | Writes Spec Kit artifacts; never touches source |
| `implementer` | read, write, shell | Implements one task group at a time, tests first |
| `test-reviewer` | read-only | Finds tests that cannot fail |
| `pr-reviewer` | read-only | Reviews the diff and answers only in the findings JSON format |
| `mutation-analyst` | read-only | Classifies surviving mutants and proposes tests |

## Hooks

| Event | Hook | Effect |
| --- | --- | --- |
| UserPromptSubmit, PostToolUse, Stop | `log_event.py` | Appends one JSON line to `logs/ai-interactions.jsonl` |
| PostToolUse (shell) | `check_summary.py` | Turns pytest, mutmut and Playwright output into `CHECK <name> \| metrics \| result=pass/fail` |
| SubagentStop | `validate_review.py` | Blocks a `pr-reviewer` answer that is not the findings schema |

Every log line has the same 27 keys (`FIELDS` in `hooks/log_event.py`): `id, timestamp, session, stage, event, agent, agent_name, agent_type, ai_tool, model, mode, related_ids, parent_task, context, request, summary, skills_used, subagents_used, mcp_tools_used, tools_used, suggestion, human_decision, action_verification, limitation, status, artifacts, source`. A prompt gets an `id`; every action after it carries that id in `related_ids` and `parent_task`, so each edit, command and check can be traced to the request that caused it. Local paths, the account name and secrets are removed before writing. Hooks never fail a session: any error is swallowed.

`log-defaults.json` names the AI tool, model and context (hooks cannot see the model). Record a human decision or correction with `python .claude/hooks/log_event.py --human "what I decided"`.

Check the log and write the readable summary: `python scripts/summarize_log.py` (writes `logs/ai-interactions-summary.md`; `--check` only validates). Test the hook: `python -m pytest .claude/hooks -q`.

## Notes

- Project agents are registered when a session starts, so a newly created agent is available from the next session.
- `settings.local.json` is machine-specific and git-ignored.
- Details: `docs/guides/10-ai-workflow-guide.md`.
