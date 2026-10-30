#!/usr/bin/env python3
"""PostToolUse hook for Bash: turn test/mutation/e2e output into ONE identically formatted line.

    CHECK <name> | <metric>=<value> ... | result=<pass|fail>

The line is handed back to the agent as additionalContext and also appended to the AI log, so every
run of pytest, mutmut or Playwright is reported in the same shape no matter who ran it.
"""

import json
import re
import sys

sys.path.insert(0, __file__.rsplit("hooks", 1)[0] + "hooks")
from log_event import agent_fields, append, clean, infer_stage, last_prompt, new_record  # noqa: E402


def first_int(pattern: str, text: str) -> int:
    """The first captured integer in the text, or 0 when the pattern does not match."""
    match = re.search(pattern, text)
    return int(match.group(1)) if match else 0


def summarize(command: str, output: str) -> str | None:
    """Turn pytest, mutmut or Playwright output into one ``CHECK <name> | metrics | result=pass|fail`` line, or ``None``
    for other commands.
    """
    if "run_mutation" in command or "mutmut" in command:
        score = re.search(r"Mutation score:\s*([\d.]+)%", output)
        if not score:
            return None
        killed, survived = first_int(r"Killed\s*:\s*(\d+)", output), first_int(r"Survived\s*:\s*(\d+)", output)
        return f"CHECK mutation | killed={killed} survived={survived} score={score.group(1)}% | result={'pass' if survived == 0 else 'fail'}"
    if "playwright" in command or "npm test" in command:
        passed, failed = first_int(r"(?<![=\w])(\d+) passed", output), first_int(r"(?<![=\w])(\d+) failed", output)
        if not (passed or failed):
            return None
        return f"CHECK e2e | passed={passed} failed={failed} | result={'pass' if failed == 0 and passed else 'fail'}"
    if "pytest" in command:
        passed, failed = first_int(r"(?<![=\w])(\d+) passed", output), first_int(r"(?<![=\w])(\d+) failed", output)
        errors = first_int(r"(?<![=\w])(\d+) errors?", output)
        # Only pytest's own final line ("177 passed in 1.1s") counts; a command that merely mentions pytest does not.
        if not re.search(r"\d+ (passed|failed|errors?)\b[^\n]* in [\d.]+s", output):
            return None
        if not (passed or failed or errors):
            return None
        return f"CHECK pytest | passed={passed} failed={failed} errors={errors} | result={'pass' if failed == 0 and errors == 0 and passed else 'fail'}"
    return None


def main() -> None:
    """After a Bash or PowerShell call, log the check summary and hand it back to the agent as extra context."""
    data = json.load(sys.stdin)
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return
    command = (data.get("tool_input") or {}).get("command", "")
    response = data.get("tool_response")
    output = response if isinstance(response, str) else "\n".join(
        str(response.get(key, "")) for key in ("stdout", "stderr", "output")
    ) if isinstance(response, dict) else ""
    line = summarize(command, output)
    if line is None:
        return

    passed = line.endswith("result=pass")
    prompt = last_prompt()
    append(new_record(
        **agent_fields(data),
        event="CheckSummary", stage=infer_stage(data.get("tool_name", ""), data.get("tool_input") or {}),
        related_ids=[prompt["id"]] if prompt.get("id") else [], parent_task=prompt.get("id"),
        request=prompt.get("request"), summary=clean(line), tools_used=[data.get("tool_name", "")],
        action_verification=clean(line), status="verified" if passed else "failed",
        limitation=None if passed else "a check failed; see the metrics in the summary",
    ))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": line}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
