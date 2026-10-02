"""Repo wechseln (plan P4, AGP_REPOSITORY_SWITCH_V1) — dialog and switch flow."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from agp_cockpit.core import repository_switch as rsw


def perform_switch(candidate: Path, *, current: Path, app_support: Path, persist, relaunch,
                   check=rsw.check, provision=rsw.provision) -> list[str]:
    """Check again, provision the transport paths, persist, remember, restart.

    Raises on a failed check or provisioning; nothing is persisted then.
    """
    result = check(candidate, current=current)
    if not result.ok:
        raise ValueError("; ".join(result.blockers))
    root = Path(result.root)
    actions = provision(root)
    persist(root)
    rsw.remember(app_support, current)  # the previous repository stays one click away
    rsw.remember(app_support, root)
    relaunch()
    return actions


class RepoSwitchDialog(tk.Toplevel):
    def __init__(self, master, *, current: Path, app_support: Path, on_switch,
                 check=rsw.check, choose_directory=None) -> None:
        super().__init__(master)
        self.title("Repo wechseln")
        self.current = Path(current)
        self.on_switch = on_switch
        self._check = check
        self._choose = choose_directory or (lambda: filedialog.askdirectory(
            parent=self, title="Repository auswählen", mustexist=True))
        self.candidate: Path | None = None
        self.result = None
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=f"Aktuell: {self.current}").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ttk.Label(self, text="Zuletzt verwendet:").grid(row=1, column=0, sticky="w", padx=12)
        self.recent = [p for p in rsw.load_recent(app_support) if Path(p) != self.current]
        self.listbox = tk.Listbox(self, height=min(6, max(2, len(self.recent))), width=80)
        for entry in self.recent:
            self.listbox.insert("end", entry)
        self.listbox.grid(row=2, column=0, sticky="ew", padx=12)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self._select_recent())
        ttk.Button(self, text="Anderen Ordner wählen …", command=self._choose_folder).grid(
            row=3, column=0, sticky="w", padx=12, pady=6)
        self.report = tk.StringVar(value="Repository auswählen — es wird nur gelesen geprüft.")
        ttk.Label(self, textvariable=self.report, justify="left", wraplength=640).grid(
            row=4, column=0, sticky="w", padx=12, pady=6)
        buttons = ttk.Frame(self)
        buttons.grid(row=5, column=0, sticky="e", padx=12, pady=(0, 12))
        self.switch_button = ttk.Button(buttons, text="Wechseln und neu starten", command=self._switch,
                                        state="disabled")
        self.switch_button.grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Abbrechen", command=self.destroy).grid(row=0, column=1)

    def _select_recent(self) -> None:
        selection = self.listbox.curselection()
        if selection:
            self.evaluate(Path(self.recent[selection[0]]))

    def _choose_folder(self) -> None:
        chosen = self._choose()
        if chosen:
            self.evaluate(Path(chosen))

    def evaluate(self, candidate: Path) -> None:
        self.candidate = Path(candidate)
        self.result = self._check(self.candidate, current=self.current)
        self.report.set(self.result.text())
        self.switch_button.configure(state="normal" if self.result.ok else "disabled")

    def _switch(self) -> None:
        if self.result is None or not self.result.ok:
            return
        try:
            actions = self.on_switch(Path(self.result.root))
        except Exception as exc:  # noqa: BLE001 - UI boundary shows every failure
            self.report.set(f"Wechsel nicht möglich: {exc}")
            return
        done = "; ".join(actions) if actions else "keine Vorbereitung nötig"
        self.report.set(f"Gewechselt ({done}). Das Cockpit startet neu …")
        self.switch_button.configure(state="disabled")
