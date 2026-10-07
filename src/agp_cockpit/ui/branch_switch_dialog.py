"""„Branch wechseln …“ (AGP_BRANCH_SWITCH_V1): pick a local branch, newest first."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def ask_branch(parent: tk.Misc, branches) -> str | None:
    """Modal choice of one non-current local branch; None when cancelled."""
    choices = [entry for entry in branches if not entry.current]
    current = next((entry.name for entry in branches if entry.current), "")
    window = tk.Toplevel(parent)
    window.title("Branch wechseln")
    window.transient(parent.winfo_toplevel())
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)
    ttk.Label(window, text=f"Aktiv: {current or '—'} · lokaler Branch, neuester zuerst",
              padding=(10, 8)).grid(row=0, column=0, columnspan=2, sticky="w")
    listbox = tk.Listbox(window, height=12, width=70, exportselection=False)
    listbox.grid(row=1, column=0, sticky="nsew", padx=(10, 0))
    bar = ttk.Scrollbar(window, orient="vertical", command=listbox.yview)
    bar.grid(row=1, column=1, sticky="ns", padx=(0, 10))
    listbox.configure(yscrollcommand=bar.set)
    for entry in choices:
        listbox.insert("end", f"{entry.name}   ·   {entry.date}   ·   {entry.subject}")
    if choices:
        listbox.selection_set(0)
    result: dict = {"name": None}

    def accept(_event=None) -> None:
        selected = listbox.curselection()
        if selected:
            result["name"] = choices[selected[0]].name
        window.destroy()

    buttons = ttk.Frame(window, padding=10)
    buttons.grid(row=2, column=0, columnspan=2, sticky="e")
    ttk.Button(buttons, text="Abbrechen", command=window.destroy).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(buttons, text="Wechseln", command=accept,
               state="normal" if choices else "disabled").grid(row=0, column=1)
    listbox.bind("<Double-Button-1>", accept)
    window.bind("<Return>", accept)
    window.bind("<Escape>", lambda _e: window.destroy())
    window.grab_set()
    listbox.focus_set()
    window.wait_window()
    return result["name"]
