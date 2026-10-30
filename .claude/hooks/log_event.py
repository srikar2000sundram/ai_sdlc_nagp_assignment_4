#!/usr/bin/env python3
"""Append one structured line per AI interaction to logs/ai-interactions.jsonl.

Wired to UserPromptSubmit, PostToolUse, SubagentStop and Stop in .claude/settings.json.
Every line has the same keys, in the same order (see ``FIELDS``), covering: the AI tool and model, the agent and its
mode, the request, skills / sub-agents / MCP tools / tools used, what the AI suggested, the human decision, how the
action was verified, limitations, status and the files touched. Empty facts are ``null`` or ``[]``, never missing.

Traceability: a prompt record gets an ``id``; every record that follows (tool calls, sub-agent reports, checks) lists it
in ``related_ids`` and ``parent_task``, so each action can be traced to the request that caused it.

Stdlib only. Never fails the session: any error is swallowed and the hook exits 0.

Manual use (to record work done outside a hook):
    log_event.py --manual EVENT "summary" [agent] [status]
    log_event.py --human  "decision or correction" ["what it was about"]
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_SUMMARY = 300
MAX_REQUEST = 700
MAX_SUGGESTION = 500

# The one record shape. Every record written by any hook or script has exactly these keys, in this order.
FIELDS = (
    "id", "timestamp", "session", "stage", "event",
    "agent", "agent_name", "agent_type", "ai_tool", "model", "mode",
    "related_ids", "parent_task", "context", "request", "summary",
    "skills_used", "subagents_used", "mcp_tools_used", "tools_used",
    "suggestion", "human_decision", "action_verification", "limitation",
    "status", "artifacts", "source",
)

SECRET_PATTERNS = [
    re.compile(r"(ghp_|gho_|github_pat_|sk-|xox[bp]-)[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*[=:]\s*\S+"),
]

# Claude Code reports its permission mode; map it to the four modes the log uses.
MODE_BY_PERMISSION = {"plan": "plan", "default": "agent", "acceptEdits": "edit", "auto": "agent", "bypassPermissions": "agent"}


def project_dir() -> Path:
    """The project folder: ``CLAUDE_PROJECT_DIR`` when Claude Code sets it, otherwise two levels above this file."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def local_path_forms() -> list[tuple[str, str]]:
    """(path text, placeholder) pairs, longest first, so the log never carries the user name or machine paths."""
    pairs = []
    for location, placeholder in ((project_dir(), "<repo>"), (Path.home(), "<home>")):
        text = str(location)
        for form in {text, text.replace("\\", "/"), "/" + text[0].lower() + text[2:].replace("\\", "/") if text[1:2] == ":" else text}:
            pairs.append((form, placeholder))
    return sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)


def clean(text: object, limit: int = MAX_SUMMARY) -> str:
    """Make text safe for the log: collapse whitespace, replace local paths and the account name, redact secrets, cap the
    length at ``limit`` characters.
    """
    value = " ".join(str(text or "").split())
    for path_text, placeholder in local_path_forms():
        value = value.replace(path_text, placeholder)
    account = Path.home().name
    for leftover in (account, account[:6].upper() + "~1"):
        value = re.sub("(?i)" + re.escape(leftover), "<user>", value)
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[redacted]", value)
    return value[: limit - 1] + "…" if len(value) > limit else value


def relative_path(path_text: object) -> str:
    """A file path relative to the project, with forward slashes (or the cleaned text when it is outside the project)."""
    text = str(path_text or "").replace("\\", "/")
    root = project_dir().as_posix()
    if text.lower().startswith(root.lower() + "/"):
        return text[len(root) + 1:]
    return clean(text)


def load_defaults() -> dict:
    """Tool, model and context from ``.claude/log-defaults.json``; hooks cannot see the model, so the file names it."""
    defaults = {"ai_tool": "Claude Code", "model": "unknown", "context": "AI in SDLC assignment"}
    try:
        defaults.update(json.loads((project_dir() / ".claude" / "log-defaults.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return defaults


def now_utc() -> datetime:
    """The current time in UTC, to the second."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def make_id(moment: datetime, agent: str, event: str, salt: str) -> str:
    """A readable unique id: ``20261019T063542Z-main-userpromptsubmit-3fa9c1``."""
    digest = hashlib.sha1(f"{moment.isoformat()}{agent}{event}{salt}{os.getpid()}".encode()).hexdigest()[:6]
    return f"{moment.strftime('%Y%m%dT%H%M%SZ')}-{agent}-{event.lower()}-{digest}"


def new_record(**fields) -> dict:
    """Build a full record: the defaults for every key in ``FIELDS``, overridden by ``fields``.

    Args:
        **fields: any of the keys in ``FIELDS``. ``event`` is required; ``timestamp`` defaults to now.

    Returns:
        A dict with exactly the keys in ``FIELDS``, in that order.
    """
    defaults = load_defaults()
    moment = now_utc()
    agent = fields.get("agent", "main")
    record = {
        "id": "", "timestamp": moment.isoformat().replace("+00:00", "Z"), "session": "", "stage": "general",
        "event": "unknown", "agent": agent, "agent_name": "claude-code-main-agent", "agent_type": "built-in",
        "ai_tool": defaults["ai_tool"], "model": defaults["model"], "mode": "agent",
        "related_ids": [], "parent_task": None, "context": defaults["context"], "request": None, "summary": "",
        "skills_used": [], "subagents_used": [], "mcp_tools_used": [], "tools_used": [],
        "suggestion": None, "human_decision": None, "action_verification": None, "limitation": None,
        "status": "applied", "artifacts": [], "source": "hook",
    }
    record.update(fields)
    if not record["id"]:
        stamp = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        record["id"] = make_id(stamp, record["agent"], record["event"], record["summary"])
    return {key: record[key] for key in FIELDS}


def describe_tool(name: str, tool_input: dict) -> str:
    """One short line describing a tool call (the file for Edit/Read, the command for Bash, and so on)."""
    if name in ("Edit", "Write", "Read", "NotebookEdit"):
        return f"{name} {relative_path(tool_input.get('file_path', ''))}"
    if name in ("Bash", "PowerShell"):
        return clean(tool_input.get("command", ""))
    if name in ("Glob", "Grep"):
        return f"{name} {tool_input.get('pattern', '')}"
    if name == "Agent":
        return f"spawn {tool_input.get('subagent_type', 'general-purpose')}: {tool_input.get('description', '')}"
    if name == "Skill":
        return f"skill {tool_input.get('skill', '')}"
    return clean(json.dumps(tool_input, default=str))


def tool_outcome(response: object) -> str:
    """``ok`` or ``error`` from a tool's response."""
    if isinstance(response, dict):
        if response.get("is_error") or response.get("error") or response.get("interrupted"):
            return "error"
        return "ok"
    return "error" if isinstance(response, str) and response.lower().startswith("error") else "ok"


def infer_stage(tool: str, tool_input: dict) -> str:
    """Which lifecycle stage a tool call belongs to, from the file it touches or the command it runs."""
    # Use the project-relative path: a folder name above the project (a temp dir named "pytest-...") must not decide the stage.
    target = (relative_path(tool_input.get("file_path", "")) + " " + str(tool_input.get("command", ""))).replace("\\", "/").lower()
    rules = (
        ("mutmut", "mutation-testing"), ("run_mutation", "mutation-testing"), ("docs/mutation", "mutation-testing"),
        ("specs/", "specification"), (".specify", "specification"), ("speckit", "specification"),
        ("playwright", "e2e-testing"), ("/e2e/", "e2e-testing"),
        ("pytest", "testing"), ("backend/tests", "testing"),
        (".claude", "setup"), ("agents.md", "setup"), ("claude.md", "setup"),
        ("backend/src", "implementation"),
        ("git ", "version-control"),
        ("docs/", "documentation"), (".md", "documentation"), ("build_docs", "documentation"),
    )
    if tool == "Skill":
        return "setup"
    for needle, stage in rules:
        if needle in target:
            return stage
    return "general"


def agent_kind(name: str) -> str:
    """``custom`` when the sub-agent is defined in ``.claude/agents``, otherwise ``built-in``."""
    return "custom" if (project_dir() / ".claude" / "agents" / f"{name}.md").exists() else "built-in"


def skill_kind(name: str) -> str:
    """``custom`` when the skill lives in ``.claude/skills``, otherwise ``built-in``."""
    return "custom" if (project_dir() / ".claude" / "skills" / name / "SKILL.md").exists() else "built-in"


def capabilities_used(tool: str, tool_input: dict, outcome: str) -> dict:
    """The skills, sub-agents and MCP tools a tool call used, in the log's nested shapes."""
    found = {"skills_used": [], "subagents_used": [], "mcp_tools_used": []}
    if tool == "Skill":
        name = str(tool_input.get("skill", ""))
        found["skills_used"].append({
            "name": name, "type": skill_kind(name.split(":")[-1]),
            "purpose": clean(tool_input.get("args") or "applied the skill's instructions", 120), "invocation": "explicit",
        })
    elif tool in ("Agent", "Task"):
        name = str(tool_input.get("subagent_type") or "general-purpose")
        found["subagents_used"].append({
            "name": name, "type": agent_kind(name), "task": clean(tool_input.get("description", ""), 120),
            "status": "failed" if outcome == "error" else "completed",
        })
    elif tool.startswith("mcp__"):
        parts = tool.split("__")
        found["mcp_tools_used"].append({
            "server": parts[1] if len(parts) > 1 else "", "tool": "__".join(parts[2:]),
            "purpose": clean(json.dumps(tool_input, default=str), 120),
        })
    return found


def state_file() -> Path:
    """Where the latest human prompt is remembered, so later records can point back to it."""
    return project_dir() / "logs" / ".state.json"


def last_prompt() -> dict:
    """``{"id", "request"}`` of the latest human prompt, or empty when none is remembered."""
    try:
        return json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def remember_prompt(record_id: str, request: str) -> None:
    """Remember the latest human prompt for the records that follow."""
    state_file().parent.mkdir(parents=True, exist_ok=True)
    state_file().write_text(json.dumps({"id": record_id, "request": request}), encoding="utf-8")


def is_system_message(prompt: str) -> bool:
    """True for text the harness injects as a "prompt" (a sub-agent hand-back, a task notification), not human input."""
    return prompt.lstrip().startswith("<") and any(tag in prompt[:60] for tag in ("agent-message", "task-", "system-"))


def agent_fields(data: dict) -> dict:
    """The agent identity fields: the main Claude Code agent, or a sub-agent when the hook payload names one."""
    name = data.get("agent_type") or ""
    return {
        "agent": name or "main",
        "agent_name": name or "claude-code-main-agent",
        "agent_type": "sub-agent" if name else "built-in",
        "mode": MODE_BY_PERMISSION.get(data.get("permission_mode", "default"), "agent"),
        "session": str(data.get("session_id", ""))[:8],
    }


def build_record(data: dict) -> dict:
    """Turn a hook payload into one full log record (see ``FIELDS``)."""
    event = data.get("hook_event_name", "unknown")
    identity = agent_fields(data)
    prompt = last_prompt()
    link = {"related_ids": [prompt["id"]] if prompt.get("id") else [], "parent_task": prompt.get("id"),
            "request": prompt.get("request")}

    if event == "UserPromptSubmit":
        text = clean(data.get("prompt", ""), MAX_REQUEST)
        system = is_system_message(data.get("prompt", ""))
        fields = {**identity, "event": event, "stage": "interaction", "request": text, "summary": clean(text),
                  "status": "received"}
        if system:
            # Harness text (a sub-agent hand-back): not human input, so link it to the prompt that caused it.
            fields.update(link, agent_name="harness", request=text)
        record = new_record(**fields)
        if not system:
            remember_prompt(record["id"], text)
        return record

    if event == "PostToolUse":
        tool, tool_input = data.get("tool_name", ""), data.get("tool_input") or {}
        outcome = tool_outcome(data.get("tool_response"))
        artifacts = [relative_path(tool_input["file_path"])] if tool in ("Edit", "Write", "NotebookEdit") and "file_path" in tool_input else []
        return new_record(**identity, **link, event=event, stage=infer_stage(tool, tool_input),
                          summary=describe_tool(tool, tool_input), tools_used=[tool], artifacts=artifacts,
                          status="failed" if outcome == "error" else "applied",
                          limitation="the tool reported an error" if outcome == "error" else None,
                          **capabilities_used(tool, tool_input, outcome))

    if event in ("SubagentStop", "Stop"):
        message = data.get("last_assistant_message") or data.get("stop_reason") or ""
        return new_record(**identity, **link, event=event, stage="review" if event == "SubagentStop" else "general",
                          summary=clean(message), suggestion=clean(message, MAX_SUGGESTION), status="completed")

    return new_record(**identity, **link, event=event, summary=clean(json.dumps(
        {k: v for k, v in data.items() if k != "transcript_path"}, default=str)))


def append(record: dict) -> None:
    """Append one record to ``logs/ai-interactions.jsonl`` with a single binary write so parallel hooks never interleave
    lines.
    """
    log_file = project_dir() / "logs" / "ai-interactions.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    # One binary append per record: parallel hooks (subagents) cannot interleave partial lines.
    with log_file.open("ab") as handle:
        handle.write(line)


def main() -> None:
    """Read the hook payload from stdin and log it; or, with ``--manual`` / ``--human``, log what the command line says."""
    if len(sys.argv) >= 3 and sys.argv[1] == "--human":
        prompt = last_prompt()
        append(new_record(
            session="manual", event="HumanDecision", agent="human", agent_name="human", agent_type="human",
            stage="oversight", related_ids=[prompt["id"]] if prompt.get("id") else [], parent_task=prompt.get("id"),
            request=clean(sys.argv[3], MAX_REQUEST) if len(sys.argv) > 3 else prompt.get("request"),
            summary=clean(sys.argv[2]), human_decision=clean(sys.argv[2], MAX_SUGGESTION), status="recorded",
            source="manual"))
        return
    if len(sys.argv) >= 4 and sys.argv[1] == "--manual":
        append(new_record(
            session="manual", event=sys.argv[2], agent=sys.argv[4] if len(sys.argv) > 4 else "main",
            summary=clean(sys.argv[3]), status=sys.argv[5] if len(sys.argv) > 5 else "applied", source="manual"))
        return
    append(build_record(json.load(sys.stdin)))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # logging must never break the session
        pass
    sys.exit(0)
