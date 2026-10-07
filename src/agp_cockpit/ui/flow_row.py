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
        self.bind("<Configure>", self._on_configure, add="+")

    def add(self, widget: tk.Widget) -> tk.Widget:
        self.items.append(widget)
        self.relayout()
        return widget

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
            width = 10_000            # not yet mapped: one row until the real width is known
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
                widget.pack(in_=self._rows[index], side="left", padx=(self.gap if position else 0, 0))
                widget.lift(self._rows[index])

    def rows(self) -> int:
        return sum(1 for frame in self._rows if frame.winfo_manager())
