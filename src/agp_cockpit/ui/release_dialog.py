"""Input dialog of "Release" (plan P11): the version of the release (tag plus the Kit-made GitHub Release entry)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ReleaseDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, *, current: str = "", suggestion: str = "", check=None) -> None:
        super().__init__(master)
        self.title("Release")
        self.resizable(False, False)
        self.result: dict | None = None
        self.check = check
        self.current = current
        frame = ttk.Frame(self, padding=14)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Privates Release", font=("TkDefaultFont", 14, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(frame, text=f"Aktuelle Version: {current or 'unbekannt'}", foreground="#888888").grid(
            row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text="Neue Version").grid(row=2, column=0, sticky="w")
        self.version_var = tk.StringVar(value=suggestion)
        entry = ttk.Entry(frame, textvariable=self.version_var, width=16)
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
        ttk.Button(buttons, text="Weiter", command=self.accept).grid(row=0, column=1)
        self.version_var.trace_add("write", lambda *_: self._preview())
        self._preview()
        entry.focus_set()
        entry.select_range(0, "end")
        self.bind("<Return>", lambda _e: self.accept())
        self.bind("<Escape>", lambda _e: self.destroy())

    def values(self) -> dict:
        return {"version": self.version_var.get().strip()}

    def _preview(self) -> None:
        self.preview_var.set(release_preview(self.values()["version"], self.current))

    def accept(self) -> None:
        values = self.values()
        reason = self.check(values) if self.check else None
        if reason:
            self.error_var.set(reason)
            return
        self.result = values
        self.destroy()


def release_preview(version: str, current: str) -> str:
    """AGP_RELEASE_RESUME_PHASE2_V1: the version main already names only gets its tag."""
    version = str(version or "").strip()
    if version and version == str(current or "").strip():
        return f"Release-Branch schon gemergt · nur noch Tag: v{version}"
    shown = version or "…"
    return f"Branch: release/{shown} · Tag: v{shown}"


def next_patch(version: str) -> str:
    parts = str(version or "").split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    return ""


def ask_release_inputs(master: tk.Misc, *, current: str = "", resume: str = "",
                       check=None) -> dict | None:
    """``resume``: the version whose tag is missing although main names it (phase 1 done)."""
    dialog = ReleaseDialog(master, current=current, suggestion=resume or next_patch(current), check=check)
    dialog.transient(master.winfo_toplevel())
    dialog.grab_set()
    master.wait_window(dialog)
    return dialog.result
