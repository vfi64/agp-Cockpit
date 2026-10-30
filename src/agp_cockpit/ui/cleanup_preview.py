"""Preview window of „Aufräumen“ (AGP_CLEANUP_PREVIEW_WINDOW_V1).

Live 2026-10-30: the preview was a native yes/no box; with 150 entries it grew taller than the
screen and could not be read to the end. The window is resizable, the list keeps a bounded
height with a scroll bar, and the decision stays explicit („Löschen“ / „Abbrechen“).
The window only shows the core's plan; it decides nothing.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from agp_cockpit.core import maintenance

LIST_LINES = 18          # visible lines before the scroll bar takes over


class CleanupPreview(tk.Toplevel):
    def __init__(self, master: tk.Misc, plan: maintenance.Plan) -> None:
        super().__init__(master)
        self.title("Aufräumen — Vorschau")
        self.resizable(True, True)
        self.minsize(520, 320)
        self.approved = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text=maintenance.summary(plan), font=("TkDefaultFont", 14, "bold"),
                  padding=(12, 10, 12, 4)).grid(row=0, column=0, sticky="w")
        frame = ttk.Frame(self, padding=(12, 0, 12, 0))
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.text = tk.Text(frame, wrap="word", height=LIST_LINES, width=90, relief="flat")
        self.scroll = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.text.insert("1.0", maintenance.describe(plan))
        self.text.configure(state="disabled")
        buttons = ttk.Frame(self, padding=(12, 8, 12, 12))
        buttons.grid(row=2, column=0, sticky="e")
        ttk.Label(buttons, text="Gelöscht wird nur, was eine neue Prüfung beim Löschen noch findet.",
                  foreground="#888888").grid(row=0, column=0, padx=(0, 16))
        self.cancel_button = ttk.Button(buttons, text="Abbrechen", command=self._cancel)
        self.cancel_button.grid(row=0, column=1, padx=(0, 8))
        self.delete_button = ttk.Button(buttons, text="Löschen", command=self._approve)
        self.delete_button.grid(row=0, column=2)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())

    def _approve(self) -> None:
        self.approved = True
        self.destroy()

    def _cancel(self) -> None:
        self.approved = False
        self.destroy()


def ask(master: tk.Misc, plan: maintenance.Plan) -> bool:
    """Show the preview modally; True only after „Löschen“."""
    window = CleanupPreview(master, plan)
    window.transient(master)
    window.grab_set()
    master.wait_window(window)
    return window.approved
