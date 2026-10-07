"""A row of buttons that wraps with the window width (AGP_FLOW_ROW_V1).

Owner 2026-10-06: the „Arbeiten“ tab's eight buttons sat in one grid row and
were cut off when the window was narrow (Chrome shares the screen).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class FlowRow(ttk.Frame):
    def __init__(self, master: tk.Misc, *, gap: int = 8, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.gap = gap
        self.items: list[tk.Widget] = []
        self._width = 0
        self._rows: list[ttk.Frame] = []
        self._pending = False
        self._layout_key: tuple = ()
        # AGP_VIEWPORT_WRAP_V1: the row never requests the width of all buttons in
        # one line (that kept the tab wide and showed a horizontal scroll bar); its
        # height follows the wrapped rows, its width comes from the parent's grid.
        self.grid_propagate(False)
        self.configure(width=1, height=1)
        self.bind("<Configure>", self._on_configure, add="+")

    def add(self, widget: tk.Widget) -> tk.Widget:
        self.items.append(widget)
        # An item that changes its size (a badge becomes „★ empfohlen …“) re-flows the row.
        widget.bind("<Configure>", lambda _e: self._schedule(), add="+")
        self.relayout()
        return widget

    def _schedule(self) -> None:
        if not self._pending:
            self._pending = True
            self.after_idle(self._run_scheduled)

    def _run_scheduled(self) -> None:
        self._pending = False
        self.relayout()

    def _on_configure(self, event) -> None:
        if event.width != self._width:
            self._width = event.width
            self.relayout()

    def relayout(self, width: int | None = None) -> None:
        """Pack the items left to right into row frames; a new row when the width is used up.

        Row frames (not one grid) keep each row independent: grid columns would take the
        widest cell of every row and push a wrapped row beyond the window again.
        """
        width = width or self._width or self.winfo_width()
        if width <= 1:
            width = 600               # not yet mapped: a narrow guess until the real width is known
        lines: list[list[tk.Widget]] = [[]]
        used = 0
        for widget in self.items:
            need = widget.winfo_reqwidth() + (self.gap if lines[-1] else 0)
            if lines[-1] and used + need > width:
                lines.append([])
                used = 0
                need = widget.winfo_reqwidth()
            lines[-1].append(widget)
            used += need
        key = tuple(tuple(str(w) for w in line) for line in lines)
        height = sum(max(w.winfo_reqheight() for w in line) + 4 for line in lines if line)
        if key == self._layout_key:
            self.configure(height=max(1, height))
            return
        self._layout_key = key
        while len(self._rows) < len(lines):
            frame = ttk.Frame(self)
            self._rows.append(frame)
        for index, frame in enumerate(self._rows):
            if index < len(lines):
                frame.grid(row=index, column=0, sticky="w", pady=(0, 4))
            else:
                frame.grid_remove()
        for index, line in enumerate(lines):
            for position, widget in enumerate(line):
                widget.pack_forget()
                # anchor "n": a button beside a cell of button + badge starts at the same
                # height (owner 2026-10-07: „Wiederherstellen“ and „Weitere anzeigen“).
                widget.pack(in_=self._rows[index], side="left", anchor="n",
                            padx=(self.gap if position else 0, 0))
                widget.lift(self._rows[index])
        self.configure(height=max(1, height))

    def rows(self) -> int:
        return sum(1 for frame in self._rows if frame.winfo_manager())
