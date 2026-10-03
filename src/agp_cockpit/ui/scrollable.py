"""Scrollable tab container (AGP_SCROLLABLE_TABS_V1).

Live 2026-10-02: the window opened too small and parts of a tab were cut off.
Each tab now lives in a canvas: the content fills the visible area when there
is room (rows with weight still stretch) and scroll bars appear only when the
content needs more space than the window offers.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

SCROLL_EXEMPT = ("Text", "Treeview", "Listbox", "TCombobox")
REQUEST_POLL_MS = 300


class ScrollableTab(ttk.Frame):
    def __init__(self, master: tk.Misc, *, min_width: int = 0) -> None:
        super().__init__(master)
        self.min_width = min_width
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        background = ttk.Style(self).lookup("TFrame", "background")
        if background:
            self.canvas.configure(background=background)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self._yset, xscrollcommand=self._xset)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.inner = ttk.Frame(self.canvas)
        self.inner.columnconfigure(0, weight=1)
        self.inner.rowconfigure(0, weight=1)
        self._window = self.canvas.create_window(0, 0, anchor="nw", window=self.inner)
        self.inner.bind("<Configure>", lambda _e: self._layout())
        self.canvas.bind("<Configure>", lambda _e: self._layout())
        # The window item has an explicit size, so a child that grows later (a
        # decision box, a longer status) changes only the inner frame's
        # requested size and fires no <Configure>; a cheap poll catches it.
        self._requested = (0, 0)
        self.after(REQUEST_POLL_MS, self._watch_request)
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _watch_request(self) -> None:
        requested = (self.inner.winfo_reqwidth(), self.inner.winfo_reqheight())
        if requested != self._requested:
            self._requested = requested
            self._layout()
        self.after(REQUEST_POLL_MS, self._watch_request)

    def _layout(self) -> None:
        # AGP_SCROLL_WIDTH_FROM_CONTENT_V1 (P8 live test 2): the content's own
        # width decides, not a fixed 900 px — with the vertical bar shown the
        # canvas got narrower than 900 px and a needless horizontal bar appeared.
        width = max(self.canvas.winfo_width(), self.min_width, self.inner.winfo_reqwidth(), 1)
        height = max(self.canvas.winfo_height(), self.inner.winfo_reqheight(), 1)
        self.canvas.itemconfigure(self._window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    @staticmethod
    def _toggle(bar: ttk.Scrollbar, low: str, high: str, **grid) -> None:
        if float(low) <= 0.0 and float(high) >= 1.0:
            bar.grid_remove()
        else:
            bar.grid(**grid)
        bar.set(low, high)

    def _yset(self, low: str, high: str) -> None:
        self._toggle(self.vbar, low, high, row=0, column=1, sticky="ns")

    def _xset(self, low: str, high: str) -> None:
        self._toggle(self.hbar, low, high, row=1, column=0, sticky="ew")

    def overflowing(self) -> bool:
        low, high = self.canvas.yview()
        return low > 0.0 or high < 1.0

    def _on_wheel(self, event) -> None:
        if not self.overflowing() or event.widget.winfo_class() in SCROLL_EXEMPT:
            return
        step = -event.delta if sys.platform == "darwin" else -int(event.delta / 120)
        self.canvas.yview_scroll(int(step), "units")


# AGP_INITIAL_WINDOW_SIZE_V2 (owner 2026-10-02): the size the owner chose by hand
# (986x754 pt outer window on macOS, minus the 28 pt title bar); smaller screens
# shrink it. Longer tabs scroll (ScrollableFrame).
INITIAL_WIDTH, INITIAL_HEIGHT = 986, 726


def initial_geometry(screen_width: int, screen_height: int) -> str:
    """The owner's chosen size, clamped to the screen."""
    width = min(INITIAL_WIDTH, int(screen_width * 0.95))
    height = min(INITIAL_HEIGHT, int(screen_height * 0.9))
    return f"{width}x{height}"
