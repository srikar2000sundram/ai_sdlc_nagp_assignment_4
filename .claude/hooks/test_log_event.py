"""Tests for the AI-interaction logging hook (`log_event.py`): one fixed record shape, traceable links. Run with `python -m pytest .claude/hooks -q`."""

import importlib.util
import json
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent / "log_event.py"


@pytest.fixture
def hook(tmp_path, monkeypatch):
    """The hook module, pointed at an empty temporary project so tests never touch the real log."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("log_event_under_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_record_has_exactly_the_schema_keys_in_order(hook):
    record = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "x.py"}})
    assert tuple(record) == hook.FIELDS


def test_a_prompt_is_remembered_and_later_records_point_back_to_it(hook):
    prompt = hook.build_record({"hook_event_name": "UserPromptSubmit", "prompt": "add approval limits"})
    action = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "Edit",
                                "tool_input": {"file_path": "backend/src/x.py"}})
    assert action["related_ids"] == [prompt["id"]]
    assert action["parent_task"] == prompt["id"]
    assert action["request"] == "add approval limits"


def test_plan_permission_mode_is_logged_as_plan_mode(hook):
    record = hook.build_record({"hook_event_name": "UserPromptSubmit", "prompt": "plan it", "permission_mode": "plan"})
    assert record["mode"] == "plan"


def test_a_subagent_call_is_recorded_with_its_name_and_type(hook, tmp_path):
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "pr-reviewer.md").write_text("agent", encoding="utf-8")
    record = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "Agent",
                                "tool_input": {"subagent_type": "pr-reviewer", "description": "review the diff"}})
    assert record["subagents_used"] == [
        {"name": "pr-reviewer", "type": "custom", "task": "review the diff", "status": "completed"}]


def test_a_skill_and_an_mcp_tool_are_recorded_in_their_own_fields(hook):
    skill = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "run-checks"}})
    mcp = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "mcp__playwright__browser_click", "tool_input": {}})
    assert skill["skills_used"][0]["name"] == "run-checks"
    assert (mcp["mcp_tools_used"][0]["server"], mcp["mcp_tools_used"][0]["tool"]) == ("playwright", "browser_click")


def test_an_edit_lists_the_file_it_changed_relative_to_the_project(hook, tmp_path):
    record = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "Edit",
                                "tool_input": {"file_path": str(tmp_path / "backend" / "src" / "x.py")}})
    assert record["artifacts"] == ["backend/src/x.py"]
    assert record["stage"] == "implementation"


def test_a_failed_tool_is_logged_as_failed_with_a_limitation(hook):
    record = hook.build_record({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                "tool_input": {"command": "pytest"}, "tool_response": {"is_error": True}})
    assert (record["status"], record["limitation"]) == ("failed", "the tool reported an error")


def test_secrets_and_local_paths_never_reach_the_log(hook, tmp_path):
    record = hook.build_record({"hook_event_name": "UserPromptSubmit",
                                "prompt": f"use token=abc123 and open {tmp_path}/file.py"})
    assert "abc123" not in record["request"]
    assert str(tmp_path) not in record["request"]


def test_append_writes_one_json_line_per_record(hook, tmp_path):
    hook.append(hook.new_record(event="Test", summary="one"))
    hook.append(hook.new_record(event="Test", summary="two"))
    lines = (tmp_path / "logs" / "ai-interactions.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["summary"] for line in lines] == ["one", "two"]


def test_human_decision_text_is_stored_in_its_own_field(hook, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["log_event.py", "--human", "Rejected the first design"])
    hook.main()
    record = json.loads((tmp_path / "logs" / "ai-interactions.jsonl").read_text(encoding="utf-8"))
    assert record["human_decision"] == "Rejected the first design"
    assert record["agent_type"] == "human"
