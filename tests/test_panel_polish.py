"""P8 live test 2 polish: summaries are cut at a word boundary
(AGP_SUMMARY_CLIP_V1) and the scroll width follows the content
(AGP_SCROLL_WIDTH_FROM_CONTENT_V1)."""
from __future__ import annotations

import pytest

from agp_cockpit.core.standard_task_progress import SUMMARY_LIMIT, clip

LIVE_1628 = ("Step 1628 executed the explicitly approved signed Kit rescue successfully. `agentic-kit work "
             "rescue --execute` returned result_status PASS with failed_step null and completed the non-lossy "
             "rescue. The saved work is on rescue branch rescue/main-cdc9a828-b76a2efa2b.")


def test_clip_never_cuts_a_word_and_marks_the_cut():
    short = "Lokal geprüft (Lagebericht BEREIT)."
    assert clip(short) == short
    clipped = clip(LIVE_1628)
    assert clipped.endswith(" …") and len(clipped) <= SUMMARY_LIMIT + 2
    assert "with fail …" not in clipped and "with fail" not in clipped.replace("failed_step", "")
    assert clip("x" * 300).endswith(" …")             # one long token: hard cut, still marked
    assert clip("a  b\n c") == "a b c"


def test_scroll_width_follows_the_content():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        from tkinter import ttk

        from agp_cockpit.ui.scrollable import ScrollableTab
        root.geometry("500x200")
        tab = ScrollableTab(root)
        tab.pack(fill="both", expand=True)
        ttk.Frame(tab.inner, height=900, width=300).grid(row=0, column=0)
        root.update()
        assert tab.vbar.winfo_ismapped() and not tab.hbar.winfo_ismapped()
        ttk.Frame(tab.inner, height=10, width=900).grid(row=1, column=0)
        root.update()
        root.after(400, root.quit)
        root.mainloop()               # let the request poll run once
        root.update()
        assert tab.hbar.winfo_ismapped()
    finally:
        root.destroy()
