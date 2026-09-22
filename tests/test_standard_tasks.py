from pathlib import Path

from agp_cockpit.core.standard_tasks import standard_tasks

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/agp_cockpit/core/standard_tasks.py").read_text(encoding="utf-8")
PANEL = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")


def test_registry_has_chat_switch_as_first_standard_task():
    tasks = standard_tasks()
    assert tasks
    assert tasks[0].key == "chat-switch"
    assert tasks[0].label == "Chat wechseln"


def test_chat_switch_contract_is_repository_bound_and_fail_closed():
    task = standard_tasks()[0]
    contract = task.contract(ROOT)
    assert contract["repository_root"] == str(ROOT.resolve())
    assert "Fail closed" in " ".join(contract["constraints"])
    assert "git and agentic-kit" in " ".join(contract["constraints"])
    assert "validation_report.json is PASS" in " ".join(contract["acceptance_criteria"])


def test_chat_switch_prompt_is_plain_text_and_carries_file_loop_contract():
    prompt = standard_tasks()[0].prompt(ROOT)
    assert prompt.startswith("CHAT SWITCH STANDARD TASK")
    assert "exactly one executable Python command file" not in prompt
    assert "exactly one newly numbered Download/*.py" in prompt
    assert "validation_report.json" in prompt
    assert str(ROOT.resolve()) in prompt
    assert "at most 80 source lines and 16 KiB" in prompt


def test_standard_task_panel_uses_existing_mission_and_start_request_routes():
    assert "TaskOperatorAPI" in PANEL
    assert "create_live_full_auto" in PANEL
    assert "request_task_start" in PANEL
    assert "start_task_from_contract" in PANEL


def test_standard_task_panel_fails_before_remote_start_without_required_tools():
    assert 'required_tools = {"git", "agentic-kit"}' in PANEL
    assert "missing_tools" in PANEL
    assert "BLOCKED — lokale Authority fehlt" in PANEL
