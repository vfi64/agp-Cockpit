from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from agp_cockpit.core.operator_api import OperatorAPI


class MissionOperatorWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        *,
        repository_root: Path,
    ) -> None:
        super().__init__(master)
        self.title("AGP Cockpit – Mission Operator")
        self.geometry("760x520")
        self.minsize(680, 460)

        self.api = OperatorAPI(repository_root)

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(6, weight=1)

        ttk.Label(root, text="Titel").grid(
            row=0, column=0, sticky="w"
        )
        self.title_var = tk.StringVar()
        ttk.Entry(
            root,
            textvariable=self.title_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
        )

        ttk.Label(root, text="Execution").grid(
            row=1, column=0, sticky="w"
        )
        self.execution_var = tk.StringVar(
            value="DRY_RUN"
        )
        ttk.Combobox(
            root,
            textvariable=self.execution_var,
            values=("DRY_RUN", "LIVE"),
            state="readonly",
        ).grid(
            row=1,
            column=1,
            sticky="ew",
        )

        ttk.Label(root, text="Run mode").grid(
            row=2, column=0, sticky="w"
        )
        self.run_var = tk.StringVar(
            value="SINGLE_STEP"
        )
        ttk.Combobox(
            root,
            textvariable=self.run_var,
            values=("SINGLE_STEP", "FULL_AUTO"),
            state="readonly",
        ).grid(
            row=2,
            column=1,
            sticky="ew",
        )

        ttk.Label(root, text="Mission").grid(
            row=3, column=0, sticky="nw"
        )
        self.mission_text = tk.Text(
            root,
            height=8,
            wrap="word",
        )
        self.mission_text.grid(
            row=3,
            column=1,
            sticky="nsew",
        )

        buttons = ttk.Frame(root)
        buttons.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 8),
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
            text="Status aktualisieren",
            command=self.refresh,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Label(root, text="Status").grid(
            row=5, column=0, sticky="nw"
        )
        self.status_text = tk.Text(
            root,
            height=10,
            wrap="word",
            state="disabled",
        )
        self.status_text.grid(
            row=5,
            column=1,
            sticky="nsew",
        )

        self.refresh()

    def _show(self, text: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        self.status_text.configure(state="disabled")

    def create_mission(self) -> None:
        try:
            result = self.api.create(
                title=self.title_var.get(),
                mission_text=self.mission_text.get(
                    "1.0",
                    "end",
                ).strip(),
                execution_mode=self.execution_var.get(),
                run_mode=self.run_var.get(),
            )
            self._show(str(result))
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces mission failures.
            messagebox.showerror(
                "Mission",
                str(exc),
                parent=self,
            )

    def resume(self) -> None:
        try:
            result = self.api.resume_next_step()
            self._show(str(result))
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces resume failures.
            messagebox.showerror(
                "Next Step",
                str(exc),
                parent=self,
            )

    def refresh(self) -> None:
        self._show(str(self.api.status()))
