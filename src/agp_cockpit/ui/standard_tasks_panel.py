from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

from agp_cockpit.core.chrome_automation import require_allowed_active_chat
from agp_cockpit.core.mission_http_client import create_live_full_auto
from agp_cockpit.core.mission_http_client import status as bridge_status
from agp_cockpit.core.repo_state import ARBEITEN, LAEUFT
from agp_cockpit.core.standard_task_progress import describe_standard_task_progress
from agp_cockpit.core.standard_tasks import StandardTask, standard_tasks
from agp_cockpit.core.start_request_client import request_task_start
from agp_cockpit.core.task_operator_api import TaskOperatorAPI
from agp_cockpit.core.verbs import BY_KEY as VERB_BY_KEY
from agp_cockpit.core.verbs import VERBS, Verb, availability
from agp_cockpit.ui.tooltip import Tooltip

STEP_MARK = {1: "①", 2: "②", 3: "③", 4: "④"}


class StandardTasksPanel(ttk.Frame):
    """Button surface for deterministic, reusable Cockpit task templates."""

    def __init__(self, master: tk.Misc, *, repository_root: Path, local_contract=None,
                 on_open_work=None) -> None:
        super().__init__(master, padding=16)
        self.on_open_work = on_open_work
        self.repository_root = repository_root.expanduser().resolve()
        self.api = TaskOperatorAPI(self.repository_root, local_contract=local_contract)
        self.tasks = standard_tasks()
        # The hint line follows the repository state; the status line belongs to
        # the task this panel started (live 2026-10-01: "bereit" while a task ran).
        self.status_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="Lagebericht wird erstellt …")
        # AGP_STANDARD_TASK_PROGRESS_V1: status line follows the started
        # mission and durable task instead of the one-shot start message.
        self._tracked_mission_id = ""
        self._poll_job: str | None = None

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

        # AGP_REPO_STATE_V1 (plan P2): Lagebericht of the active repository.
        lage = ttk.LabelFrame(self, text="Lage", padding=10)
        lage.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        lage.columnconfigure(0, weight=1)
        self.lage_var = tk.StringVar(value="Lagebericht wird erstellt …")
        ttk.Label(lage, textvariable=self.lage_var, wraplength=700, justify="left").grid(
            row=0, column=0, sticky="ew"
        )
        self.lage_button = ttk.Button(lage, text="Aktualisieren", command=self.refresh_lage)
        self.lage_button.grid(row=0, column=1, sticky="ne", padx=(12, 0))
        self.repo_state = None
        self._lage_result: list = []
        self.after(300, self.refresh_lage)

        # AGP_STANDARD_TASK_VERBS_V1 (plan P3): lifecycle verbs grouped as a
        # numbered main path, problems and rarely used tasks; only verbs valid
        # in the current repository state are enabled, one is recommended.
        self.tasks_by_key = {task.key: task for task in self.tasks}
        self.verb_buttons: dict[str, ttk.Button] = {}
        self.verb_badges: dict[str, ttk.Label] = {}
        self.verb_reasons: dict[str, str] = {}
        style = ttk.Style(self)
        # Same size as every other button; the star sits in the badge line below,
        # a star glyph inside the button made it taller on macOS (live 2026-10-01).
        bold = tkfont.nametofont("TkDefaultFont").copy()
        bold.configure(weight="bold")
        self._recommended_font = bold
        style.configure("Recommended.TButton", font=bold)
        sections = ttk.Frame(self)
        sections.grid(row=3, column=0, sticky="ew")
        heading = ("TkDefaultFont", 12, "bold")
        ttk.Label(sections, text="Arbeitsweg", font=heading).grid(row=0, column=0, sticky="w")
        path = ttk.Frame(sections)
        path.grid(row=1, column=0, sticky="w", pady=(4, 12))
        column = 0
        for verb in sorted((v for v in VERBS if v.group == "weg"), key=lambda v: v.step or 0):
            if column:
                ttk.Label(path, text="→").grid(row=0, column=column, padx=6)
                column += 1
            self._verb_button(path, verb, column)
            column += 1
        ttk.Label(sections, text="Bei Problemen", font=heading).grid(row=2, column=0, sticky="w")
        problems = ttk.Frame(sections)
        problems.grid(row=3, column=0, sticky="w", pady=(4, 12))
        for index, verb in enumerate(v for v in VERBS if v.group == "probleme"):
            self._verb_button(problems, verb, index)
        self.more_button = ttk.Button(sections, text="Weitere anzeigen", command=self.toggle_more)
        self.more_button.grid(row=4, column=0, sticky="w")
        self.more_frame = ttk.Frame(sections)
        for index, verb in enumerate(v for v in VERBS if v.group == "weitere"):
            self._verb_button(self.more_frame, verb, index)
        self.apply_state(None)

        ttk.Label(self, textvariable=self.detail_var, wraplength=760, justify="left").grid(
            row=4, column=0, sticky="ew", pady=(16, 4)
        )
        ttk.Label(self, textvariable=self.status_var, wraplength=760, justify="left").grid(
            row=5, column=0, sticky="ew"
        )

    def start_standard_task(self, task: StandardTask) -> None:
        contract = task.contract(self.repository_root)
        self.detail_var.set(task.description)
        # AGP_STALE_APP_GUARD_V1: never start a task on an outdated app.
        from agp_cockpit.core.build_freshness import start_block_reason
        blocked = start_block_reason(self.repository_root)
        if blocked:
            self.status_var.set(blocked)
            return
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
        self._track(str(mission["mission_id"]))
        self.refresh_lage()   # the started task makes the state LÄUFT

    def _verb_button(self, parent: ttk.Frame, verb: Verb, column: int) -> None:
        cell = ttk.Frame(parent)
        cell.grid(row=0, column=column, padx=(0, 8), sticky="n")
        button = ttk.Button(cell, text=self._verb_text(verb, False),
                            command=lambda selected=verb: self.run_verb(selected))
        button.grid(row=0, column=0, sticky="ew")
        badge = ttk.Label(cell, text=verb.badge, foreground="#888888", font=("TkDefaultFont", 10))
        badge.grid(row=1, column=0)
        self.verb_badges[verb.key] = badge
        self.verb_buttons[verb.key] = button
        Tooltip(button, lambda selected=verb: self._tooltip(selected))

    def _verb_text(self, verb: Verb, recommended: bool = False) -> str:
        mark = STEP_MARK.get(verb.step or 0, "")
        return (f"{mark} " if mark else "") + verb.label

    def _tooltip(self, verb: Verb) -> str:
        reason = self.verb_reasons.get(verb.key, "")
        return verb.tooltip() + (f"\n\n{reason}" if reason else "")

    def toggle_more(self) -> None:
        self.more_open = not getattr(self, "more_open", False)
        if self.more_open:
            self.more_frame.grid(row=5, column=0, sticky="w", pady=(4, 0))
            self.more_button.configure(text="Weitere ausblenden")
        else:
            self.more_frame.grid_remove()
            self.more_button.configure(text="Weitere anzeigen")

    def apply_state(self, state) -> None:
        """Enable exactly the verbs valid in ``state``; mark the recommended one."""
        self.repo_state = state
        recommended = getattr(state, "recommended", None)
        for key, button in self.verb_buttons.items():
            verb = VERB_BY_KEY[key]
            enabled, reason = availability(verb, state)
            self.verb_reasons[key] = reason
            is_recommended = enabled and key == recommended
            button.configure(state="normal" if enabled else "disabled",
                             text=self._verb_text(verb),
                             style="Recommended.TButton" if is_recommended else "TButton")
            self.verb_badges[key].configure(
                text=("★ empfohlen · " if is_recommended else "") + verb.badge,
                foreground="#d0a000" if is_recommended else "#888888",
            )
        self.detail_var.set(self._state_hint(state))
        if self._poll_job is None and getattr(state, "state", None) == LAEUFT:
            self.status_var.set("")   # a task started elsewhere; its progress is in "Arbeiten"

    @staticmethod
    def _state_hint(state) -> str:
        if state is None:
            return "Lagebericht wird erstellt …"
        if state.state == LAEUFT:
            return ("Ein Task läuft — neue Aufträge erst nach seinem Ende. "
                    "Den Fortschritt zeigt der Tab „Arbeiten“.")
        if state.recommended:
            verb = VERB_BY_KEY[state.recommended]
            enabled, _reason = availability(verb, state)
            if not enabled and verb.slice:
                # Live 2026-10-02: "Empfohlen: Abschließen" next to a disabled button.
                return (f"Nächster Schritt wäre „{verb.label}“ — die Schaltfläche folgt mit Plan "
                        f"{verb.slice}; bis dahin als Auftrag im Tab „Arbeiten“.")
            return f"Empfohlen: {verb.label}. Details im Tooltip der Schaltfläche."
        return "Gerade ist kein Auftrag empfohlen — siehe Lage."

    def run_verb(self, verb: Verb) -> None:
        enabled, reason = availability(verb, self.repo_state)
        if not enabled:
            self.status_var.set(reason)
            return
        if verb.key == ARBEITEN:
            if self.on_open_work is not None:
                self.on_open_work()
            return
        task = self.tasks_by_key.get(verb.task_key or "")
        if task is not None:
            self.start_standard_task(task)

    def _task_running(self) -> bool:
        try:
            mission = (bridge_status() or {}).get("mission") or {}
        except Exception:  # noqa: BLE001 - an unreachable bridge runs no task
            return False
        return bool(mission) and str(mission.get("state") or "") not in {
            "", "IDLE", "DONE", "COMPLETED", "NEEDS_HUMAN", "BLOCKED", "FAILED", "ERROR",
            "STOPPED", "CANCELLED",
        }

    def refresh_lage(self) -> None:
        """Observe in a worker thread (network reads); the UI polls the result."""
        from agp_cockpit.core.repo_state import lagebericht
        if self._lage_result is None:
            return  # a run is in progress
        self.lage_button.configure(state="disabled")
        self.lage_var.set("Lagebericht wird erstellt …")
        running = self._task_running()
        holder: list = []
        self._lage_result = None

        def work() -> None:
            try:
                holder.append(lagebericht(self.repository_root, task_running=running))
            except Exception as exc:  # noqa: BLE001 - shown to the operator
                holder.append(exc)

        threading.Thread(target=work, daemon=True).start()
        self._poll_lage(holder)

    def _poll_lage(self, holder: list) -> None:
        if not holder:
            self.after(200, self._poll_lage, holder)
            return
        from agp_cockpit.core.repo_state import describe
        result = holder[0]
        self._lage_result = holder
        self.lage_button.configure(state="normal")
        if isinstance(result, Exception):
            self.lage_var.set(f"Lagebericht fehlgeschlagen: {result}")
            return
        self.repo_state = result
        self.lage_var.set(describe(result))
        self.apply_state(result)

    def _track(self, mission_id: str) -> None:
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        self._tracked_mission_id = mission_id
        self._poll_job = self.after(2000, self.refresh_progress)

    def refresh_progress(self) -> None:
        self._poll_job = None
        mission_id = self._tracked_mission_id
        if not mission_id:
            return
        try:
            progress = describe_standard_task_progress(
                mission_id=mission_id,
                task_status=self.api.status(),
                bridge_status=bridge_status(),
            )
        except Exception as exc:  # noqa: BLE001 - polling survives transient bridge/DB errors.
            self.status_var.set(f"Status momentan nicht verfügbar ({exc}) — neuer Versuch läuft.")
            self._poll_job = self.after(3000, self.refresh_progress)
            return
        self.status_var.set(progress.text)
        if not progress.terminal:
            self._poll_job = self.after(2000, self.refresh_progress)
        else:
            self.refresh_lage()   # the finished task changed the repository state
