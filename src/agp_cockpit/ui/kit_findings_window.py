"""Read-only window over the Kit findings register (AGP_KIT_FINDINGS_VIEW_V1).

AGP_KIT_CATALOG_GROUP_V1 (plan C5): entries of the installed Kit's catalog (``greenfield status``) that the
register does not list are a group of their own below the register's rows. The Kit is asked beside the UI
thread; the worker gets plain values only and the answer is read on the UI thread
(AGP_TK_GC_ON_MAIN_THREAD_V1).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk

from agp_cockpit.core import kit_findings as kf

FILTERS = ("Alle", "Offen", "In Arbeit", "Behoben")
CATALOG_GROUP = "kit-catalog-group"
CATALOG_GROUP_TEXT = ("Nur im Kit-Katalog: Diese Befunde führt das installierte Kit (agentic-kit greenfield status), "
                      "das Register des Cockpits aber nicht. Kennung, Titel, Zustand und „behoben in“ sind die "
                      "Angaben des Kits; das Cockpit bewertet sie nicht und trägt sie nicht ins Register ein.")


class KitFindingsWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, *, repository_root: Path, installed_version: str | None,
                 catalog_reader: Callable[[Path], kf.KitCatalog] | None = None) -> None:
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
        self.catalog_var = tk.StringVar(value=kf.catalog_summary([], None))
        ttk.Label(head, textvariable=self.catalog_var, foreground="#888888").grid(
            row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(head, text=f"Installiertes Kit: {installed_version or 'nicht gefunden'}").grid(
            row=0, column=2, sticky="e")

        bar = ttk.Frame(self, padding=(12, 4))
        bar.grid(row=1, column=0, sticky="ew")
        ttk.Label(bar, text="Anzeigen:").grid(row=0, column=0, padx=(0, 6))
        self.filter_var = tk.StringVar(value="Offen")
        self.filter_box = ttk.Combobox(bar, textvariable=self.filter_var, values=FILTERS, state="readonly", width=10)
        self.filter_box.grid(row=0, column=1)
        self.filter_box.bind("<<ComboboxSelected>>", lambda _e: self.populate())
        ttk.Label(bar, text="Quelle: docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json und Kit-Katalog (nur lesen)",
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
        self.tree.tag_configure("group", foreground="#666666", background="#eeeeee")
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
        self.catalog: kf.KitCatalog | None = None
        self.catalog_findings: list[kf.KitFinding] = []
        self.catalog_reader = catalog_reader or kf.read_catalog
        self.reload()
        self.load_catalog()

    def load_catalog(self) -> None:
        """AGP_KIT_CATALOG_GROUP_V1: the installed Kit's catalog, read beside the UI thread."""
        import threading
        reader, root = self.catalog_reader, Path(self.repository_root)
        holder: list = []

        def work() -> None:          # plain values only: no Tk object in this frame
            try:
                holder.append(reader(root))
            except Exception as exc:  # noqa: BLE001 - shown in the window
                holder.append(kf.KitCatalog(reason=f"{type(exc).__name__}: {exc}"))

        def poll() -> None:
            try:
                if not self.winfo_exists():
                    return
            except tk.TclError:
                return
            if not holder:
                self.after(200, poll)
                return
            self.catalog = holder[0]
            self._merge_catalog()
            selected = self.tree.selection()
            self.populate(keep=selected[0] if selected else None)

        threading.Thread(target=work, daemon=True).start()
        poll()

    def _merge_catalog(self) -> None:
        self.catalog_findings = kf.catalog_only(self.findings, self.catalog)
        self.catalog_var.set(kf.catalog_summary(self.catalog_findings, self.catalog))

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
        self._merge_catalog()
        self.populate()

    def visible(self, findings: list[kf.KitFinding] | None = None) -> list[kf.KitFinding]:
        findings = self.findings if findings is None else findings
        wanted = self.filter_var.get()
        if wanted == "Offen":
            return [f for f in findings if f.effective_status(self.installed) == kf.OPEN]
        if wanted == "In Arbeit":
            return [f for f in findings if f.effective_status(self.installed) == kf.IN_PROGRESS]
        if wanted == "Behoben":
            return [f for f in findings
                    if f.effective_status(self.installed) not in {kf.OPEN, kf.IN_PROGRESS}]
        return list(findings)

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

        def ordered(findings: list[kf.KitFinding]) -> list[kf.KitFinding]:
            return sorted(self.visible(findings), key=lambda f: kf.sort_key(f, self.sort_column, self.installed),
                          reverse=self.sort_reverse)

        def insert(parent: str, finding: kf.KitFinding) -> None:
            status = finding.effective_status(self.installed)
            tag = {kf.OPEN: "open", kf.IN_PROGRESS: "progress", kf.VERIFIED: "verified"}.get(status, "fixed")
            self.tree.insert(parent, "end", iid=finding.id, tags=(tag,), values=(
                finding.id, finding.title, finding.severity, status, finding.first_observed))

        children = []
        for finding in ordered(self.findings):
            insert("", finding)
            children.append(finding.id)
        extra = ordered(self.catalog_findings)        # AGP_KIT_CATALOG_GROUP_V1: always below the register
        if extra:
            self.tree.insert("", "end", iid=CATALOG_GROUP, open=True, tags=("group",), values=(
                "Nur im Kit-Katalog", f"{len(extra)} Befunde des installierten Kits, die das Register nicht führt",
                "", "", ""))
            for finding in extra:
                insert(CATALOG_GROUP, finding)
                children.append(finding.id)
        if keep in children or keep == CATALOG_GROUP and extra:
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
        if selected and selected[0] == CATALOG_GROUP:
            self._set_detail(CATALOG_GROUP_TEXT)
            return
        finding = next((f for f in [*self.findings, *self.catalog_findings] if selected and f.id == selected[0]), None)
        if finding is not None:
            self._set_detail(finding.detail_text(self.installed))

    def _set_detail(self, text: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")
