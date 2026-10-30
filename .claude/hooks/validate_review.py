#!/usr/bin/env python3
"""SubagentStop hook: the pr-reviewer agent must answer in the one structured findings format.

Accepted answer: a ```json fenced array (possibly empty) of objects with exactly the keys
    id (F1, F2, ...), severity (high|medium|low), location (path:line), issue, suggestion
If the answer does not parse or breaks the schema, the subagent is blocked from stopping and told why,
so the review always comes back in the same shape. Skills/agents: see .claude/skills/review-findings.
"""

import json
import re
import sys

REQUIRED_KEYS = {"id", "severity", "location", "issue", "suggestion"}
SEVERITIES = {"high", "medium", "low"}


def extract_json(message: str):
    """Return the parsed content of the first ```json block, or ``None`` when there is none."""
    match = re.search(r"```json\s*(.*?)```", message, re.DOTALL)
    return json.loads(match.group(1)) if match else None


def problems(message: str) -> list[str]:
    """Everything wrong with a reviewer's answer against the findings schema; an empty list means it is valid."""
    try:
        findings = extract_json(message)
    except json.JSONDecodeError as error:
        return [f"the ```json block is not valid JSON ({error.msg})"]
    if findings is None:
        return ["no ```json fenced block found"]
    if not isinstance(findings, list):
        return ["the JSON must be an array of findings (use [] when there are none)"]

    found = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict) or set(finding) != REQUIRED_KEYS:
            found.append(f"finding {index} must have exactly the keys {sorted(REQUIRED_KEYS)}")
            continue
        if not re.fullmatch(r"F\d+", str(finding["id"])):
            found.append(f"finding {index}: id must look like F1, F2, ...")
        if finding["severity"] not in SEVERITIES:
            found.append(f"finding {index}: severity must be one of {sorted(SEVERITIES)}")
        if not re.search(r".+:\d+", str(finding["location"])):
            found.append(f"finding {index}: location must look like path/to/file.py:123")
    return found


def main() -> None:
    """Block the pr-reviewer agent from finishing until its answer follows the findings format."""
    data = json.load(sys.stdin)
    if data.get("agent_type") != "pr-reviewer" or data.get("stop_hook_active"):
        return
    message = data.get("last_assistant_message") or ""
    issues = problems(message)
    if issues:
        print(json.dumps({
            "decision": "block",
            "reason": "Review output rejected: " + "; ".join(issues) + ". Re-send using the review-findings format.",
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
