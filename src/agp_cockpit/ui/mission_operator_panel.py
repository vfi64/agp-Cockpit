from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from agp_cockpit.core.operator_api import OperatorAPI


class MissionOperatorPanel(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        repository_root: Path,
    ) -> None:
        super().__init__(master, padding=10)
        self.repository_root = repository_root.resolve()
        self.api = OperatorAPI(self.repository_root)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(
            top,
            text="Mission Operator",
            font=("TkDefaultFont", 13, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.state_var = tk.StringVar(value="IDLE")
        ttk.Label(
            top,
            textvariable=self.state_var,
        ).grid(row=0, column=1, sticky="e")

        controls = ttk.LabelFrame(
            self,
            text="Mission",
            padding=8,
        )
        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 8),
        )
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Titel").grid(
            row=0, column=0, sticky="w"
        )
        self.title_var = tk.StringVar()
        ttk.Entry(
            controls,
            textvariable=self.title_var,
        ).grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(8, 0),
        )

        ttk.Label(
            controls,
            text="Execution",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(6, 0),
        )
        self.execution_var = tk.StringVar(
            value="DRY_RUN"
        )
        ttk.Combobox(
            controls,
            textvariable=self.execution_var,
            values=("DRY_RUN", "LIVE"),
            state="readonly",
            width=14,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 8),
            pady=(6, 0),
        )

        ttk.Label(
            controls,
            text="Run mode",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            pady=(6, 0),
        )
        self.run_var = tk.StringVar(
            value="SINGLE_STEP"
        )
        ttk.Combobox(
            controls,
            textvariable=self.run_var,
            values=("SINGLE_STEP", "FULL_AUTO"),
            state="readonly",
            width=14,
        ).grid(
            row=1,
            column=3,
            sticky="w",
            pady=(6, 0),
        )

        ttk.Label(
            controls,
            text="Auftrag",
        ).grid(
            row=2,
            column=0,
            sticky="nw",
            pady=(6, 0),
        )
        self.mission_text = tk.Text(
            controls,
            height=5,
            wrap="word",
        )
        self.mission_text.grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="nsew",
            padx=(8, 0),
            pady=(6, 0),
        )

        buttons = ttk.Frame(controls)
        buttons.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Mission anlegen",
            command=self.create_mission,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Next Step freigeben",
            command=self.resume,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Status",
            command=self.refresh,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        dashboard = ttk.Frame(self)
        dashboard.grid(
            row=2,
            column=0,
            sticky="nsew",
        )
        dashboard.columnconfigure(0, weight=1)
        dashboard.columnconfigure(1, weight=1)
        dashboard.rowconfigure(1, weight=1)

        self.summary_var = tk.StringVar(
            value="Keine aktive Mission."
        )
        summary = ttk.LabelFrame(
            dashboard,
            text="Status & Fortschritt",
            padding=8,
        )
        summary.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 4),
        )
        ttk.Label(
            summary,
            textvariable=self.summary_var,
            justify="left",
        ).pack(anchor="w")

        self.bridge_var = tk.StringVar(
            value="Bridge: localhost"
        )
        bridge = ttk.LabelFrame(
            dashboard,
            text="Bridge",
            padding=8,
        )
        bridge.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(4, 0),
        )
        ttk.Label(
            bridge,
            textvariable=self.bridge_var,
            justify="left",
        ).pack(anchor="w")

        result_box = ttk.LabelFrame(
            dashboard,
            text="Letztes Ergebnis / Kit-Report",
            padding=8,
        )
        result_box.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(8, 0),
        )
        result_box.rowconfigure(0, weight=1)
        result_box.columnconfigure(0, weight=1)

        self.result_text = tk.Text(
            result_box,
            wrap="word",
            height=10,
            state="disabled",
        )
        self.result_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.refresh()

    def _set_result(self, value: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert(
            "1.0",
            value or "Noch kein Ergebnis.",
        )
        self.result_text.configure(state="disabled")

    def create_mission(self) -> None:
        try:
            result = self.api.create(
                title=self.title_var.get().strip()
                or "AGP Cockpit Mission",
                mission_text=self.mission_text.get(
                    "1.0",
                    "end",
                ).strip(),
                execution_mode=self.execution_var.get(),
                run_mode=self.run_var.get(),
            )
            self.refresh()
        except Exception as exc:
            messagebox.showerror(
                "Mission",
                str(exc),
                parent=self.winfo_toplevel(),
            )

    def resume(self) -> None:
        try:
            self.api.resume_next_step()
            self.refresh()
        except Exception as exc:
            messagebox.showerror(
                "Next Step",
                str(exc),
                parent=self.winfo_toplevel(),
            )

    def refresh(self) -> None:
        status = self.api.status()
        mission = status.get("mission")
        state = status.get("state", "IDLE")
        self.state_var.set(state)

        if mission is None:
            self.summary_var.set(
                "Zustand: IDLE\n"
                "Mission: —\n"
                "Modus: —\n"
                "Turns: 0\n"
                "Steps: 0"
            )
            self.bridge_var.set(
                "Status: lokal\n"
                "Host: 127.0.0.1\n"
                "Port: 8765"
            )
            self._set_result("")
            return

        self.execution_var.set(
            mission.get(
                "execution_mode",
                "DRY_RUN",
            )
        )
        self.run_var.set(
            mission.get(
                "run_mode",
                "SINGLE_STEP",
            )
        )

        self.summary_var.set(
            f"Zustand: {mission.get('state', state)}\n"
            f"Mission: {mission.get('title', '')}\n"
            f"Modus: {mission.get('execution_mode', '')}"
            f" / {mission.get('run_mode', '')}\n"
            f"Turns: {mission.get('turn_count', 0)}\n"
            f"Steps: {mission.get('step_count', 0)}"
        )

        self.bridge_var.set(
            "Status: lokal\n"
            "Host: 127.0.0.1\n"
            "Port: 8765\n"
            f"Repository: {self.repository_root.name}"
        )

        result = mission.get("last_result", "")
        error = mission.get("last_error", "")
        text = result
        if error:
            text += (
                ("\n\n" if text else "")
                + "FEHLER:\n"
                + error
            )
        self._set_result(text)
