"""Read-only window over the Kit findings register (AGP_KIT_FINDINGS_VIEW_V1)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from agp_cockpit.core import kit_findings as kf

FILTERS = ("Alle", "Offen", "In Arbeit", "Behoben")


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
        # AGP_KIT_FINDINGS_SYNC_V1: the Kit's own adjudication from its public repository.
        self.sync_button = ttk.Button(bar, text="Mit Kit-Repo abgleichen", command=self.sync_with_kit)
        self.sync_button.grid(row=0, column=3, padx=(16, 0))
        self.sync_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.sync_var, foreground="#888888").grid(row=0, column=4, padx=(8, 0))

        body = ttk.Panedwindow(self, orient="vertical")
        body.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 12))
        table = ttk.Frame(body)
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        columns = ("id", "title", "severity", "status", "first")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=12, selectmode="browse")
        self.labels = {"id": "ID", "title": "Titel", "severity": "Schwere", "status": "Status", "first": "Seit"}
        self.sort_column, self.sort_reverse = "id", False   # AGP_FINDINGS_SORT_V1: opens sorted by ID
        for key, width in (("id", 190), ("title", 430), ("severity", 90), ("status", 170), ("first", 90)):
            self.tree.heading(key, text=self.labels[key], command=lambda column=key: self.sort_by(column))
            self.tree.column(key, width=width, stretch=key == "title", anchor="w")
        self.tree.tag_configure("fixed", foreground="#3c7fd0")
        self.tree.tag_configure("progress", foreground="#d0a000")
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

    def sync_with_kit(self) -> None:
        import threading

        from agp_cockpit.core.kit_findings_sync import sync
        self.sync_button.configure(state="disabled")
        self.sync_var.set("Abgleich läuft …")
        holder: list = []

        def work() -> None:
            try:
                holder.append(sync(self.repository_root))
            except Exception as exc:  # noqa: BLE001 - shown in the window
                holder.append(exc)

        def poll() -> None:
            if not holder:
                self.after(200, poll)
                return
            self.sync_button.configure(state="normal")
            if isinstance(holder[0], Exception):
                self.sync_var.set(f"Abgleich fehlgeschlagen: {holder[0]}")
                return
            self.reload()

        threading.Thread(target=work, daemon=True).start()
        poll()

    def reload(self) -> None:
        from agp_cockpit.core.kit_findings_sync import load_overlay
        overlay = load_overlay(self.repository_root)
        self.sync_var.set(
            f"Kit-Repo-Stand {str(overlay.get('kit_commit') or '')[:12]} (letztes Release {overlay.get('latest_release')})"
            if overlay else "noch nicht abgeglichen — Stand des Registers")
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
        if wanted == "In Arbeit":
            return [f for f in self.findings if f.effective_status(self.installed) == kf.IN_PROGRESS]
        if wanted == "Behoben":
            return [f for f in self.findings
                    if f.effective_status(self.installed) not in {kf.OPEN, kf.IN_PROGRESS}]
        return list(self.findings)

    def sort_by(self, column: str) -> None:
        """A click on a column head sorts by it; a second click reverses the order."""
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        self.sort_column = column
        selected = self.tree.selection()
        self.populate(keep=selected[0] if selected else None)

    def populate(self, keep: str | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for key, label in self.labels.items():
            arrow = (" ▼" if self.sort_reverse else " ▲") if key == self.sort_column else ""
            self.tree.heading(key, text=label + arrow)
        ordered = sorted(self.visible(), key=lambda f: kf.sort_key(f, self.sort_column, self.installed),
                         reverse=self.sort_reverse)
        for finding in ordered:
            status = finding.effective_status(self.installed)
            tag = {kf.OPEN: "open", kf.IN_PROGRESS: "progress", kf.VERIFIED: "verified"}.get(status, "fixed")
            self.tree.insert("", "end", iid=finding.id, tags=(tag,), values=(
                finding.id, finding.title, finding.severity, status, finding.first_observed))
        children = self.tree.get_children()
        if keep in children:
            self.tree.selection_set(keep)
            self.tree.see(keep)
            self.show_selected()
        elif children:
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
