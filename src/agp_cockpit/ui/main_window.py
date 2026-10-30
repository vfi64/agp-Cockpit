from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from agp_cockpit import __version__
from agp_cockpit.adapters.macos_settings import bridge_runtime_root
from agp_cockpit.core.hermes_config import DEFAULT_HERMES_CONFIG
from agp_cockpit.core.hermes_runtime import discover_hermes_runtime
from agp_cockpit.core.hermes_writer import update_hermes_model
from agp_cockpit.core.live_startup import execute_live_guarded_startup
from agp_cockpit.core.runtime_identity import runtime_identity_status
from agp_cockpit.core.startup import StartupAction, decide_startup
from agp_cockpit.core.startup_probe import observe_live_read_only
from agp_cockpit.ui.bridge_identity_status import format_bridge_identity_status
from agp_cockpit.ui.hermes_status import format_hermes_status
from agp_cockpit.ui.scrollable import ScrollableTab, follow_viewport
from agp_cockpit.ui.simple_task_panel import SimpleTaskPanel
from agp_cockpit.ui.standard_tasks_panel import StandardTasksPanel
from agp_cockpit.version import BRIDGE_BUILD_ID, BRIDGE_PROTOCOL_VERSION


class MainWindow(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        repository_root: Path | None = None,
        local_contract=None,
    ) -> None:
        super().__init__(master, padding=12)
        self.repository_root = (repository_root or Path.cwd()).expanduser().resolve()
        self.local_contract = local_contract
        self.grid(sticky="nsew")

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.status_var = tk.StringVar(
            value="Lokale Laufzeit bereit"
        )
        self.ollama_var = tk.StringVar(value="")
        self.hermes_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="")
        self.context_var = tk.StringVar(value=f"Repository: {self.repository_root}")
        self.system_focus_var = tk.StringVar(value="Tastaturfokus: —")
        self.bridge_identity_var = tk.StringVar(value="Browser-Bridge wird geprüft …")
        self.ui_variant_var = tk.StringVar(value="")   # AGP_UI_FINGERPRINT_V1

        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 4),
        )
        header.columnconfigure(1, weight=1)

        ttk.Label(
            header,
            text=f"AGP Cockpit v{__version__}",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            header,
            textvariable=self.status_var,
        ).grid(
            row=0,
            column=1,
            sticky="e",
        )

        context = ttk.Frame(self)
        context.grid(row=1, column=0, sticky="ew", pady=(2, 8))
        context.columnconfigure(0, weight=1)
        # AGP_REPO_LINE_V1 (owner 2026-10-07): the repository path has a line of its own
        # and wraps; build and „Repo wechseln …“ follow in the next line (the path was cut).
        self._context_label = ttk.Label(context, textvariable=self.context_var, justify="left",
                                        wraplength=900)
        self._context_label.grid(row=0, column=0, columnspan=3, sticky="w")
        self.build_var = tk.StringVar(
            value=f"Bridge protocol v{BRIDGE_PROTOCOL_VERSION} · build {BRIDGE_BUILD_ID}"
        )
        self._build_label = ttk.Label(context, textvariable=self.build_var, foreground="#888888")
        self._build_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        # AGP_BRANCH_SWITCH_V1 (owner 2026-10-07): the local branch through the Kit route.
        self._branch_button = ttk.Button(context, text="Branch wechseln …", command=self.open_branch_switch)
        self._branch_button.grid(row=1, column=1, sticky="e", padx=(0, 8), pady=(2, 0))
        # AGP_REPOSITORY_SWITCH_V1 (P4): switch only while idle (R5).
        ttk.Button(context, text="Repo wechseln …", command=self.open_repo_switch).grid(
            row=1, column=2, sticky="e", pady=(2, 0))
        # AGP_FRESHNESS_LINE_V1 (owner 2026-10-05): the stale-app warning was appended to
        # the one-line build label and cut off at the window edge; it gets its own line.
        self.freshness_var = tk.StringVar(value="")
        self._freshness_label = ttk.Label(context, textvariable=self.freshness_var, foreground="#d03030",
                                          wraplength=900, justify="left")
        self._freshness_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self._freshness_label.grid_remove()
        # AGP_FRESHNESS_WRAP_V1 (live 2026-10-06): the line was cut at a fixed 900 px.
        context.bind("<Configure>", lambda event: (
            self._freshness_label.configure(wraplength=max(240, event.width - 300)),
            self._context_label.configure(wraplength=max(240, event.width - 8))), add="+")
        # AGP_REBUILD_BUTTON_V1: the guard's warning offers the step it asks for.
        self._rebuild = None
        self._rebuild_kind = ""
        self._rebuild_note = ""   # a failed build stays visible until the next attempt
        self._rebuild_button = ttk.Button(context, text="Neu bauen und neu starten",
                                          command=self.start_rebuild)
        self._rebuild_button.grid(row=2, column=2, sticky="ne", pady=(4, 0))
        self._rebuild_button.grid_remove()

        ttk.Separator(
            self,
            orient="horizontal",
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        self.tabs = ttk.Notebook(self)
        self.tabs.grid(row=3, column=0, sticky="nsew")

        # Plan P3: Standard Tasks first (the guided path), then the free
        # "Arbeiten" tab, which is verb ② of that path.
        # AGP_SCROLLABLE_TABS_V1: every tab scrolls when the window is too small.
        work_tab = ScrollableTab(self.tabs)
        standard_tab = ScrollableTab(self.tabs)
        self.standard_tasks_panel = StandardTasksPanel(
            standard_tab.inner,
            repository_root=self.repository_root,
            local_contract=self.local_contract,
            on_open_work=lambda: self.tabs.select(work_tab),
        )
        self.standard_tasks_panel.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(standard_tab, text="Standard Tasks")

        self.simple_task_panel = SimpleTaskPanel(
            work_tab.inner,
            repository_root=self.repository_root,
            local_contract=self.local_contract,
            on_task_event=lambda event, text="": self._work_task_event(event, standard_tab, text),
            repo_light=lambda: self.standard_tasks_panel.ampel_state,   # AGP_WORK_AMPEL_V1
        )
        # AGP_LAGE_ALL_TABS_V1: a task of the „Arbeiten“ tab counts as running in the Lage.
        self.standard_tasks_panel.external_task_active = self.simple_task_panel.task_active
        self.simple_task_panel.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(work_tab, text="Arbeiten")

        system_tab = ScrollableTab(self.tabs)
        system_tab.inner.rowconfigure(0, weight=0)
        system_tab.inner.rowconfigure(4, weight=1)
        self._build_system_tab(system_tab.inner)
        self.tabs.add(system_tab, text="System")
        self.after(80, self.refresh_runtime_status)
        self.after(120, self.refresh_bridge_identity)
        self.after(500, self.refresh_build_freshness)

    def _work_task_event(self, event: str, standard_tab, text: str = "") -> None:
        """AGP_WORK_TAB_HANDOFF_V1 (owner 2026-10-06): the Lage follows a task of the „Arbeiten“
        tab, and a finished one leads back to the guided path; a decision or a failure stays."""
        panel = self.standard_tasks_panel
        work = self.simple_task_panel
        if event == "finished_done":
            panel.note_external_result(text)
            self.tabs.select(standard_tab)
            if work.auto_finish_armed:
                # AGP_AUTO_FINISH_V1: the tick at the start approved „Abschließen“.
                work.auto_finish_armed = False
                panel.request_auto_finish()
                return
        if event.startswith("finished") and event != "finished_human":
            # AGP_AUTO_FINISH_THROUGH_DECISION_V1: a stop for a decision keeps the tick armed
            work.auto_finish_armed = False
        panel.refresh_lage()

    def open_branch_switch(self) -> None:
        """AGP_BRANCH_SWITCH_V1: idle and clean only; the Kit switches, git verifies."""
        import threading

        from agp_cockpit.core import branch_switch
        from agp_cockpit.core.ci_gate import tool_env
        from agp_cockpit.ui.branch_switch_dialog import ask_branch
        panel = self.standard_tasks_panel
        running = panel._task_running()
        if running:
            panel.status_var.set(branch_switch.block_reason(self.repository_root, "", task_running=True))
            return
        name = ask_branch(self, branch_switch.all_branches(self.repository_root))
        if not name:
            return
        reason = branch_switch.block_reason(self.repository_root, name, task_running=panel._task_running())
        if reason:
            panel.status_var.set(f"Branch wechseln — {reason}")
            return
        kit = self._installed_kit()
        if kit is None:
            panel.status_var.set("Branch wechseln — kein Agentic Project Kit gefunden.")
            return
        self._branch_button.configure(state="disabled")
        panel.status_var.set(f"Branch wechseln — {name} wird über das Kit aktiviert …")
        holder: list = []

        def work() -> None:
            holder.append(branch_switch.switch(self.repository_root, kit.binary, name,
                                               env=tool_env(self.repository_root)))

        def poll() -> None:
            if not holder:
                self.after(200, poll)
                return
            _ok, message = holder[0]
            self._branch_button.configure(state="normal")
            panel.status_var.set(message)
            panel.refresh_lage()
            self.refresh_build_freshness()   # a different build asks for „Neu bauen und neu starten“

        threading.Thread(target=work, daemon=True).start()
        poll()

    def open_repo_switch(self) -> None:
        """Repo wechseln (P4): idle only (R5); check, provision, persist, restart."""
        if self.standard_tasks_panel._task_running():
            self.status_var.set("Repo wechseln erst, wenn kein Task läuft (R5).")
            return None
        from agp_cockpit.adapters.macos_settings import application_support_root
        from agp_cockpit.ui.repo_switch_dialog import RepoSwitchDialog, perform_switch
        app_support = application_support_root()

        def on_switch(root: Path) -> list[str]:
            return perform_switch(root, current=self.repository_root, app_support=app_support,
                                  persist=self._persist_repository, relaunch=self._relaunch)

        return RepoSwitchDialog(self, current=self.repository_root, app_support=app_support,
                                on_switch=on_switch)

    def _persist_repository(self, root: Path) -> None:
        from agp_cockpit.adapters.macos_context import persist_repository_root
        from agp_cockpit.adapters.macos_settings import settings_path
        from agp_cockpit.settings import load_and_migrate_settings
        settings, _migrated = load_and_migrate_settings(settings_path())
        persist_repository_root(settings, root)

    def _relaunch(self) -> None:
        from agp_cockpit.adapters.macos_relaunch import schedule_relaunch
        schedule_relaunch()
        self.after(800, self.winfo_toplevel().destroy)

    def _build_system_tab(self, parent: ttk.Frame) -> None:
        bridge = ttk.LabelFrame(
            parent,
            text="Browser-Bridge",
            padding=8,
        )
        bridge.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
        )
        ttk.Label(
            bridge,
            textvariable=self.bridge_identity_var,
            justify="left",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(bridge, textvariable=self.ui_variant_var, justify="left").grid(
            row=1, column=0, sticky="w")

        ollama = ttk.LabelFrame(
            parent,
            text="Ollama",
            padding=8,
        )
        # AGP_SYSTEM_BOXES_V1 (owner 2026-10-07): Ollama and Hermes share one height and
        # their buttons sit on the same line at the bottom of both boxes.
        ollama.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 4),
            pady=(8, 0),
        )
        ollama.columnconfigure(0, weight=1)
        ollama.rowconfigure(2, weight=1)

        ttk.Label(
            ollama,
            textvariable=self.ollama_var,
            justify="left",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        model_row = ttk.Frame(ollama)
        model_row.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )
        model_row.columnconfigure(1, weight=1)

        ttk.Label(
            model_row,
            text="Modell:",
        ).grid(
            row=0,
            column=0,
            padx=(0, 6),
        )

        self.model_box = ttk.Combobox(
            model_row,
            textvariable=self.model_var,
            state="readonly",
        )
        self.model_box.grid(
            row=0,
            column=1,
            sticky="ew",
        )

        ollama_buttons = ttk.Frame(ollama)
        ollama_buttons.grid(
            row=2,
            column=0,
            sticky="sw",
            pady=(8, 0),
        )

        self.runtime_refresh_button = ttk.Button(
            ollama_buttons,
            text="Aktualisieren",
            command=self.refresh_runtime_status,
            takefocus=True,
        )
        self.runtime_refresh_button.grid(
            row=0,
            column=0,
            padx=(0, 6),
        )

        self.repair_button = ttk.Button(
            ollama_buttons,
            text="Starten / reparieren",
            command=self.run_guarded_ollama_action,
            state="disabled",
        )
        self.repair_button.grid(
            row=0,
            column=1,
        )

        hermes = ttk.LabelFrame(
            parent,
            text="Hermes",
            padding=8,
        )
        hermes.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(4, 0),
            pady=(8, 0),
        )
        hermes.columnconfigure(0, weight=1)
        hermes.rowconfigure(1, weight=1)

        hermes_label = ttk.Label(
            hermes,
            textvariable=self.hermes_var,
            justify="left",
            wraplength=360,
        )
        hermes_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.hermes_model_button = ttk.Button(
            hermes,
            text="Modell übernehmen",
            command=self.apply_selected_model_to_hermes,
            state="disabled",
        )
        self.hermes_model_button.grid(
            row=1,
            column=0,
            sticky="sw",
            pady=(8, 0),
        )

        info = ttk.LabelFrame(
            parent,
            text="Zweck",
            padding=8,
        )
        info.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )
        purpose_label = ttk.Label(
            info,
            text=(
                "Das Cockpit transportiert lokale Aufträge und Ergebnisse. "
                "Workflow-, GitHub- und Sicherheitsentscheidungen bleiben beim Agentic Project Kit."
            ),
            wraplength=760,
            justify="left",
        )
        purpose_label.grid(
            row=0,
            column=0,
            sticky="w",
        )
        # AGP_KIT_FINDINGS_VIEW_V1 / AGP_MAINTENANCE_CLEANUP_V1
        tools = ttk.LabelFrame(parent, text="Werkzeuge", padding=8)
        tools.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        # One tool per row; the description wraps instead of being cut off.
        tools.columnconfigure(1, weight=1)
        ttk.Button(tools, text="Kit-Befunde …", command=self.open_kit_findings).grid(row=0, column=0, sticky="ew")
        findings_label = ttk.Label(tools, text="Fehler des Kits aus der Arbeit an diesem Projekt, mit Status",
                                   foreground="#888888", wraplength=520, justify="left")
        findings_label.grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(tools, text="Aufräumen …", command=self.open_cleanup).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        cleanup_label = ttk.Label(tools, text="alte Arbeitsdateien und Kit-Logs, mit Vorschau",
                                  foreground="#888888", wraplength=520, justify="left")
        cleanup_label.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        # AGP_SYSTEM_CHECK_V1 (plan item 5): every task precondition at a glance, with the fix.
        ttk.Button(tools, text="Systemcheck …", command=self.open_system_check).grid(
            row=2, column=0, sticky="ew", pady=(4, 0))
        check_label = ttk.Label(tools, text="Build, Bridge, Erweiterung, Kit, Repository, GitHub, Speicher — mit Lösungsweg",
                                foreground="#888888", wraplength=520, justify="left")
        check_label.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(4, 0))

        def wrap_system(width: int) -> None:
            """AGP_VIEWPORT_WRAP_V1 (live 2026-10-07): the System tab wraps to the visible width."""
            purpose_label.configure(wraplength=max(200, width - 60))
            hermes_label.configure(wraplength=max(160, width // 2 - 60))
            for label in (findings_label, cleanup_label, check_label):
                label.configure(wraplength=max(160, width - 220))
        follow_viewport(parent, wrap_system)
        ttk.Label(parent,textvariable=self.system_focus_var).grid(row=4,column=0,columnspan=2,sticky="w",pady=(8,0))
        system_focus_names={
            self.model_box:"Modell",
            self.runtime_refresh_button:"Aktualisieren",
            self.repair_button:"Starten / reparieren",
            self.hermes_model_button:"Modell übernehmen",
        }
        for widget,name in system_focus_names.items():
            widget.bind("<FocusIn>",lambda _e,n=name:self.system_focus_var.set(f"Tastaturfokus: {n}"),add="+")

    def _installed_kit(self):
        from agp_cockpit.core.kit_installation import discover
        try:
            return discover(self.repository_root)
        except Exception:  # noqa: BLE001 - shown as "not found"
            return None

    def open_kit_findings(self) -> None:
        """AGP_FINDINGS_FROM_COCKPIT_V1 (live 2026-10-06, P4 in the Kit repository): the register
        belongs to the Cockpit's own checkout, never to the steered repository."""
        from agp_cockpit.core.build_freshness import freshness_root
        from agp_cockpit.core.kit_installation import discover
        from agp_cockpit.ui.kit_findings_window import KitFindingsWindow
        home = freshness_root(self.repository_root)
        try:
            kit = discover(home)
        except Exception:  # noqa: BLE001 - shown as "not found"
            kit = None
        KitFindingsWindow(self, repository_root=home, installed_version=getattr(kit, "version", None))

    def open_system_check(self) -> None:
        """AGP_SYSTEM_CHECK_V1: read-only; checks the repository this Cockpit steers."""
        from agp_cockpit.ui.system_check_window import SystemCheckWindow
        SystemCheckWindow(self, repository_root=self.repository_root)

    def open_cleanup(self) -> None:
        """AGP_MAINTENANCE_CLEANUP_V1: preview first, delete only after OK, never while a task runs."""
        from agp_cockpit.core import maintenance
        from agp_cockpit.core.mission_http_client import status as bridge_status
        try:
            mission = (bridge_status() or {}).get("mission") or {}
        except Exception:  # noqa: BLE001 - an unreachable bridge runs no task
            mission = {}
        if mission and str(mission.get("state") or "") not in {
                "", "IDLE", "DONE", "COMPLETED", "NEEDS_HUMAN", "BLOCKED", "FAILED", "ERROR", "STOPPED", "CANCELLED"}:
            messagebox.showinfo("Aufräumen", "Ein Task läuft — Aufräumen erst nach seinem Ende.", parent=self)
            return
        kit = self._installed_kit()
        binary = getattr(kit, "binary", None)
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            plan = maintenance.plan(self.repository_root, kit_binary=binary)
        finally:
            self.configure(cursor="")
        if maintenance.nothing_to_do(plan):   # AGP_CLEANUP_PREVIEW_WINDOW_V1
            messagebox.showinfo("Aufräumen", "Nichts zu löschen.\n\n" + maintenance.describe(plan), parent=self)
            return
        from agp_cockpit.ui import cleanup_preview
        if not cleanup_preview.ask(self, plan):
            return
        outcome = maintenance.execute(self.repository_root, plan, kit_binary=binary)
        messagebox.showinfo(
            "Aufräumen",
            f"Gelöscht: {outcome['deleted']} Einträge, {outcome['bytes'] / 1e6:.1f} MB"
            + (f"; übersprungen: {len(outcome['skipped'])}" if outcome["skipped"] else "")
            + (f"\n\n{outcome['kit_output']}" if outcome["kit_output"] else ""),
            parent=self)

    def refresh_build_freshness(self) -> None:
        """AGP_STALE_APP_GUARD_V1: warn while a newer build or source is on disk."""
        from agp_cockpit.core.build_freshness import check, freshness_root
        base = f"Bridge protocol v{BRIDGE_PROTOCOL_VERSION} · build {BRIDGE_BUILD_ID}"
        try:
            freshness = check(freshness_root(self.repository_root))
        except Exception:  # noqa: BLE001 - a status label must never break the UI
            freshness = None
        if self._rebuild is not None:
            pass   # the rebuild owns the line until it ends (see _watch_rebuild)
        elif freshness is not None and freshness.stale:
            self.build_var.set(f"{base} · ⚠ veraltet")
            self._build_label.configure(foreground="#d03030")
            self.freshness_var.set(self._rebuild_note or f"⚠ {freshness.message}")
            self._freshness_label.configure(foreground="#d03030")
            self._freshness_label.grid()
            self._show_rebuild(freshness)
        elif freshness is not None and freshness.note:
            # AGP_RELEASE_IN_PROGRESS_V1: a running release is no stale app — yellow, no button.
            self.build_var.set(base)
            self._build_label.configure(foreground="")
            self.freshness_var.set(freshness.note)
            self._freshness_label.configure(foreground="#c8a020")
            self._freshness_label.grid()
            self._rebuild_button.grid_remove()
        else:
            self.build_var.set(base)
            self._build_label.configure(foreground="")
            self.freshness_var.set("")
            self._rebuild_note = ""
            self._freshness_label.grid_remove()
            self._rebuild_button.grid_remove()
        self.after(10_000, self.refresh_build_freshness)

    def _show_rebuild(self, freshness) -> None:
        import sys

        from agp_cockpit.core import app_rebuild
        kind = app_rebuild.offer(freshness) if getattr(sys, "frozen", False) else ""
        self._rebuild_kind = kind
        if kind:
            self._rebuild_button.configure(text=app_rebuild.label(kind), state="normal")
            self._rebuild_button.grid()
        else:
            self._rebuild_button.grid_remove()

    def start_rebuild(self) -> bool:
        """AGP_REBUILD_BUTTON_V1: build (if needed), then close and reopen the app."""
        from agp_cockpit.core import app_rebuild
        from agp_cockpit.core.build_freshness import cockpit_home
        from agp_cockpit.core.mission_http_client import task_running
        kind = self._rebuild_kind or app_rebuild.BUILD
        home = cockpit_home()
        blocked = app_rebuild.block_reason(home, task_running=task_running(), kind=kind)
        if blocked:
            messagebox.showwarning(app_rebuild.label(kind), blocked, parent=self)
            return False
        what = ("Die App wird aus dem aktuellen Stand des Cockpit-Checkouts neu gebaut (1–2 Minuten), "
                "danach geschlossen und neu geöffnet. Schlägt der Bau fehl, läuft sie weiter."
                if kind == app_rebuild.BUILD else "Die App wird geschlossen und der neuere Build geöffnet.")
        if not messagebox.askyesno(app_rebuild.label(kind),
                                   f"{what}\n\nDie Chrome-Erweiterung lädt sich danach selbst neu.\n\n"
                                   "Fortfahren?", parent=self):
            return False
        self._rebuild_button.configure(state="disabled")
        self._rebuild_note = ""
        if kind == app_rebuild.RESTART:
            return self._relaunch_new_build(home)
        try:
            self._rebuild = app_rebuild.start(home)
        except Exception as exc:  # noqa: BLE001 - shown to the operator
            self._rebuild_button.configure(state="normal")
            messagebox.showerror(app_rebuild.label(kind), f"Start fehlgeschlagen: {exc}", parent=self)
            return False
        self.freshness_var.set(f"Neubau läuft … Protokoll: {self._rebuild.log}")
        self._freshness_label.grid()
        self.after(2000, self._watch_rebuild)
        return True

    def _watch_rebuild(self) -> None:
        from agp_cockpit.core.build_freshness import cockpit_home
        rebuild = self._rebuild
        if rebuild is None:
            return
        code = rebuild.returncode()
        if code is None:
            self.after(2000, self._watch_rebuild)
            return
        self._rebuild = None
        if code != 0:
            # One or two lines only (the window is shared with Chrome); the log has the rest.
            cause = rebuild.cause() or f"Code {code}"
            self._rebuild_note = (f"⚠ Neubau fehlgeschlagen, die App läuft weiter: {cause}\n"
                                  f"Protokoll: .local/agp-cockpit/logs/{rebuild.log.name}")
            self.freshness_var.set(self._rebuild_note)
            self._rebuild_button.configure(state="normal")
            return
        self._relaunch_new_build(cockpit_home())

    def _relaunch_new_build(self, home) -> bool:
        # AGP_UNIQUE_METHODS_V1 (live 2026-10-06): this was also named _relaunch and silently
        # replaced the repository switch's _relaunch() („missing 1 required positional
        # argument: 'home'“); tests/test_unique_methods.py now rejects any duplicate.
        import os

        from agp_cockpit.core import app_rebuild
        from agp_cockpit.core.mission_http_client import task_running
        if task_running():   # a task started while the build ran: never cut it off
            self._rebuild_note = ("Neuer Build ist fertig, aber ein Task läuft — nach seinem Ende "
                                  "„Neu starten“ klicken.")
            self.freshness_var.set(self._rebuild_note)
            self._rebuild_kind = app_rebuild.RESTART
            self._rebuild_button.configure(text=app_rebuild.label(app_rebuild.RESTART), state="normal")
            return False
        try:
            app_rebuild.relaunch(home, os.getpid())
        except Exception as exc:  # noqa: BLE001 - shown to the operator
            self._rebuild_note = f"⚠ Neustart nicht möglich: {exc}"
            self.freshness_var.set(self._rebuild_note)
            self._rebuild_button.configure(state="normal")
            return False
        self.freshness_var.set("Die App wird neu gestartet …")
        self.after(300, self.winfo_toplevel().destroy)   # mainloop ends, the bridge stops cleanly
        return True

    def refresh_bridge_identity(self) -> None:
        try:
            identity = runtime_identity_status(
                self.repository_root,
                bridge_runtime_root(),
            )
            self.bridge_identity_var.set(format_bridge_identity_status(identity))
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces diagnostics.
            self.bridge_identity_var.set(f"Status: Diagnosefehler\n{exc}")
        finally:
            self.after(2_000, self.refresh_bridge_identity)
        self.refresh_ui_variant()

    def refresh_ui_variant(self) -> None:
        """AGP_UI_FINGERPRINT_V1: the ChatGPT UI variant under the bridge identity."""
        var = getattr(self, "ui_variant_var", None)
        if var is None:
            return
        try:
            from agp_cockpit.core.ui_observation import variant_line
            var.set(variant_line(self.repository_root))
        except Exception:  # noqa: BLE001 - an observation line never breaks the System tab
            var.set("ChatGPT-Oberfläche: nicht lesbar")

    def refresh_runtime_status(self) -> None:
        try:
            obs = observe_live_read_only()
            decision = decide_startup(obs)

            self.ollama_var.set(
                "\n".join((
                    f"Installiert: {'ja' if obs.ollama_installed else 'nein'}",
                    f"Port 11434: {'belegt' if obs.port_busy else 'frei'}",
                    f"Portbesitzer: {'Ollama' if obs.port_owner_is_ollama else 'fremd/keiner'}",
                    f"API: {'erreichbar' if obs.api_reachable else 'nicht erreichbar'}",
                ))
            )

            models = tuple(obs.models)
            self.model_box["values"] = models

            hermes = discover_hermes_runtime(
                ollama_models=models,
            )
            self.hermes_var.set(
                format_hermes_status(hermes)
            )

            preferred = hermes.config.model
            current = self.model_var.get()

            if preferred and preferred in models:
                self.model_var.set(preferred)
            elif current in models:
                pass
            elif models:
                self.model_var.set(models[0])
            else:
                self.model_var.set("")

            healthy = (
                obs.ollama_installed
                and obs.api_reachable
                and bool(models)
            )

            if healthy:
                self.status_var.set(
                    "Ollama bereit · Hermes geprüft"
                )
            else:
                self.status_var.set(
                    decision.message
                )

            if decision.action in (
                StartupAction.START_OLLAMA,
                StartupAction.RECOVER_OLLAMA,
            ):
                self.repair_button.configure(
                    state="normal"
                )
            else:
                self.repair_button.configure(
                    state="disabled"
                )

            can_write_hermes = (
                bool(models)
                and hermes.config.exists
                and hermes.config.error is None
                and hermes.config.model_path is not None
            )
            self.hermes_model_button.configure(
                state=(
                    "normal"
                    if can_write_hermes
                    else "disabled"
                )
            )

        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces diagnostics.
            self.status_var.set(
                f"Diagnosefehler: {exc}"
            )
            self.ollama_var.set("")
            self.hermes_var.set("")
            self.model_box["values"] = ()
            self.model_var.set("")
            self.repair_button.configure(
                state="disabled"
            )
            self.hermes_model_button.configure(
                state="disabled"
            )

    def run_guarded_ollama_action(self) -> None:
        self.repair_button.configure(
            state="disabled"
        )
        self.status_var.set(
            "Ollama-Aktion läuft …"
        )
        self.update_idletasks()

        try:
            result = execute_live_guarded_startup()
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces startup failures.
            messagebox.showerror(
                "Ollama konnte nicht vorbereitet werden",
                str(exc),
                parent=self.winfo_toplevel(),
            )
            self.refresh_runtime_status()
            return

        self.refresh_runtime_status()

        if result.ok:
            messagebox.showinfo(
                "Ollama bereit",
                "Ollama ist erreichbar und mindestens ein Modell ist verfügbar.",
                parent=self.winfo_toplevel(),
            )
        else:
            messagebox.showwarning(
                "Ollama nicht bereit",
                result.decision.message,
                parent=self.winfo_toplevel(),
            )

    def apply_selected_model_to_hermes(self) -> None:
        selected = self.model_var.get().strip()
        if not selected:
            messagebox.showwarning(
                "Kein Modell ausgewählt",
                "Bitte zuerst ein Modell auswählen.",
                parent=self.winfo_toplevel(),
            )
            return

        confirmed = messagebox.askyesno(
            "Hermes-Modell ändern",
            (
                f"Soll Hermes künftig {selected} verwenden?\n\n"
                "AGP Cockpit legt vorher ein Backup der Konfiguration an."
            ),
            parent=self.winfo_toplevel(),
        )
        if not confirmed:
            return

        try:
            result = update_hermes_model(
                selected,
                path=DEFAULT_HERMES_CONFIG,
            )
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces config failures.
            messagebox.showerror(
                "Hermes-Konfiguration nicht geändert",
                str(exc),
                parent=self.winfo_toplevel(),
            )
            self.refresh_runtime_status()
            return

        self.refresh_runtime_status()

        messagebox.showinfo(
            "Hermes-Modell aktualisiert",
            (
                f"Hermes verwendet jetzt: {result.new_model}\n\n"
                f"Backup: {result.backup_path}"
            ),
            parent=self.winfo_toplevel(),
        )
