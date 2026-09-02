from __future__ import annotations

from agp_cockpit.core.browser_refresh import request_browser_refresh
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from agp_cockpit.core.hermes_config import DEFAULT_HERMES_CONFIG
from agp_cockpit.core.hermes_runtime import discover_hermes_runtime
from agp_cockpit.core.hermes_writer import update_hermes_model
from agp_cockpit.core.live_startup import execute_live_guarded_startup
from agp_cockpit.core.startup import StartupAction, decide_startup
from agp_cockpit.core.startup_probe import observe_live_read_only
from agp_cockpit.ui.hermes_status import format_hermes_status
from agp_cockpit.ui.work_order_panel import WorkOrderPanel
from agp_cockpit.ui.browser_transport_panel import BrowserTransportPanel


class MainWindow(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=10)
        self.grid(sticky="nsew")

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.status_var = tk.StringVar(
            value="Lokale Laufzeit wird geprüft …"
        )
        self.ollama_var = tk.StringVar(value="")
        self.hermes_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="")

        self._build()
        self.after(80, self.refresh_runtime_status)

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
            text="AGP Cockpit",
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

        ttk.Separator(
            self,
            orient="horizontal",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )

        self.tabs = ttk.Notebook(self)

        # AGP_BROWSER_REFRESH_BUTTON_062
        try:
            _agp_refresh_parent = self.tabs.winfo_toplevel()
            _agp_browser_refresh_button = tk.Button(
                _agp_refresh_parent,
                text="Browser-Verbindung neu laden",
                command=lambda: request_browser_refresh(
                    Path.cwd(),
                    reason="cockpit-button",
                ),
            )
            _agp_browser_refresh_button.place(relx=0.985, rely=0.985, anchor="se")
        except Exception:
            pass
        self.tabs.grid(
            row=2,
            column=0,
            sticky="nsew",
        )

        system_tab = ttk.Frame(
            self.tabs,
            padding=8,
        )
        system_tab.columnconfigure(0, weight=1)
        system_tab.columnconfigure(1, weight=1)
        system_tab.rowconfigure(1, weight=1)

        order_tab = ttk.Frame(
            self.tabs,
            padding=4,
        )
        order_tab.columnconfigure(0, weight=1)
        order_tab.rowconfigure(0, weight=1)

        self.tabs.add(
            system_tab,
            text="System",
        )
        self.tabs.add(
            order_tab,
            text="Auftrag",
        )

        self._build_system_tab(system_tab)

        self.work_order_panel = WorkOrderPanel(
            order_tab,
            repository_root=Path.cwd(),
        )
        self.work_order_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.browser_transport_panel = BrowserTransportPanel(
            order_tab,
            get_result_text=self.work_order_panel.get_result_for_copy,
            set_work_order_text=self.work_order_panel.set_work_order_text,
        )
        self.browser_transport_panel.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(6, 0),
        )

    def _build_system_tab(self, parent: ttk.Frame) -> None:
        ollama = ttk.LabelFrame(
            parent,
            text="Ollama",
            padding=8,
        )
        ollama.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 4),
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

        ttk.Button(
            ollama_buttons,
            text="Aktualisieren",
            command=self.refresh_runtime_status,
        ).grid(
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
            row=0,
            column=1,
            sticky="nsew",
            padx=(4, 0),
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
            row=1,
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

        except Exception as exc:
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
        except Exception as exc:
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
        except Exception as exc:
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
