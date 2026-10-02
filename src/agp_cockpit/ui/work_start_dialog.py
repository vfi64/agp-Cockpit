"""Input dialog of "Arbeit beginnen" (plan P7): kind and name of the branch."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from agp_cockpit.core.standard_tasks import WORK_KINDS


class WorkStartDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, *, check=None) -> None:
        super().__init__(master)
        self.title("Arbeit beginnen")
        self.resizable(False, False)
        self.result: dict | None = None
        self.check = check
        frame = ttk.Frame(self, padding=14)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Neuer Arbeitsbranch", font=("TkDefaultFont", 14, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(frame, text="Art").grid(row=1, column=0, sticky="w")
        self.kind_var = tk.StringVar(value=WORK_KINDS[0])
        ttk.Combobox(frame, textvariable=self.kind_var, values=WORK_KINDS, state="readonly",
                     width=12).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(frame, text="Name").grid(row=2, column=0, sticky="w")
        self.name_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.name_var, width=36)
        entry.grid(row=2, column=1, sticky="w", pady=2)
        self.preview_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.preview_var, foreground="#888888").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.error_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.error_var, foreground="#d9534f", wraplength=360,
                  justify="left").grid(row=4, column=0, columnspan=2, sticky="w")
        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Abbrechen", command=self.destroy).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Beginnen", command=self.accept).grid(row=0, column=1)
        for var in (self.kind_var, self.name_var):
            var.trace_add("write", lambda *_: self._preview())
        self._preview()
        entry.focus_set()
        self.bind("<Return>", lambda _e: self.accept())
        self.bind("<Escape>", lambda _e: self.destroy())

    def values(self) -> dict:
        return {"kind": self.kind_var.get().strip(), "name": self.name_var.get().strip().lower()}

    def _preview(self) -> None:
        values = self.values()
        self.preview_var.set(f"Branch: {values['kind']}/{values['name'] or '…'}")

    def accept(self) -> None:
        values = self.values()
        reason = self.check(values) if self.check else None
        if reason:
            self.error_var.set(reason)
            return
        self.result = values
        self.destroy()


def ask_work_inputs(master: tk.Misc, check=None) -> dict | None:
    dialog = WorkStartDialog(master, check=check)
    dialog.transient(master.winfo_toplevel())
    dialog.grab_set()
    master.wait_window(dialog)
    return dialog.result
