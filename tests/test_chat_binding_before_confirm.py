"""AGP_CHAT_BINDING_BEFORE_CONFIRM_V1 (live 2026-10-31, „Kit übernehmen“): the owner confirmed
„Kit 1.1.9 → 1.1.10 übernehmen?“ and only then read that the front ChatGPT chat belonged to the Kit
repository (P4). Every verb now checks the chat binding before an input dialog, a question or the Kit's
release request; the start still checks it again. An undeterminable chat is left to the start."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.conversation_binding import ConversationBindingStore
from agp_cockpit.core.verbs import BY_KEY as VERBS

CHAT = "https://chatgpt.com/c/0123456789abcdef"


@pytest.fixture
def panel(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    repo = tmp_path / "cockpit"
    repo.mkdir()
    asked = []
    widget = m.StandardTasksPanel(root, repository_root=repo, runtime_root=tmp_path / "rt",
                                  confirm=lambda task: asked.append(("confirm", task.key)) or False,
                                  ask_inputs=lambda task: asked.append(("inputs", task.key)) or None)
    monkeypatch.setattr(widget, "refresh_lage", lambda: None)
    monkeypatch.setattr(widget, "run_kit_adopt", lambda task: asked.append(("kit-release", task.key)))
    monkeypatch.setattr(widget, "start_standard_task", lambda task, inputs=None: asked.append(("start", task.key)))
    widget.apply_state(rs.RepoState(rs.BEREIT, "s", rs.ARBEIT_BEGINNEN, rs.OFFERED[rs.BEREIT]))
    yield m, widget, asked, repo, tmp_path
    root.destroy()
    del widget, root
    import gc
    gc.collect()


def _front_chat(m, monkeypatch, url=CHAT):
    monkeypatch.setattr(m, "require_allowed_active_chat", lambda: SimpleNamespace(url=url))


def test_a_chat_of_another_repository_blocks_before_any_question(panel, monkeypatch):
    m, widget, asked, _repo, tmp_path = panel
    _front_chat(m, monkeypatch)
    ConversationBindingStore(tmp_path / "rt").bind(CHAT, tmp_path / "kit")
    for key in (rs.KIT_UEBERNEHMEN, rs.ARBEIT_BEGINNEN, rs.PFLEGE):
        widget.run_verb(VERBS[key])
        assert asked == [], key
        text = widget.status_var.get()
        assert text.startswith("BLOCKED — Dieser ChatGPT-Chat gehört zum Repository") and "Neuer Chat" in text
        assert f"„{VERBS[key].label}“ erneut klicken" in text


def test_the_chat_of_this_repository_or_a_new_chat_goes_on_to_the_question(panel, monkeypatch):
    m, widget, asked, repo, tmp_path = panel
    _front_chat(m, monkeypatch)
    widget.run_verb(VERBS[rs.KIT_UEBERNEHMEN])                       # an unbound chat
    ConversationBindingStore(tmp_path / "rt").bind(CHAT, repo)
    widget.run_verb(VERBS[rs.ARBEIT_BEGINNEN])                       # the chat of this repository
    assert asked == [("kit-release", "kit-adopt"), ("inputs", "work-start")]


def test_an_undeterminable_chat_is_left_to_the_start(panel, monkeypatch):
    m, widget, asked, _repo, _tmp = panel

    def no_chat():
        raise PermissionError("kein ChatGPT-Tab")
    monkeypatch.setattr(m, "require_allowed_active_chat", no_chat)
    widget.run_verb(VERBS[rs.KIT_UEBERNEHMEN])
    assert asked == [("kit-release", "kit-adopt")] and not widget.status_var.get().startswith("BLOCKED")


def test_the_start_still_checks_the_binding_itself():
    source = (Path(__file__).resolve().parents[1] / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(
        encoding="utf-8")
    start = source[source.index("def start_standard_task("):source.index("contract = task.contract(")]
    assert "block_reason(conversation_url" in start and "chat_binding_hint(" in start
    run_verb = source[source.index("def run_verb("):source.index("def chat_binding_block(")]
    assert run_verb.index("self.chat_binding_block(") < run_verb.index('task.key == "kit-adopt"')
    assert run_verb.index('task.key == "kit-adopt"') < run_verb.index("self.ask_inputs(task)")
