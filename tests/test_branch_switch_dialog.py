"""AGP_BRANCH_DIALOG_EXPLICIT_V1 (live 2026-10-07): no preselected target, so a second open of
„Branch wechseln …“ can no longer switch straight back to main."""
import tkinter as tk

import pytest

from agp_cockpit.core.branch_switch import LocalBranch
from agp_cockpit.ui.branch_switch_dialog import build_dialog

BRANCHES = [LocalBranch("ci/runner-hardening", "2026-10-07", "ci: harden", True),
            LocalBranch("main", "2026-10-07", "Refresh successor package", False)]


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    window.withdraw()
    yield window
    window.destroy()


def test_nothing_is_preselected_and_switch_waits_for_a_click(root):
    window, listbox, switch, result, on_select = build_dialog(root, BRANCHES)
    assert listbox.curselection() == ()
    assert str(switch.cget("state")) == "disabled"
    assert "zurück auf main" in listbox.get(0)
    window.event_generate("<Return>")          # Return without a choice does nothing
    root.update()
    assert result["name"] is None and window.winfo_exists()
    assert listbox.bind("<<ListboxSelect>>")      # a click on a row runs on_select
    listbox.selection_set(0)
    on_select()
    assert str(switch.cget("state")) == "normal"
    switch.invoke()
    assert result["name"] == "main"


def test_an_origin_only_branch_is_labelled(root):
    """AGP_BRANCH_SWITCH_ORIGIN_V1"""
    branches = [*BRANCHES, LocalBranch("codex/pushed", "2026-10-22", "pushed", False, remote_only=True)]
    _window, listbox, _switch, result, on_select = build_dialog(root, branches)
    assert "nur auf origin" in listbox.get(1) and "nur auf origin" not in listbox.get(0)
    listbox.selection_set(1)
    on_select()
    _switch.invoke()
    assert result["name"] == "codex/pushed"
