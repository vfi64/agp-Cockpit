from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class TerminalPanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, text="Lokale Ausführung", padding=10)
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text=(
                "Der Terminal-Executor ist vorbereitet. "
                "Browser-/Kit-Aufträge werden im nächsten Slice hier sichtbar "
                "vor der Ausführung angezeigt."
            ),
            justify="left",
            wraplength=690,
        ).grid(row=0, column=0, sticky="w")
