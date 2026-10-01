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
        ttk.Label(context, textvariable=self.context_var).grid(row=0, column=0, sticky="w")
        self.build_var = tk.StringVar(
            value=f"Bridge protocol v{BRIDGE_PROTOCOL_VERSION} · build {BRIDGE_BUILD_ID}"
        )
        self._build_label = ttk.Label(context, textvariable=self.build_var)
        self._build_label.grid(row=0, column=1, sticky="e")

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

        work_tab = ttk.Frame(self.tabs)
        work_tab.columnconfigure(0, weight=1)
        work_tab.rowconfigure(0, weight=1)
        self.simple_task_panel = SimpleTaskPanel(
            work_tab,
            repository_root=self.repository_root,
            local_contract=self.local_contract,
        )
        self.simple_task_panel.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(work_tab, text="Arbeiten")

        standard_tab = ttk.Frame(self.tabs)
        standard_tab.columnconfigure(0, weight=1)
        standard_tab.rowconfigure(0, weight=1)
        self.standard_tasks_panel = StandardTasksPanel(
            standard_tab,
            repository_root=self.repository_root,
            local_contract=self.local_contract,
        )
        self.standard_tasks_panel.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(standard_tab, text="Standard Tasks")

        system_tab = ttk.Frame(self.tabs)
        system_tab.columnconfigure(0, weight=1)
        system_tab.rowconfigure(4, weight=1)
        self._build_system_tab(system_tab)
        self.tabs.add(system_tab, text="System")
        self.after(80, self.refresh_runtime_status)
        self.after(120, self.refresh_bridge_identity)
        self.after(500, self.refresh_build_freshness)

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

        ollama = ttk.LabelFrame(
            parent,
            text="Ollama",
            padding=8,
        )
        ollama.grid(
            row=1,
            column=0,
            sticky="new",
            padx=(0, 4),
            pady=(8, 0),
        )
        ollama.columnconfigure(0, weight=1)

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
            sticky="w",
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
            sticky="new",
            padx=(4, 0),
            pady=(8, 0),
        )
        hermes.columnconfigure(0, weight=1)

        ttk.Label(
            hermes,
            textvariable=self.hermes_var,
            justify="left",
            wraplength=360,
        ).grid(
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
            sticky="w",
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
        ttk.Label(
            info,
            text=(
                "Das Cockpit transportiert lokale Aufträge und Ergebnisse. "
                "Workflow-, GitHub- und Sicherheitsentscheidungen bleiben beim Agentic Project Kit."
            ),
            wraplength=760,
            justify="left",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(parent,textvariable=self.system_focus_var).grid(row=3,column=0,columnspan=2,sticky="w",pady=(8,0))
        system_focus_names={
            self.model_box:"Modell",
            self.runtime_refresh_button:"Aktualisieren",
            self.repair_button:"Starten / reparieren",
            self.hermes_model_button:"Modell übernehmen",
        }
        for widget,name in system_focus_names.items():
            widget.bind("<FocusIn>",lambda _e,n=name:self.system_focus_var.set(f"Tastaturfokus: {n}"),add="+")

    def refresh_build_freshness(self) -> None:
        """AGP_STALE_APP_GUARD_V1: warn while a newer build or source is on disk."""
        from agp_cockpit.core.build_freshness import check
        base = f"Bridge protocol v{BRIDGE_PROTOCOL_VERSION} · build {BRIDGE_BUILD_ID}"
        try:
            freshness = check(self.repository_root)
        except Exception:  # noqa: BLE001 - a status label must never break the UI
            freshness = None
        if freshness is not None and freshness.stale:
            self.build_var.set(f"{base} · ⚠ {freshness.message}")
            self._build_label.configure(foreground="#b00020")
        else:
            self.build_var.set(base)
            self._build_label.configure(foreground="")
        self.after(10_000, self.refresh_build_freshness)

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
