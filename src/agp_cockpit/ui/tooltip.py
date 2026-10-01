"""Small tooltip for Tk widgets (Tk has none built in). AGP_STANDARD_TASK_VERBS_V1."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class Tooltip:
    def __init__(self, widget: tk.Misc, text: Callable[[], str] | str, delay_ms: int = 500) -> None:
        self.widget = widget
        self._text = text
        self.delay_ms = delay_ms
        self._job: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def text(self) -> str:
        return self._text() if callable(self._text) else self._text

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._job = self.widget.after(self.delay_ms, self.show)

    def _cancel(self) -> None:
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None

    def show(self) -> None:
        self._job = None
        text = self.text()
        if not text or self._window is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(window, text=text, justify="left", wraplength=420, background="#ffffe0",
                 foreground="#000000", relief="solid", borderwidth=1, padx=8, pady=6).pack()
        self._window = window

    def hide(self, _event=None) -> None:
        self._cancel()
        if self._window is not None:
            self._window.destroy()
            self._window = None
