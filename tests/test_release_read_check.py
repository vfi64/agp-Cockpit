"""AGP_RELEASE_READ_CHECK_V1 (workflow-friction plan C4, V11 live 2026-11-13): the Release task runs the Kit's
read check (``release ready``, step A2 of the release run) before it asks the owner. Only PASS leads to the
question; any other answer shows the Kit's own words: stopped steps, check id and the resolving command with
its consent flag (G3), or the Kit's reason. The Cockpit judges nothing itself. A resumed release skips it."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import release_read_check as rc
from agp_cockpit.core import standard_tasks as st

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path("/venv/bin/agentic-kit")
TASK = st.BY_KEY["release"]
BLOCKED = {"result_status": "BLOCKED", "returncode": 2, "blockers": ["standard-error-scan"],
           "check_id": "KIT-CHK-CURATED-UNRELEASED-LINE", "next_command": "agentic-kit docs lifecycle sweep",
           "next_command_kind": "kit", "next_command_autonomous": False, "next_command_reason": "",
           "steps": [{"name": "standard-error-scan", "ok": False, "stdout": "SECRET-STEP-DETAIL"}]}


def _kit(monkeypatch, found=True):
    from agp_cockpit.core import kit_installation
    monkeypatch.setattr(kit_installation, "discover",
                        lambda _root: SimpleNamespace(version="1.4.0", binary=BINARY) if found else None)


def _runner(payload, calls=None, rc_=2, stderr=""):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append((argv, kwargs))
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.CompletedProcess(argv, rc_, text, stderr)
    return run


def test_the_check_is_step_a2_of_the_release_run_in_the_repository(monkeypatch, tmp_path):
    _kit(monkeypatch)
    calls = []
    check = rc.read(tmp_path, "0.4.2", runner=_runner({"result_status": "PASS", "blockers": []}, calls, 0))
    assert check.passed and check.result == rc.PASS
    argv, kwargs = calls[0]
    assert argv == [str(BINARY), "release", "ready", "--version", "0.4.2", "--json"]   # no summary lines
    assert kwargs["cwd"] == str(tmp_path) and kwargs["timeout"] == rc.READ_CHECK_TIMEOUT


def test_a_stop_carries_the_kits_steps_check_and_resolving_command(monkeypatch, tmp_path):
    _kit(monkeypatch)
    check = rc.read(tmp_path, "0.4.2", runner=_runner(BLOCKED))
    assert check.result == rc.STOPPED and not check.passed
    assert check.blockers == ("standard-error-scan",) and check.check_id == "KIT-CHK-CURATED-UNRELEASED-LINE"
    text = rc.stop_text(check, "0.4.2")
    assert "release ready: BLOCKED" in text and "standard-error-scan" in text
    assert "KIT-CHK-CURATED-UNRELEASED-LINE" in text
    assert "agentic-kit docs lifecycle sweep" in text and "braucht deine Zustimmung" in text
    assert "SECRET-STEP-DETAIL" not in text                    # the steps stay the Kit's; nothing is judged
    autonomous = rc.read(tmp_path, "0.4.2", runner=_runner({**BLOCKED, "next_command_autonomous": True}))
    assert "darf ohne neue Zustimmung laufen" in rc.stop_text(autonomous, "0.4.2")


def test_a_stop_without_a_kit_command_shows_the_kits_reason(monkeypatch, tmp_path):
    _kit(monkeypatch)
    human = {**BLOCKED, "next_command": "", "next_command_kind": "human",
             "next_command_reason": "No automatic Kit route for blocked step release-prep-dry-run"}
    text = rc.stop_text(rc.read(tmp_path, "0.4.2", runner=_runner(human)), "0.4.2")
    assert "Das Kit nennt keinen behebenden Befehl: No automatic Kit route" in text
    assert "Behebender Befehl" not in text


def test_every_answer_but_pass_stops_and_no_answer_fails_closed(monkeypatch, tmp_path):
    _kit(monkeypatch)
    for status in ("FAIL", "WARN", "PLANNED"):
        assert rc.read(tmp_path, "0.4.2", runner=_runner({"result_status": status})).result == rc.STOPPED
    garbled = rc.read(tmp_path, "0.4.2", runner=_runner("Traceback", stderr="Error: No such option\n"))
    assert garbled.result == rc.NO_ANSWER and "No such option" in garbled.reason
    assert "kein Ergebnis" in rc.stop_text(garbled, "0.4.2")

    def slow(argv, **_kwargs):
        raise subprocess.TimeoutExpired(argv, rc.READ_CHECK_TIMEOUT)
    assert rc.read(tmp_path, "0.4.2", runner=slow).result == rc.NO_ANSWER
    _kit(monkeypatch, found=False)
    missing = rc.read(tmp_path, "0.4.2", runner=_runner(BLOCKED))
    assert missing.result == rc.NO_KIT and "nicht gestartet" in rc.stop_text(missing, "0.4.2")


def test_the_cockpit_reads_only_status_blockers_check_and_route():
    source = (ROOT / "src/agp_cockpit/core/release_read_check.py").read_text(encoding="utf-8")
    code = source[source.index("def read("):source.index("def stop_text(")]
    assert '"steps"' not in code and "stdout\n" not in code
    assert 'status == PASS else STOPPED' in code


def test_a_resumed_release_skips_the_check(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.4.2"\n', encoding="utf-8")
    assert rc.needed(tmp_path, "0.4.3") is True
    assert rc.needed(tmp_path, "0.4.2") is False               # main names it: the Kit's run resumes


def test_the_task_description_names_the_check():
    assert "release ready" in TASK.description and "nur nach PASS" in TASK.description


@pytest.fixture
def panel(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    asked = []
    widget = m.StandardTasksPanel(root, repository_root=tmp_path, on_open_work=lambda: None,
                                  confirm=lambda task: asked.append(task.key) or True)
    shown, started = [], []
    monkeypatch.setattr(widget, "_show_info", lambda title, text: shown.append(text))
    monkeypatch.setattr(widget, "start_standard_task", lambda task, inputs: started.append(inputs) or True)
    yield SimpleNamespace(root=root, widget=widget, asked=asked, shown=shown, started=started)
    root.destroy()


def test_only_the_kits_pass_leads_to_the_question(panel):
    widget = panel.widget
    inputs = {"version": "0.4.2"}
    stopped = rc.ReadCheck(rc.STOPPED, status="BLOCKED", blockers=("standard-error-scan",),
                           next_command="agentic-kit docs lifecycle sweep", next_command_kind="kit")
    assert widget.release_check_answer(TASK, inputs, stopped) is False
    assert not panel.asked and not panel.started
    assert "agentic-kit docs lifecycle sweep" in panel.shown[-1]
    assert widget.status_var.get().startswith("Das Kit stoppt Release 0.4.2")
    assert widget.release_check_answer(TASK, inputs, rc.ReadCheck(rc.NO_ANSWER, reason="x")) is False
    assert not panel.asked and not panel.started
    assert widget.release_check_answer(TASK, inputs, rc.ReadCheck(rc.PASS, status="PASS")) is True
    assert panel.asked == ["release"] and panel.started == [inputs]
    assert widget.release_check_answer(TASK, inputs, None) is True          # resumed release: no check
    assert panel.asked == ["release", "release"]


def test_the_verb_runs_the_check_beside_the_ui_thread_before_the_question(panel, monkeypatch):
    widget = panel.widget
    from agp_cockpit.core import repo_state as rs
    from agp_cockpit.core.verbs import BY_KEY as VERBS
    monkeypatch.setattr(widget, "chat_binding_block", lambda _label: "")
    monkeypatch.setattr(widget, "ask_inputs", lambda _task: {"version": "0.4.2"})
    monkeypatch.setattr("agp_cockpit.ui.standard_tasks_panel.availability", lambda *a, **k: (True, ""))
    seen = []
    monkeypatch.setattr(rc, "read", lambda root, version: seen.append(version) or rc.ReadCheck(
        rc.STOPPED, status="BLOCKED", blockers=("release-prep-dry-run",), next_command_kind="human",
        next_command_reason="Unreleased line rejected"))
    widget.run_verb(VERBS[rs.RELEASE])
    assert "prüft die Release-Bereitschaft" in widget.status_var.get() and not panel.shown
    deadline = time.monotonic() + 5
    while not panel.shown and time.monotonic() < deadline:
        panel.root.update()
        time.sleep(0.02)
    assert seen == ["0.4.2"] and "Unreleased line rejected" in panel.shown[-1]
    assert not panel.asked and not panel.started


def test_the_thread_touches_no_tk_object():
    """AGP_TK_GC_ON_MAIN_THREAD_V1: the worker gets only plain values; the panel reads its answer on the UI thread."""
    source = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    method = source[source.index("def run_release_check("):source.index("def release_check_answer(")]
    ask = method[method.index("def ask("):method.index("threading.Thread(")]
    assert "self" not in ask
    assert 'threading.Thread(target=ask, name="agp-release-read-check", daemon=True)' in method
    run_verb = source[source.index("def run_verb("):source.index("def chat_binding_block(")]
    assert run_verb.index("self.ask_inputs(task)") < run_verb.index('task.key == "release"') \
        < run_verb.index("self.confirm(task)")
