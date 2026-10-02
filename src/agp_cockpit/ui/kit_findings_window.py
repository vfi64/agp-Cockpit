"""Read-only window over the Kit findings register (AGP_KIT_FINDINGS_VIEW_V1)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from agp_cockpit.core import kit_findings as kf

FILTERS = ("Alle", "Offen", "Behoben")


class KitFindingsWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, *, repository_root: Path, installed_version: str | None) -> None:
        super().__init__(master)
        self.title("Kit-Befunde")
        self.geometry("1000x640")
        self.repository_root = Path(repository_root)
        self.installed = installed_version
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        head = ttk.Frame(self, padding=(12, 10, 12, 4))
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(1, weight=1)
        ttk.Label(head, text="Kit-Befunde", font=("TkDefaultFont", 15, "bold")).grid(row=0, column=0, sticky="w")
        self.summary_var = tk.StringVar()
        ttk.Label(head, textvariable=self.summary_var).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))
        ttk.Label(head, text=f"Installiertes Kit: {installed_version or 'nicht gefunden'}").grid(
            row=0, column=2, sticky="e")

        bar = ttk.Frame(self, padding=(12, 4))
        bar.grid(row=1, column=0, sticky="ew")
        ttk.Label(bar, text="Anzeigen:").grid(row=0, column=0, padx=(0, 6))
        self.filter_var = tk.StringVar(value="Offen")
        self.filter_box = ttk.Combobox(bar, textvariable=self.filter_var, values=FILTERS, state="readonly", width=10)
        self.filter_box.grid(row=0, column=1)
        self.filter_box.bind("<<ComboboxSelected>>", lambda _e: self.populate())
        ttk.Label(bar, text="Quelle: docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json (nur lesen)",
                  foreground="#888888").grid(row=0, column=2, padx=(16, 0))

        body = ttk.Panedwindow(self, orient="vertical")
        body.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 12))
        table = ttk.Frame(body)
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        columns = ("id", "title", "severity", "status", "first")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=12, selectmode="browse")
        for key, label, width in (("id", "ID", 190), ("title", "Titel", 430), ("severity", "Schwere", 90),
                                  ("status", "Status", 170), ("first", "Seit", 90)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, stretch=key == "title", anchor="w")
        self.tree.tag_configure("fixed", foreground="#d0a000")
        self.tree.tag_configure("verified", foreground="#3c9a3c")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        body.add(table, weight=3)
        detail = ttk.Frame(body)
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(0, weight=1)
        self.detail = tk.Text(detail, wrap="word", height=12, padx=8, pady=6)
        detail_scroll = ttk.Scrollbar(detail, orient="vertical", command=self.detail.yview)
        self.detail.configure(yscrollcommand=detail_scroll.set, state="disabled")
        self.detail.grid(row=0, column=0, sticky="nsew")
        detail_scroll.grid(row=0, column=1, sticky="ns")
        body.add(detail, weight=2)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.show_selected())

        self.findings: list[kf.KitFinding] = []
        self.reload()

    def reload(self) -> None:
        try:
            self.findings = kf.load(self.repository_root)
        except (OSError, ValueError) as exc:
            self.findings = []
            self.summary_var.set(f"Register nicht lesbar: {exc}")
            return
        self.summary_var.set(kf.summary(self.findings, self.installed))
        self.populate()

    def visible(self) -> list[kf.KitFinding]:
        wanted = self.filter_var.get()
        if wanted == "Offen":
            return [f for f in self.findings if f.effective_status(self.installed) == kf.OPEN]
        if wanted == "Behoben":
            return [f for f in self.findings if f.effective_status(self.installed) != kf.OPEN]
        return list(self.findings)

    def populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for finding in self.visible():
            status = finding.effective_status(self.installed)
            tag = {kf.OPEN: "open", kf.VERIFIED: "verified"}.get(status, "fixed")
            self.tree.insert("", "end", iid=finding.id, tags=(tag,), values=(
                finding.id, finding.title, finding.severity, status, finding.first_observed))
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.show_selected()
        else:
            self._set_detail("Keine Befunde in dieser Auswahl.")

    def show_selected(self) -> None:
        selected = self.tree.selection()
        finding = next((f for f in self.findings if selected and f.id == selected[0]), None)
        if finding is not None:
            self._set_detail(finding.detail_text(self.installed))

    def _set_detail(self, text: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")
