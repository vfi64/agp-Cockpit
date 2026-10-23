"""„Branch wechseln …“ (AGP_BRANCH_SWITCH_V1): pick a local branch, newest first.

AGP_BRANCH_DIALOG_EXPLICIT_V1 (live 2026-10-07, 22:07): right after a switch the only other branch
was main, preselected; opening the dialog again and pressing „Wechseln“ (or Return) switched
straight back to main twice. Nothing is preselected now: „Wechseln“ and Return act only after
the owner has clicked a branch, and main is labelled as the way back.

AGP_BRANCH_SWITCH_ORIGIN_V1: origin-only branches follow the local ones, labelled „nur auf origin“.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def _label(entry) -> str:
    back = "   ·   zurück auf main" if entry.name in ("main", "master") else ""
    if getattr(entry, "remote_only", False):
        back += "   ·   nur auf origin (wird über das Kit geholt)"
    return f"{entry.name}   ·   {entry.date}   ·   {entry.subject}{back}"


def build_dialog(parent: tk.Misc, branches):
    """The dialog without waiting: (window, listbox, switch button, result dict, selection handler)."""
    choices = [entry for entry in branches if not entry.current]
    current = next((entry.name for entry in branches if entry.current), "")
    window = tk.Toplevel(parent)
    window.title("Branch wechseln")
    window.transient(parent.winfo_toplevel())
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)
    ttk.Label(window, text=f"Aktiv: {current or '—'} · Ziel anklicken (lokale Branches, dann nur auf origin; neuester zuerst)",
              padding=(10, 8)).grid(row=0, column=0, columnspan=2, sticky="w")
    listbox = tk.Listbox(window, height=12, width=70, exportselection=False)
    listbox.grid(row=1, column=0, sticky="nsew", padx=(10, 0))
    bar = ttk.Scrollbar(window, orient="vertical", command=listbox.yview)
    bar.grid(row=1, column=1, sticky="ns", padx=(0, 10))
    listbox.configure(yscrollcommand=bar.set)
    for entry in choices:
        listbox.insert("end", _label(entry))
    result: dict = {"name": None}

    def accept(_event=None) -> None:
        selected = listbox.curselection()
        if not selected:
            return                      # never a default target
        result["name"] = choices[selected[0]].name
        window.destroy()

    buttons = ttk.Frame(window, padding=10)
    buttons.grid(row=2, column=0, columnspan=2, sticky="e")
    ttk.Button(buttons, text="Abbrechen", command=window.destroy).grid(row=0, column=0, padx=(0, 8))
    switch = ttk.Button(buttons, text="Wechseln", command=accept, state="disabled")
    switch.grid(row=0, column=1)

    def on_select(_event=None) -> None:
        switch.configure(state="normal" if listbox.curselection() else "disabled")

    listbox.bind("<<ListboxSelect>>", on_select)
    listbox.bind("<Double-Button-1>", accept)
    window.bind("<Return>", accept)
    window.bind("<Escape>", lambda _e: window.destroy())
    return window, listbox, switch, result, on_select


def ask_branch(parent: tk.Misc, branches) -> str | None:
    """Modal choice of one non-current branch (local or origin-only); None when cancelled or nothing chosen."""
    window, listbox, _switch, result, _on_select = build_dialog(parent, branches)
    window.grab_set()
    listbox.focus_set()
    window.wait_window()
    return result["name"]
