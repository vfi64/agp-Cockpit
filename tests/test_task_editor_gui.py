"""AGP_TASK_EDITOR_V1: the "Arbeiten" tab is an editable task editor (type,
paste, load, change, start) driven through the real Tk widgets."""
import json
from pathlib import Path
from typing import ClassVar

import pytest

from agp_cockpit.core.task_contract_text import (
    contract_from_text,
    editor_text_from_file,
)


def test_plain_text_becomes_the_goal_and_json_the_contract():
    assert contract_from_text("  Tue X\n") == {"goal": "Tue X"}
    assert contract_from_text('{"goal": "G", "title": "T"}') == {"goal": "G", "title": "T"}
    with pytest.raises(ValueError, match="leer"):
        contract_from_text("   ")
    with pytest.raises(ValueError, match="JSON-Auftrag ist ungültig"):
        contract_from_text("{ kaputt")
    assert contract_from_text("[1] Liste als Text") == {"goal": "[1] Liste als Text"}


def test_json_file_is_shown_formatted(tmp_path):
    (tmp_path / "a.json").write_text('{"goal":"G"}')
    assert editor_text_from_file(tmp_path / "a.json") == '{\n  "goal": "G"\n}\n'
    (tmp_path / "a.txt").write_text("Text")
    assert editor_text_from_file(tmp_path / "a.txt") == "Text"


def test_editor_widget_flow(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    import agp_cockpit.ui.simple_task_panel as m

    class FakeAPI:
        def __init__(self, *args, **kwargs):
            pass

        def prepare_task_contract(self, contract):
            return dict(contract, task_id="t1")

        def start_task_from_contract(self, contract):
            return {"state": "WAITING_FOR_REMOTE"}

        def status(self):
            return {"state": "WAITING_FOR_REMOTE"}

        class operator_control:
            requests: ClassVar[list] = []

            @classmethod
            def request(cls, action):
                cls.requests.append(action)

    sent = {}
    monkeypatch.setattr(m, "TaskOperatorAPI", FakeAPI)
    # AGP_REPO_STATE_V1: the test repository has no installed Kit
    monkeypatch.setattr("agp_cockpit.core.build_freshness.kit_block_reason", lambda root: "")
    monkeypatch.setattr(m.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(m, "require_allowed_active_chat", lambda: type("C", (), {"url": "https://chatgpt.com/c/x"})())
    monkeypatch.setattr(m, "create_live_full_auto", lambda **k: sent.update(k) or {"mission": {"mission_id": "M1"}})
    monkeypatch.setattr(m, "request_task_start", lambda mission_id, task_id: sent.update(start=(mission_id, task_id)))
    monkeypatch.setattr(m, "mission_status", lambda: {"mission": {
        "mission_id": "M1", "state": "NEEDS_HUMAN", "turn_count": 2, "step_count": 1,
        "last_summary": "Push freigeben?"}})
    decisions = []
    monkeypatch.setattr(m, "record_decision", lambda **k: decisions.append(k) or {"decision": k["decision"]})
    try:
        panel = m.SimpleTaskPanel(root, repository_root=Path("."))
        panel.pack()
        root.update()
        assert str(panel.start_button["state"]) == "disabled"
        # paste into the empty editor, then change it before the start
        panel.editor.insert("1.0", "Bereite einen Push vor.\nFühre ihn nicht aus.")
        root.update()
        assert str(panel.start_button["state"]) == "normal"
        panel.editor.insert("end", "\nZusatz.")
        panel.start_task()
        assert sent["mission_text"].count("Zusatz.") == 1
        assert sent["start"] == ("M1", "t1")
        assert str(panel.editor["state"]) == "disabled" and panel.workflow_phase == "STARTED"
        # a terminal mission hands the editor back
        panel.refresh_status()
        assert panel.state_var.get().startswith("Mensch muss eingreifen")
        assert str(panel.editor["state"]) == "normal" and str(panel.start_button["state"]) == "normal"
        # AGP_HUMAN_DECISION_V1: the question is shown and answered in the app
        root.update()
        assert panel.decision_frame.winfo_ismapped()
        assert panel.decision_question_var.get() == "Push freigeben?"
        panel.decision_note.insert("1.0", "ja, nach origin")
        panel.decide("APPROVE")
        assert decisions == [{"mission_id": "M1", "decision": "APPROVE", "note": "ja, nach origin"}]
        assert FakeAPI.operator_control.requests == ["RESUME"]
        assert "APPROVED" in sent["mission_text"] and "ja, nach origin" in sent["mission_text"]
        assert sent["title"].endswith("· Entscheidung") and sent["start"] == ("M1", "t1")
        root.update()
        assert not panel.decision_frame.winfo_ismapped() and panel.workflow_phase == "STARTED"
        panel.workflow_phase = "LOADED"
        panel.editor.configure(state="normal")
        # loading a JSON file fills the editor; invalid JSON is reported, not started
        (tmp_path / "a.json").write_text(json.dumps({"goal": "G", "title": "T"}))
        monkeypatch.setattr(m.filedialog, "askopenfilename", lambda **k: str(tmp_path / "a.json"))
        panel.load_contract()
        assert '"title": "T"' in panel._editor_text()
        panel._set_editor("{ kaputt")
        panel.start_task()
        assert "JSON-Auftrag ist ungültig" in panel.state_var.get()
        panel.new_task()
        assert panel._editor_text() == "" and str(panel.start_button["state"]) == "disabled"
    finally:
        root.destroy()
