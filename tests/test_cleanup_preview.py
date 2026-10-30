"""AGP_CLEANUP_PREVIEW_WINDOW_V1 (live 2026-10-30): the cleanup preview was a native yes/no box that grew
taller than the screen with 150 entries, and with nothing to delete it still asked „Jetzt endgültig
löschen?“ and reported 0 deletions."""
from __future__ import annotations

from pathlib import Path

import pytest

from agp_cockpit.core import maintenance as mt

ROOT = Path(__file__).resolve().parents[1]


def _plan(n: int, kit_preview: str = "PASS_NOTHING_TO_COLLECT", kit: bool = True) -> mt.Plan:
    candidates = tuple(mt.Candidate(Path(f"/x/tmp/{i}"), 1000, f"Temporär (repo{i})") for i in range(n))
    return mt.Plan(candidates, ("k", "artifact-gc", "--tmp-logs") if kit else None, kit_preview)


def test_nothing_to_do_needs_no_cockpit_entries_and_an_idle_kit():
    assert mt.nothing_to_do(_plan(0))
    assert mt.nothing_to_do(_plan(0, kit=False))
    assert not mt.nothing_to_do(_plan(1))
    assert not mt.nothing_to_do(_plan(0, kit_preview="WOULD_DELETE 3 logs"))


def test_summary_counts_entries_and_size():
    assert mt.summary(_plan(150)) == "150 Einträge, 0.1 MB"
    assert mt.summary(_plan(0)) == "Keine Cockpit-Dateien zum Löschen."


def test_main_window_uses_the_preview_window_and_skips_an_empty_question():
    source = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "maintenance.nothing_to_do(plan)" in source and "cleanup_preview.ask(self, plan)" in source
    assert "Jetzt endgültig löschen?" not in source


def test_the_preview_window_is_resizable_bounded_and_scrolls():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        from agp_cockpit.ui.cleanup_preview import LIST_LINES, CleanupPreview
        window = CleanupPreview(root, _plan(150))
        window.update()
        assert window.resizable() == (True, True)
        assert int(window.text.cget("height")) == LIST_LINES
        assert window.text.yview()[1] < 1.0               # more lines than fit: the scroll bar is needed
        assert "Temporär (repo149)" in window.text.get("1.0", "end")
        window.delete_button.invoke()
        assert window.approved is True
        window = CleanupPreview(root, _plan(3))
        window.cancel_button.invoke()
        assert window.approved is False
    finally:
        root.destroy()
