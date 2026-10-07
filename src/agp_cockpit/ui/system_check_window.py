"""AGP_SYSTEM_CHECK_V1: the Systemcheck window of the System tab (read-only checks)."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from agp_cockpit.core import system_check

MARK = {system_check.OK: ("✓", "#2e9e4f"), system_check.WARN: ("⚠", "#c8a020"),
        system_check.FAIL: ("✗", "#d03030")}


class SystemCheckWindow(tk.Toplevel):
    def __init__(self, master, *, repository_root: Path, run=system_check.run_all) -> None:
        super().__init__(master)
        self.title("Systemcheck")
        self.geometry("720x420")
        self.minsize(480, 300)
        self._root_path = Path(repository_root)
        self._run = run
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.summary_var = tk.StringVar(value="Systemcheck läuft …")
        ttk.Label(self, textvariable=self.summary_var, font=("TkDefaultFont", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.body = ttk.Frame(self, padding=(12, 0))
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.columnconfigure(2, weight=1)
        buttons = ttk.Frame(self, padding=12)
        buttons.grid(row=2, column=0, sticky="ew")
        self.again_button = ttk.Button(buttons, text="Erneut prüfen", command=self.refresh)
        self.again_button.grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Schließen", command=self.destroy).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.results: list[system_check.Check] = []
        self.refresh()

    def refresh(self) -> None:
        """The checks read git, gh and the bridge; they run beside the UI thread."""
        self.again_button.configure(state="disabled")
        self.summary_var.set("Systemcheck läuft …")
        holder: list = []
        threading.Thread(target=lambda: holder.append(self._run(self._root_path)), daemon=True).start()

        def poll() -> None:
            if not self.winfo_exists():
                return
            if not holder:
                self.after(150, poll)
                return
            self.show(holder[0])
        self.after(150, poll)

    def show(self, results: list[system_check.Check]) -> None:
        self.results = list(results)
        for child in self.body.winfo_children():
            child.destroy()
        for row, check in enumerate(self.results):
            mark, color = MARK.get(check.level, ("?", ""))
            ttk.Label(self.body, text=mark, foreground=color, font=("TkDefaultFont", 13, "bold")).grid(
                row=row, column=0, sticky="nw", padx=(0, 6), pady=2)
            ttk.Label(self.body, text=check.name, font=("TkDefaultFont", 12, "bold")).grid(
                row=row, column=1, sticky="nw", padx=(0, 10), pady=2)
            text = check.detail + (f"\n→ {check.fix}" if check.fix else "")
            ttk.Label(self.body, text=text, justify="left", wraplength=480).grid(
                row=row, column=2, sticky="w", pady=2)
        self.summary_var.set(system_check.summary(self.results))
        self.again_button.configure(state="normal")
