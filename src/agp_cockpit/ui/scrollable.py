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


class ScrollableTab(ttk.Frame):
    def __init__(self, master: tk.Misc, *, min_width: int = 900) -> None:
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
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _layout(self) -> None:
        width = max(self.canvas.winfo_width(), self.min_width, 1)
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


def initial_geometry(screen_width: int, screen_height: int) -> str:
    """Large enough for every tab without scrolling on a common laptop screen."""
    width = max(1020, min(1500, int(screen_width * 0.9)))
    height = max(600, min(1100, int(screen_height * 0.9)))
    return f"{width}x{height}"
