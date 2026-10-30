# Submission Checklist and Gap Audit

Checked against `AI-in-SDLC-Home Assignment_1.pdf` on 2026-10-16. "Done" means it exists in the working tree and was verified in this session; "Open" means it needs action from you.

## 1. The "What to do" list

| # | Requirement | Status | Evidence / what is left |
| --- | --- | --- | --- |
| 1 | Fork the repo; extend AGENTS.md; **show that context matters** | Fork: **Open**. AGENTS.md: Done. Context demonstration: Done (added in this audit) | `AGENTS.md`; cold-versus-context comparison in `ASSIGNMENT.md` section 7. You still need to fork on GitHub |
| 2 | Skills for the agents | Done | `.claude/skills/{approval-rules,review-findings,run-checks}` |
| 3 | Hooks for structured, same-format output | Done | `.claude/settings.json`, `.claude/hooks/*.py`; every log line has the same 27 keys (tool, model, agent, mode, prompt, skills, sub-agents, MCP, human decision, verification, status, files); readable summary in `logs/ai-interactions-summary.md` |
| 4 | Spec-driven tool; commit the generated files | Files: Done. Commit: **Open** | `.specify/`, `specs/001-invoice-approval-limits/` |
| 5 | Implement in at least two steps, each its own commit with what and why | Built in that order; commits: **Open** | Suggested sequence in `ASSIGNMENT.md` section 5. Steps 4 and 5 share files, so use `git add -p` or combine |
| 6a | Unit tests for the approval rules; review every generated test | Done | 177 pass; `test-reviewer` pass recorded in `docs/pr-review.md` |
| 6b | One Playwright test for a rejected over-limit approval | Done | `e2e/tests/over-limit-rejection.spec.ts` passes |
| 7 | Review your own PR with the agent; verdict on every finding in the description | Review and verdicts: Done. PR itself: **Open** | `docs/pr-review.md` is the description. See note on the "workshop review prompt" below |
| 8 | Log all AI interactions via skills/hooks | Done | `logs/ai-interactions.jsonl`, 189 lines at audit time |
| 9 | Multiple agents and sub-agents | Done | 5 project agents; general-purpose subagents ran the reviewer roles |

## 2. The "What to hand in" list

| # | Deliverable | Status |
| --- | --- | --- |
| 1 | PR on your fork with at least three commits that each stand alone | **Open** (nothing committed, as instructed) |
| 2 | Updated AGENTS.md | Done |
| 3 | Specification files from the spec tool | Done (uncommitted) |
| 4 | Unit tests for every rule including both negative rules | Done |
| 5 | One Playwright test | Done |
| 6 | Mutation scores before and after as text in the write-up | Done: 63.9% to 100%, text blocks in `ASSIGNMENT.md` section 3 |
| 7 | PR description listing every finding with a verdict | Done as text; paste into the PR when opened |
| 8 | Log file of AI interaction | Done |
| 9 | `ASSIGNMENT.md` at the repository root with write-up and video link | Write-up: Done. Video link: Done (pasted at the top of `ASSIGNMENT.md`) |
| 10 | The 8 to 10 minute demo video, uploaded and linked | A 9.5 minute draft exists (`docs/video/demo-narrated.mp4`, plus a captions-only copy). **Open:** watch it, upload it and paste the link. Script: document 15 |

## 3. Things that were missing and what was done about them

| Gap found in this audit | Action |
| --- | --- |
| No demonstration that the context file matters (assignment item 1) | Ran a comparison and recorded it honestly, including a failed first attempt. See `ASSIGNMENT.md` section 7 |
| The interaction log contained the user name, the employer folder name and local machine paths | Redacted all 189 lines; `log_event.py` now replaces the project path, the home path, the account name and its short form with placeholders before writing |
| Mutation run time was unknown for planning the video | Measured: a full run is about 19 seconds end to end |
| ASSIGNMENT.md did not mention the PDF documentation | Added |

## 4. Open items that are yours

1. **Fork** `NITIN1670/ai-sdlc-demo-app` on GitHub, then point this working tree at your fork (this folder tracks `upstream/main`).
2. **Commit in steps** and push to a branch on the fork; open the PR with `docs/pr-review.md` as the description.
3. ~~Record the video and paste the link into `ASSIGNMENT.md`.~~ Done.
4. Decide what to do with the assignment PDF in the repo root (untracked): leave it out of the commits or add it.
5. Rebuild the PDF documentation after pasting the link: `python scripts/build_docs.py`.

## 5. Things to be aware of

| Topic | Note |
| --- | --- |
| Workshop review prompt | The assignment says to run "the review prompt from the workshop". No such prompt file exists in the upstream repo, so the review used the `pr-reviewer` agent's own prompt (`.claude/agents/pr-reviewer.md`). If your workshop gave you a prompt, run it once against the diff after the PR is open and add any new findings to the table |
| AI tool | The assignment suggests free-tier GitHub Copilot but allows alternatives that meet compliance. This work used Claude Code. State that this is acceptable in your organisation if asked |
| "All AI interactions" | The hooks log prompts (as summaries), every tool call, sub-agent completions and test results. They do not store the full text of model replies |
| Reconstructed log lines | The first 12 lines are marked `source: "reconstructed"`: planning and the port happened before the hooks existed |
| Agents ran as general-purpose | Project agents were not selectable by name in the session that created them |
| Commit sequence | The tree was built and tested in the right order, but intermediate states were not kept, so commits 4 and 5 need `git add -p` |
| Language | The assignment allows any language; the upstream is C#, so the backend is a Python port, which is stated in the write-up |
| Generated video | The draft video is produced by `scripts/make_demo_video.py`: every command runs live while it is recorded, but the voice is a synthetic Windows voice and the narration says the recording was produced by a script. If your reviewer expects your own voice, re-record with document 15 |
| Stryker note | The assignment's Stryker install note applies to .NET only; mutmut was used instead |
