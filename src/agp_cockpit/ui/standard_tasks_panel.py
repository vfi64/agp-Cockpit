from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from agp_cockpit.core.chrome_automation import require_allowed_active_chat
from agp_cockpit.core.mission_http_client import create_live_full_auto
from agp_cockpit.core.standard_tasks import StandardTask, standard_tasks
from agp_cockpit.core.start_request_client import request_task_start
from agp_cockpit.core.task_operator_api import TaskOperatorAPI


class StandardTasksPanel(ttk.Frame):
    """Button surface for deterministic, reusable Cockpit task templates."""

    def __init__(self, master: tk.Misc, *, repository_root: Path, local_contract=None) -> None:
        super().__init__(master, padding=16)
        self.repository_root = repository_root.expanduser().resolve()
        self.api = TaskOperatorAPI(self.repository_root, local_contract=local_contract)
        self.tasks = standard_tasks()
        self.status_var = tk.StringVar(value="Standard Tasks bereit.")
        self.detail_var = tk.StringVar(value="Wähle einen standardisierten Auftrag.")

        self.columnconfigure(0, weight=1)
        ttk.Label(self, text="Standard Tasks", font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            self,
            text="Wiederkehrende, geprüfte Arbeitsaufträge mit derselben Task-/File-Loop-Autorität.",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 16))

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, sticky="w")
        for column, task in enumerate(self.tasks):
            button = ttk.Button(
                buttons,
                text=task.label,
                command=lambda selected=task: self.start_standard_task(selected),
            )
            button.grid(row=0, column=column, padx=(0 if column == 0 else 8, 0))

        ttk.Label(self, textvariable=self.detail_var, wraplength=760, justify="left").grid(
            row=3, column=0, sticky="ew", pady=(16, 4)
        )
        ttk.Label(self, textvariable=self.status_var, wraplength=760, justify="left").grid(
            row=4, column=0, sticky="ew"
        )

    def start_standard_task(self, task: StandardTask) -> None:
        contract = task.contract(self.repository_root)
        self.detail_var.set(task.description)
        required_tools = {"git", "agentic-kit"}
        missing_tools = sorted(required_tools - set(self.api.local_contract.allowed_tools))
        if missing_tools:
            self.status_var.set(
                "BLOCKED — lokale Authority fehlt: "
                + ", ".join(missing_tools)
                + ". Für diesen Standard Task müssen die Tools ausdrücklich freigegeben sein."
            )
            return
        try:
            prepared = self.api.prepare_task_contract(contract)
            status = self.api.start_task_from_contract(prepared)
            conversation_url = require_allowed_active_chat().url
            mission = create_live_full_auto(
                title=f"Standard · {task.label}",
                mission_text=task.prompt(self.repository_root),
                conversation_url=conversation_url,
            )["mission"]
            request_task_start(
                str(mission["mission_id"]),
                task_id=str(prepared["task_id"]),
            )
        except Exception as exc:  # noqa: BLE001 - UI boundary must surface all launch failures
            self.status_var.set(f"BLOCKED — Standard Task konnte nicht gestartet werden: {exc}")
            return

        self.status_var.set(
            "Gestartet — das Cockpit wartet auf die erste Remote-Antwort. "
            f"Lokaler Zustand: {json.dumps(status.get('state', ''), ensure_ascii=False)}"
        )
