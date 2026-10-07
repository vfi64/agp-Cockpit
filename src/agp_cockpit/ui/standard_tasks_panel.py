from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

from agp_cockpit.core.ampel import ampel as derive_ampel
from agp_cockpit.core.chrome_automation import require_allowed_active_chat
from agp_cockpit.core.conversation_binding import ConversationBindingStore
from agp_cockpit.core.mission_http_client import create_live_full_auto, record_decision
from agp_cockpit.core.mission_http_client import status as bridge_status
from agp_cockpit.core.repo_state import ARBEITEN, BEREIT, LAEUFT, WIEDERHERSTELLEN
from agp_cockpit.core.standard_task_progress import (
    clip,
    describe_standard_task_progress,
    late_completion_verdict,
    stopped_by_assistant_timeout,
)
from agp_cockpit.core.standard_tasks import StandardTask, standard_tasks
from agp_cockpit.core.start_request_client import request_task_start
from agp_cockpit.core.task_operator_api import TaskOperatorAPI
from agp_cockpit.core.verbs import BY_KEY as VERB_BY_KEY
from agp_cockpit.core.verbs import VERBS, Verb, availability, recover_not_needed
from agp_cockpit.ui.flow_row import FlowRow
from agp_cockpit.ui.scrollable import follow_viewport
from agp_cockpit.ui.tooltip import Tooltip

LAGE_POLL_MS = 4000  # AGP_LAGE_AUTO_REFRESH_V1

STEP_MARK = {1: "①", 2: "②", 3: "③", 4: "④"}


def rs_labels() -> dict:
    from agp_cockpit.core.repo_state import LABELS
    return LABELS


class StandardTasksPanel(ttk.Frame):
    """Button surface for deterministic, reusable Cockpit task templates."""

    def __init__(self, master: tk.Misc, *, repository_root: Path, local_contract=None,
                 on_open_work=None, ask_inputs=None, confirm=None, runtime_root: Path | None = None) -> None:
        super().__init__(master, padding=10)
        self.on_open_work = on_open_work
        # AGP_STANDARD_TASK_FRAMEWORK_V1: dialogs are injectable for tests.
        self.ask_inputs = ask_inputs or self._ask_inputs
        self.confirm = confirm or self._confirm
        self._runtime_root = runtime_root
        self._tracked_task: StandardTask | None = None
        self._tracked_task_id = ""
        self._tracked_inputs: dict | None = None
        self.recover_offered = False
        self._tracked_head = ""
        self._late_check = False
        self.follow_up_key: str | None = None   # verb recommended after a finished task
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
        # AGP_AMPEL_TASK_ACTIVE_V1 (live 2026-10-06, release 0.2.1): the Lage is built once right
        # after the start or the approval, when the bridge may still report the previous mission
        # at rest (here the answered NEEDS_HUMAN); it said „Grün — bereit für neue Arbeit“ and
        # recommended „Arbeit beginnen“ for the whole phase 2. The task this panel tracks counts
        # as running until its progress is terminal.
        self._task_active = False
        self.external_task_active = None   # AGP_LAGE_ALL_TABS_V1: set by the main window
        # AGP_MANUAL_GITHUB_RELEASE_HINT_V1: the owner's own command after a release.
        self._followup_command = ""

        self.columnconfigure(0, weight=1)
        # AGP_COMPACT_LAGE_V1 (owner 2026-10-06: „der Bildschirmplatz ist endlich“, Chrome
        # must stay visible beside the Cockpit): no tab title (the tab names itself), the
        # Lagebericht collapses to one line, a pending decision sits right under the Lage,
        # and the texts wrap to the window width instead of fixed pixels.
        self._wrapping: list[ttk.Label] = []

        # AGP_REPO_STATE_V1 (plan P2): Lagebericht of the active repository.
        lage = ttk.LabelFrame(self, text="Lage", padding=8)
        lage.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        lage.columnconfigure(0, weight=1)
        self.lage_var = tk.StringVar(value="Lagebericht wird erstellt …")
        # AGP_AMPEL_V1 (owner 2026-10-05): one light for the whole repository, with a word.
        self._last_outcome = ""
        self._status_detail = ""
        self.ampel_state = None
        light = ttk.Frame(lage)
        light.grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.ampel_dot = ttk.Label(light, text="●", font=("TkDefaultFont", 22), foreground="#888888")
        self.ampel_dot.grid(row=0, column=0, sticky="w")
        self.ampel_var = tk.StringVar(value="Grau — Lage wird geprüft")
        self._wrap(ttk.Label(light, textvariable=self.ampel_var, font=("TkDefaultFont", 13, "bold"),
                             justify="left"), 180).grid(row=0, column=1, sticky="w", padx=(8, 0))
        # AGP_GUIDED_RECOVERY_V1: the numbered way out, derived by core/guidance.py.
        self.guidance_var = tk.StringVar(value="")
        self.guidance_label = self._wrap(ttk.Label(lage, textvariable=self.guidance_var, justify="left"), 60)
        self.guidance_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.guidance_label.grid_remove()
        facts = ttk.Frame(lage)
        facts.grid(row=2, column=0, columnspan=2, sticky="ew")
        facts.columnconfigure(0, weight=1)
        self.facts_var = tk.StringVar(value="")
        self._wrap(ttk.Label(facts, textvariable=self.facts_var, foreground="#888888", justify="left"),
                   170).grid(row=0, column=0, sticky="w")
        self.details_open = False
        self.details_button = ttk.Button(facts, text="Details ▸", command=self.toggle_details)
        self.details_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.lage_label = self._wrap(ttk.Label(lage, textvariable=self.lage_var, justify="left"), 60)
        self.lage_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.lage_label.grid_remove()
        self.lage_button = ttk.Button(lage, text="Aktualisieren", command=self.refresh_lage)
        self.lage_button.grid(row=0, column=1, sticky="ne", padx=(12, 0))
        self.repo_state = None
        self._lage_result: list = []
        self.after(300, self.refresh_lage)
        # AGP_LAGE_AUTO_REFRESH_V1: rebuild the Lage when HEAD, the index or the
        # installed Kit change outside the Cockpit (cheap local poll, no network).
        self._lage_fingerprint = None
        self.after(LAGE_POLL_MS, self._watch_lage)

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
        # AGP_VIEWPORT_WRAP_V1 (live 2026-10-07): the verb rows wrap with the window.
        sections = ttk.Frame(self)
        sections.grid(row=2, column=0, sticky="ew")
        sections.columnconfigure(0, weight=1)
        heading = ("TkDefaultFont", 12, "bold")
        ttk.Label(sections, text="Arbeitsweg", font=heading).grid(row=0, column=0, sticky="w")
        path = FlowRow(sections)
        path.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        self.path_row = path
        first = True
        for verb in sorted((v for v in VERBS if v.group == "weg"), key=lambda v: v.step or 0):
            # the arrow belongs to the step it points to: a wrapped row never ends with „→“
            self._verb_button(path, verb, 0, arrow=not first)
            first = False
        # „Bei Problemen“ and „Weitere“ share one row (AGP_COMPACT_LAGE_V1).
        problems = FlowRow(sections)
        problems.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        self.problems_row = problems
        problems.add(ttk.Label(problems, text="Bei Problemen", font=heading))
        for verb in (v for v in VERBS if v.group == "probleme"):
            self._verb_button(problems, verb, 0)
        self.more_button = problems.add(ttk.Button(problems, text="Weitere anzeigen", command=self.toggle_more))
        self.more_frame = FlowRow(sections)
        for index, verb in enumerate(v for v in VERBS if v.group == "weitere"):
            self._verb_button(self.more_frame, verb, index)
        self.apply_state(None)

        # detail_var (the recommendation sentence) is kept for the tooltip and tests; the
        # Lösungsweg in the Lage replaces it on screen (AGP_COMPACT_LAGE_V1).
        status_label = self._wrap(ttk.Label(self, textvariable=self.status_var, justify="left"), 30)
        status_label.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self.bind("<Configure>", self._rewrap, add="+")
        self._viewport_width = 0
        follow_viewport(self, self._follow_viewport)
        # AGP_SHORT_RESULT_LINE_V1: the remote side's own report is in the tooltip.
        Tooltip(status_label, lambda: ("Meldung der Remote-Seite:\n" + clip(self._status_detail, 600))
                if self._status_detail else "")
        self.copy_command_button = ttk.Button(self, text="GitHub-Befehl kopieren",
                                              command=self.copy_followup_command)
        self.copy_command_button.grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.copy_command_button.grid_remove()

        # AGP_STANDARD_TASK_DECISION_V1 (P8 live test 2026-10-03): a standard
        # task that stops with NEEDS_HUMAN (e.g. Wiederherstellen before the
        # signed rescue) is answered here and continues in the same chat.
        self._decision_mission_id = ""
        self._decision_question = ""
        self.decision_frame = ttk.LabelFrame(self, text="Deine Entscheidung ist gefragt", padding=8)
        self.decision_frame.columnconfigure(0, weight=1)
        self.decision_question_var = tk.StringVar(value="")
        self._wrap(ttk.Label(self.decision_frame, textvariable=self.decision_question_var, justify="left"),
                   60).grid(row=0, column=0, columnspan=3, sticky="ew")
        ttk.Label(self.decision_frame, text="Antwort / Hinweis (optional):").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self.decision_note = tk.Text(self.decision_frame, height=2, width=40, wrap="word", undo=True)
        self.decision_note.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.approve_decision_button = ttk.Button(
            self.decision_frame, text="Freigeben", command=lambda: self.decide("APPROVE"))
        self.approve_decision_button.grid(row=3, column=1, sticky="e", pady=(8, 0), padx=(0, 8))
        self.reject_decision_button = ttk.Button(
            self.decision_frame, text="Ablehnen", command=lambda: self.decide("REJECT"))
        self.reject_decision_button.grid(row=3, column=2, sticky="e", pady=(8, 0))
        self.decision_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.decision_frame.grid_remove()
        self.after(600, self.adopt_pending_decision)

    def _follow_viewport(self, width: int) -> None:
        self._viewport_width = width
        self._rewrap()

    def _wrap(self, label: ttk.Label, margin: int) -> ttk.Label:
        """AGP_COMPACT_LAGE_V1: wrap at the panel width minus ``margin`` pixels."""
        label._agp_margin = margin
        label.configure(wraplength=max(240, 760 - margin))
        self._wrapping.append(label)
        return label

    def _rewrap(self, event=None) -> None:
        width = getattr(event, "width", 0) or self.winfo_width()
        if self._viewport_width > 1:
            width = self._viewport_width   # AGP_VIEWPORT_WRAP_V1: the visible width decides
        if width <= 1:
            return
        for label in self._wrapping:
            label.configure(wraplength=max(240, width - 40 - label._agp_margin))

    def toggle_details(self) -> None:
        self.details_open = not self.details_open
        if self.details_open:
            self.lage_label.grid()
            self.details_button.configure(text="Details ▾")
        else:
            self.lage_label.grid_remove()
            self.details_button.configure(text="Details ▸")

    def update_guidance(self) -> None:
        """AGP_GUIDED_RECOVERY_V1: the Lösungsweg follows every change of the light."""
        from agp_cockpit.core import guidance
        from agp_cockpit.core.build_freshness import stale_block_reason
        try:
            blocked = stale_block_reason(self.repository_root, release_version=self._release_version())
        except Exception:  # noqa: BLE001 - guidance never breaks the panel
            blocked = ""
        items = guidance.steps(self.repo_state, block_reason=blocked,
                               decision_pending=bool(getattr(self, "_decision_mission_id", "")),
                               recover_offered=self.recover_offered, task_outcome=self._last_outcome,
                               repository=str(self.repository_root))
        self.guidance_var.set(("Lösungsweg:\n" + guidance.text(items)) if items else "")
        if items:
            self.guidance_label.grid()
        else:
            self.guidance_label.grid_remove()

    def runtime_root(self) -> Path:
        if self._runtime_root is None:
            from agp_cockpit.adapters.macos_settings import bridge_runtime_root
            self._runtime_root = bridge_runtime_root()
        return self._runtime_root

    def _ask_inputs(self, task: StandardTask) -> dict | None:
        check = lambda values: task.check(self.repository_root, values)
        if task.key == "release":
            from agp_cockpit.core.standard_tasks import (
                _current_version,
                release_resume_version,
            )
            from agp_cockpit.ui.release_dialog import ask_release_inputs
            return ask_release_inputs(self, current=_current_version(self.repository_root),
                                      resume=release_resume_version(self.repository_root), check=check)
        from agp_cockpit.ui.work_start_dialog import ask_work_inputs
        return ask_work_inputs(self, check=check)

    def _confirm(self, task: StandardTask) -> bool:
        from tkinter import messagebox
        return bool(messagebox.askokcancel(task.label, task.confirm, parent=self))

    def start_standard_task(self, task: StandardTask, inputs: dict | None = None) -> bool:
        """Start ``task``; True when the mission was created."""
        self.detail_var.set(task.description)
        # AGP_STALE_APP_GUARD_V1: never start a task on an outdated app.
        from agp_cockpit.core.build_freshness import start_block_reason
        blocked = start_block_reason(self.repository_root)
        if blocked:
            self.status_var.set(blocked)
            return False
        # R5: one task at a time per repository.
        if self._task_running():
            self.status_var.set("BLOCKED — es läuft bereits ein Task; neue Aufträge erst nach seinem Ende (R5).")
            return False
        reason = task.check(self.repository_root, inputs)
        if reason:
            self.status_var.set(f"BLOCKED — {task.label}: {reason}")
            return False
        required_tools = {"git", "agentic-kit"}
        missing_tools = sorted(required_tools - set(self.api.local_contract.allowed_tools))
        if missing_tools:
            self.status_var.set(
                "BLOCKED — lokale Authority fehlt: "
                + ", ".join(missing_tools)
                + ". Für diesen Standard Task müssen die Tools ausdrücklich freigegeben sein."
            )
            return False
        # AGP_CONVERSATION_BINDING_V1 (P4): one chat per repository, checked
        # before anything is prepared or approved.
        try:
            conversation_url = require_allowed_active_chat().url
        except Exception as exc:  # noqa: BLE001 - UI boundary must surface all launch failures
            self.status_var.set(f"BLOCKED — Standard Task konnte nicht gestartet werden: {exc}")
            return False
        bindings = ConversationBindingStore(self.runtime_root())
        bound_elsewhere = bindings.block_reason(conversation_url, self.repository_root)
        if bound_elsewhere:
            # AGP_CHAT_BINDING_HINT_V1 (live 2026-10-06): say what to do, not only what is wrong.
            self.status_var.set(f"BLOCKED — {bound_elsewhere}\nIn Chrome links „Neuer Chat“ (oder den Chat "
                                f"dieses Repos) öffnen, den Tab vorn lassen, dann „{task.label}“ erneut klicken.")
            return False
        contract = task.contract(self.repository_root, inputs)
        try:
            prepared = self.api.prepare_task_contract(contract)
            status = self.api.start_task_from_contract(prepared)
            task_id = str(prepared["task_id"])
            # AGP_START_CLICK_APPROVAL_V1 (R4): the start click approves exactly
            # the declared effects; AGP_CI_GREEN_COMPLETION_V1 from the start.
            scope = task.scope(self.repository_root, inputs)   # AGP_RELEASE_RESUME_SCOPE_V1
            if scope:
                from agp_cockpit.core.human_decision import HumanDecisionStore
                HumanDecisionStore(self.runtime_root()).pre_approve(
                    task_id=task_id, label=task.label, scope=scope)
            if task.ci_gate_merge:
                from agp_cockpit.core.ci_gate import CiGateStore
                CiGateStore(self.runtime_root()).activate(
                    task_id, reason=f"standard task {task.key}", merge=True)
            mission = create_live_full_auto(
                title=f"Standard · {task.label}",
                mission_text=task.prompt(self.repository_root, inputs),
                conversation_url=conversation_url,
            )["mission"]
            request_task_start(
                str(mission["mission_id"]),
                task_id=task_id,
            )
            bindings.bind(conversation_url, self.repository_root)
        except Exception as exc:  # noqa: BLE001 - UI boundary must surface all launch failures
            self.status_var.set(f"BLOCKED — Standard Task konnte nicht gestartet werden: {exc}")
            return False

        self.recover_offered = False
        self.follow_up_key = None
        self._tracked_task = task
        self._tracked_task_id = task_id
        self._tracked_inputs = inputs
        self._tracked_head = self._head_sha()   # AGP_LATE_COMPLETION_CHECK_V1
        self._late_check = False
        self._hide_decision()
        self.status_var.set(
            "Gestartet — das Cockpit wartet auf die erste Remote-Antwort. "
            f"Lokaler Zustand: {json.dumps(status.get('state', ''), ensure_ascii=False)}"
        )
        self._track(str(mission["mission_id"]))
        self.refresh_lage()   # the started task makes the state LÄUFT
        return True

    # --- AGP_STANDARD_TASK_DECISION_V1 ------------------------------------------------

    def adopt_pending_decision(self) -> None:
        """After a restart: re-attach a standard task that waits for a decision."""
        if self._tracked_mission_id:
            return
        try:
            mission = (bridge_status() or {}).get("mission") or {}
        except Exception:  # noqa: BLE001 - no bridge, nothing to adopt
            return
        task, mission_id = pending_standard_decision(mission, self.tasks)
        if task is None:
            return
        from agp_cockpit.core.start_request import resolve_task_binding
        task_id = str(resolve_task_binding(self.runtime_root(), mission_id).get("task_id") or "")
        if not task_id:
            return
        self._tracked_task, self._tracked_task_id, self._tracked_inputs = task, task_id, None
        self._tracked_mission_id = mission_id
        self._show_decision(mission_id, str(mission.get("last_summary") or ""))
        self.status_var.set(f"{task.label} wartet auf deine Entscheidung (nach einem Neustart übernommen).")

    def _release_version(self) -> str:
        """AGP_RELEASE_PHASE2_APPROVAL_V1: the version of a tracked release task."""
        task = self._tracked_task
        if task is None or task.key != "release":
            return ""
        from agp_cockpit.core.standard_tasks import release_resume_version
        return (str((self._tracked_inputs or {}).get("version") or "")
                or release_resume_version(self.repository_root))

    def update_ampel(self, *, lage_error: str = "") -> None:
        """AGP_AMPEL_V1: recompute the light from what this panel knows."""
        from agp_cockpit.core.build_freshness import stale_block_reason
        try:
            blocked = stale_block_reason(self.repository_root, release_version=self._release_version())
        except Exception:  # noqa: BLE001 - the light never breaks the panel
            blocked = ""
        light = derive_ampel(self.repo_state, block_reason=blocked, task_outcome=self._last_outcome,
                             decision_pending=bool(getattr(self, "_decision_mission_id", "")),
                             recover_offered=self.recover_offered, lage_error=lage_error)
        self.ampel_state = light
        self.ampel_var.set(light.text)
        self.ampel_dot.configure(foreground=light.hex)
        if self.repo_state is not None:
            from agp_cockpit.core.repo_state import summary_line
            self.facts_var.set(summary_line(self.repo_state))
        self.update_guidance()

    def _show_decision(self, mission_id: str, question: str) -> None:
        if self._decision_mission_id == mission_id:
            return
        self._decision_mission_id = mission_id
        self._decision_question = question
        self.decision_question_var.set(question or "Die Remote-Seite braucht eine Entscheidung.")
        self.decision_note.delete("1.0", "end")
        self.decision_frame.grid()
        self.update_ampel()
        self._scroll_to_top()   # AGP_COMPACT_LAGE_V1: the decision sits right under the Lage

    def _scroll_to_top(self) -> None:
        widget = self.master
        while widget is not None:
            if isinstance(widget, tk.Canvas):
                widget.yview_moveto(0)
                return
            widget = getattr(widget, "master", None)

    def _hide_decision(self) -> None:
        self._decision_mission_id = ""
        self._decision_question = ""
        self.decision_frame.grid_remove()
        self.update_ampel()

    def decide(self, decision: str) -> bool:
        """Answer the NEEDS_HUMAN question; the task continues in the same chat."""
        from agp_cockpit.core.build_freshness import start_block_reason
        from agp_cockpit.core.human_decision import decision_mission_text
        task, mission_id = self._tracked_task, self._decision_mission_id
        if task is None or not mission_id or not self._tracked_task_id:
            return False
        blocked = start_block_reason(self.repository_root, release_version=self._release_version())
        if blocked:   # AGP_STALE_APP_GUARD_V1 (AGP_RELEASE_PHASE2_APPROVAL_V1 for a release)
            self.status_var.set(blocked)
            return False
        note = self.decision_note.get("1.0", "end-1c").strip()
        if decision == "REJECT":
            return self._reject(task, mission_id, note)
        goal = (task.prompt(self.repository_root, self._tracked_inputs)
                if self._tracked_inputs is not None or not task.inputs else task.description)
        try:
            record_decision(mission_id=mission_id, decision=decision, note=note)
            # The NEEDS_HUMAN stop left a durable STOP; the continuation starts clean.
            self.api.operator_control.request("RESUME")
            mission = create_live_full_auto(
                title=f"Standard · {task.label} · Entscheidung",
                mission_text=decision_mission_text(goal_text=goal, decision=decision,
                                                   question=self._decision_question, note=note),
                conversation_url=require_allowed_active_chat().url,
            )["mission"]
            request_task_start(str(mission["mission_id"]), task_id=self._tracked_task_id)
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces decision failures
            self.status_var.set(f"Entscheidung nicht übermittelt — {exc}")
            return False
        self._hide_decision()
        self.recover_offered = False   # AGP_RECOVER_OFFER_CLEARS_V1: the task itself continues
        self.status_var.set(("Freigegeben" if decision == "APPROVE" else "Abgelehnt")
                            + f" — {task.label} läuft im selben Chat weiter.")
        self._track(str(mission["mission_id"]))
        self.refresh_lage()
        return True

    def _reject(self, task: StandardTask, mission_id: str, note: str) -> bool:
        """AGP_REJECT_ENDS_TASK_V1 (live 2026-10-04, steps 1679/1680): a rejection
        used to continue the task in the chat without the action; the remote side
        could only ask again (NEEDS_HUMAN 1680). Rejecting now ends the task here:
        the decision is recorded, no remote turn follows."""
        try:
            record_decision(mission_id=mission_id, decision="REJECT", note=note)
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces decision failures
            self.status_var.set(f"Entscheidung nicht übermittelt — {exc}")
            return False
        self._hide_decision()
        text = f"Abgelehnt — {task.label} ist beendet; es wurde nichts weiter ausgeführt."
        if task.offers_recover_on_interrupt and self._effects_executed():
            self.recover_offered = True   # R6: effects of this task already ran
            text += " Freigegebene Wirkungen liefen bereits — „Wiederherstellen“ ist freigeschaltet."
        else:
            self.recover_offered = False
            text += f" „{task.label}“ kann neu gestartet werden."
        effects = self.effects_text()
        self.status_var.set(text + (f"\n{effects}" if effects else ""))
        self.refresh_lage()
        return True

    def _head_sha(self) -> str:
        import subprocess
        try:
            done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.repository_root),
                                  text=True, capture_output=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return done.stdout.strip() if done.returncode == 0 else ""

    def _bind_active_chat(self) -> None:
        """A task started in a fresh chat gets its conversation id only after the
        first send; bind it at the verified end (AGP_CONVERSATION_BINDING_V1)."""
        try:
            url = require_allowed_active_chat().url
        except Exception:  # noqa: BLE001 - binding is best effort at this point
            return
        ConversationBindingStore(self.runtime_root()).bind(url, self.repository_root)

    def _effects_executed(self) -> bool:
        if not self._tracked_task_id:
            return False
        from agp_cockpit.core.human_decision import HumanDecisionStore
        return bool(HumanDecisionStore(self.runtime_root()).effects_log(self._tracked_task_id))

    def effects_text(self) -> str:
        """P6 acceptance: every auto-approved effect, visible in the UI."""
        task = self._tracked_task
        if task is None or not task.approved_scope or not self._tracked_task_id:
            return ""
        from agp_cockpit.core.human_decision import HumanDecisionStore
        log = HumanDecisionStore(self.runtime_root()).effects_log(self._tracked_task_id)
        if not log:
            return "Freigegebene Wirkungen (Start-Klick): noch keine ausgeführt."
        # AGP_EFFECTS_BY_APPROVAL_V1 (live 2026-10-06, release 0.2.1): the tag push approved in the
        # decision box was listed under „Start-Klick“.
        groups: dict[str, list[str]] = {}
        for entry in log:
            label = "Freigabe" if entry.get("source") == "decision" else "Start-Klick"
            groups.setdefault(label, []).append(
                f"Schritt {entry.get('step') or '?'}: "
                + ", ".join(c.replace("agentic-kit ", "") for c in entry.get("commands") or ()))
        return "Freigegebene Wirkungen " + "; ".join(
            f"({label}): {'; '.join(items)}" for label, items in groups.items()) + "."

    def _verb_button(self, parent: ttk.Frame, verb: Verb, column: int, *, arrow: bool = False) -> None:
        cell = ttk.Frame(parent)
        if isinstance(parent, FlowRow):
            parent.add(cell)
        else:
            cell.grid(row=0, column=column, padx=(0, 8), sticky="n")
        if arrow:
            ttk.Label(cell, text="→").grid(row=0, column=0, padx=(0, 8))
        button = ttk.Button(cell, text=self._verb_text(verb, False),
                            command=lambda selected=verb: self.run_verb(selected))
        button.grid(row=0, column=1, sticky="ew")
        badge = ttk.Label(cell, text=verb.badge, foreground="#888888", font=("TkDefaultFont", 10))
        badge.grid(row=1, column=1)
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
            self.more_frame.grid(row=4, column=0, sticky="ew", pady=(0, 4))
            self.more_button.configure(text="Weitere ausblenden")
        else:
            self.more_frame.grid_remove()
            self.more_button.configure(text="Weitere anzeigen")

    def apply_state(self, state) -> None:
        """Enable exactly the verbs valid in ``state``; mark the recommended one."""
        self.repo_state = state
        recommended = getattr(state, "recommended", None)
        if self.recover_offered and getattr(state, "state", None) == BEREIT:
            # AGP_RECOVER_OFFER_CLEARS_V1 (live 2026-10-03): once main is clean and
            # synchronized there is nothing left to recover.
            self.recover_offered = False
        if self.recover_offered and recover_not_needed(state):
            # AGP_RECOVER_OFFER_EXPIRES_V1 (owner 2026-10-07, PR #272): the interrupted
            # Abschließen left a clean work branch with its commits; nothing is half done,
            # „Abschließen“ simply continues — the light need not stay red.
            self.recover_offered = False
        if self.recover_offered and getattr(state, "state", None) != LAEUFT:
            recommended = WIEDERHERSTELLEN   # R6: interrupted Abschließen
        elif self.follow_up_key and getattr(state, "state", None) != LAEUFT \
                and self.follow_up_key in getattr(state, "offered", ()):
            # One recommendation only (live 2026-10-02: the status line said
            # „Chat wechseln“, the star sat on „Arbeit beginnen“).
            recommended = self.follow_up_key
        for key, button in self.verb_buttons.items():
            verb = VERB_BY_KEY[key]
            enabled, reason = availability(verb, state, recover_offered=self.recover_offered)
            self.verb_reasons[key] = reason
            is_recommended = enabled and key == recommended
            button.configure(state="normal" if enabled else "disabled",
                             text=self._verb_text(verb),
                             style="Recommended.TButton" if is_recommended else "TButton")
            self.verb_badges[key].configure(
                text=("★ empfohlen · " if is_recommended else "") + verb.badge,
                foreground="#d0a000" if is_recommended else "#888888",
            )
        self.detail_var.set(self._state_hint(state, recommended))
        self._effective_recommended = recommended
        if hasattr(self, "ampel_var"):
            self.update_ampel()
        if self._poll_job is None and getattr(state, "state", None) == LAEUFT:
            self.status_var.set("")   # a task started elsewhere; its progress is in "Arbeiten"

    @staticmethod
    def _state_hint(state, recommended: str | None = None) -> str:
        if state is None:
            return "Lagebericht wird erstellt …"
        if state.state == LAEUFT:
            return ("Ein Task läuft — neue Aufträge erst nach seinem Ende. "
                    "Den Fortschritt zeigt der Tab „Arbeiten“.")
        recommended = recommended or state.recommended
        if recommended and recommended not in VERB_BY_KEY:
            # AGP_UNKLAR_HINT_V1 (found 2026-10-05 while rendering the Ampel preview): UNKLAR
            # recommends the Lagebericht, which is no button; the KeyError aborted apply_state
            # and the Lage stayed at „Lagebericht wird erstellt …“.
            return "Empfohlen: die Ursache in der Lage beheben, dann „Aktualisieren“."
        if recommended:
            verb = VERB_BY_KEY[recommended]
            enabled, _reason = availability(verb, state)
            if not enabled and verb.slice:
                # Live 2026-10-02: "Empfohlen: Abschließen" next to a disabled button.
                return (f"Nächster Schritt wäre „{verb.label}“ — die Schaltfläche folgt mit Plan "
                        f"{verb.slice}; bis dahin als Auftrag im Tab „Arbeiten“.")
            return f"Empfohlen: {verb.label}. Details im Tooltip der Schaltfläche."
        return "Gerade ist kein Auftrag empfohlen — siehe Lage."

    def run_verb(self, verb: Verb) -> None:
        enabled, reason = availability(verb, self.repo_state, recover_offered=self.recover_offered)
        if not enabled:
            self.status_var.set(reason)
            return
        if verb.key == ARBEITEN:
            if self.on_open_work is not None:
                self.on_open_work()
            return
        task = self.tasks_by_key.get(verb.task_key or "")
        if task is None:
            return
        inputs = None
        if task.inputs:
            inputs = self.ask_inputs(task)
            if inputs is None:
                self.status_var.set(f"{task.label} abgebrochen.")
                return
        if task.confirm and not self.confirm(task):
            self.status_var.set(f"{task.label} nicht gestartet.")
            return
        self.start_standard_task(task, inputs)

    def _task_running(self) -> bool:
        # AGP_ONE_TASK_ALL_TABS_V1
        from agp_cockpit.core.mission_http_client import mission_running
        if getattr(self, "_task_active", False):   # AGP_AMPEL_TASK_ACTIVE_V1
            return True
        external = getattr(self, "external_task_active", None)
        if external is not None and external():          # AGP_LAGE_ALL_TABS_V1
            return True
        try:
            mission = (bridge_status() or {}).get("mission") or {}
        except Exception:  # noqa: BLE001 - an unreachable bridge runs no task
            return False
        return mission_running(mission)

    def _watch_lage(self) -> None:
        from agp_cockpit.core.repo_state import local_fingerprint
        try:
            current = local_fingerprint(self.repository_root)
        except Exception:  # noqa: BLE001 - the poll never breaks the panel
            current = None
        previous = self._lage_fingerprint
        if current is not None and previous is not None and current != previous:
            if self._lage_result is not None and not self._task_running():
                self._lage_fingerprint = current
                self.refresh_lage()
        elif current is not None:
            self._lage_fingerprint = current
        self.after(LAGE_POLL_MS, self._watch_lage)

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
            self.update_ampel(lage_error=str(result))
            return
        self.repo_state = result
        if self._late_check and self._tracked_task is not None:
            self._late_check = False
            done, verdict = late_completion_verdict(
                self._tracked_task.key, self._tracked_head, result, self.repository_root)
            if done:
                self.recover_offered = False   # nothing to recover: the work is merged
            self.status_var.set(self.status_var.get() + "\n" + verdict)
        self.apply_state(result)
        self._maybe_auto_finish(result)
        text = describe(result)
        effective = getattr(self, "_effective_recommended", None)
        if effective and effective != result.recommended and result.recommended:
            # One recommendation in the whole tab (follow-up or R6 override).
            text = text.replace(f"Empfohlen: {rs_labels()[result.recommended]}",
                                f"Empfohlen: {rs_labels()[effective]} (nach dem letzten Task)")
        self.lage_var.set(text)

    def request_auto_finish(self, attempts: int = 15) -> None:
        """AGP_AUTO_FINISH_V1 (owner 2026-10-07): the task of the „Arbeiten“ tab ended DONE and
        its start click (with the tick) approved „Abschließen“; start it once the Lage agrees."""
        self._auto_finish_pending = attempts
        self.refresh_lage()

    def _maybe_auto_finish(self, state) -> None:
        pending = getattr(self, "_auto_finish_pending", 0)
        if not pending or state is None:
            return
        from agp_cockpit.core import repo_state as rs
        if state.state == rs.LAEUFT:
            # the ended task can still count as running for a moment
            self._auto_finish_pending = pending - 1
            if self._auto_finish_pending:
                self.after(1000, self.refresh_lage)
            else:
                self.status_var.set(self.status_var.get()
                                    + "\nAbschließen nicht automatisch gestartet: es läuft noch ein Task.")
            return
        self._auto_finish_pending = 0
        verb = VERB_BY_KEY[rs.ABSCHLIESSEN]
        enabled, reason = availability(verb, state, recover_offered=self.recover_offered)
        if not enabled or state.recommended != rs.ABSCHLIESSEN:
            why = reason or f"die Lage ist {state.state} — nichts zu veröffentlichen"
            self.status_var.set(self.status_var.get() + f"\nAbschließen nicht automatisch gestartet: {why}.")
            return
        task = self.tasks_by_key.get(verb.task_key or "")
        if task is not None and self.start_standard_task(task, None):
            self._auto_finish_started = True

    def note_external_result(self, text: str) -> None:
        """AGP_WORK_TAB_HANDOFF_V1: the result of the „Arbeiten“ tab, named as such."""
        self._tracked_task = None
        self._last_outcome = "DONE"
        self.status_var.set(f"Arbeiten · {text}" if text else "Arbeiten · Fertig ✓")
        self._status_detail = ""

    def _manual_release_hint(self) -> str:
        """AGP_MANUAL_GITHUB_RELEASE_HINT_V1: name the owner's GitHub step after the tag."""
        from agp_cockpit.core.release_hygiene import manual_github_release_command
        version = str((self._tracked_inputs or {}).get("version") or "").strip()
        command = manual_github_release_command(self.repository_root, version) if version else ""
        self.show_followup_command(command)
        if not command:
            return ""
        return (f"\nNoch offen: der GitHub-Eintrag „v{version}“ (publication: none, bis KIT-GF-049 "
                "behoben ist) — „GitHub-Befehl kopieren“ und im Terminal ausführen.")

    def show_followup_command(self, command: str) -> None:
        self._followup_command = command
        if command:
            self.copy_command_button.grid()
        else:
            self.copy_command_button.grid_remove()

    def copy_followup_command(self) -> None:
        if not self._followup_command:
            return
        self.clipboard_clear()
        self.clipboard_append(self._followup_command)
        self.status_var.set(self.status_var.get() + "\nBefehl kopiert.")

    def _track(self, mission_id: str) -> None:
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        self._tracked_mission_id = mission_id
        self._last_outcome = ""
        self._status_detail = ""
        self._task_active = True   # AGP_AMPEL_TASK_ACTIVE_V1
        self.show_followup_command("")
        self._poll_job = self.after(2000, self.refresh_progress)

    def refresh_progress(self) -> None:
        self._poll_job = None
        mission_id = self._tracked_mission_id
        if not mission_id:
            return
        try:
            bridge = bridge_status()
            progress = describe_standard_task_progress(
                mission_id=mission_id,
                task_status=self.api.status(),
                bridge_status=bridge,
            )
        except Exception as exc:  # noqa: BLE001 - polling survives transient bridge/DB errors.
            self.status_var.set(f"Status momentan nicht verfügbar ({exc}) — neuer Versuch läuft.")
            self._poll_job = self.after(3000, self.refresh_progress)
            return
        text = progress.text
        if self._tracked_task is not None:   # AGP_RESULT_NAMES_TASK_V1
            text = f"{self._tracked_task.label} · {text}"
        current = (bridge or {}).get("mission") or {}
        if (progress.outcome == "HUMAN_REQUIRED" and current.get("state") == "NEEDS_HUMAN"
                and current.get("mission_id") == mission_id and self._tracked_task is not None):
            self._show_decision(mission_id, str(current.get("last_summary") or ""))
        effects = self.effects_text()
        if effects:
            text += "\n" + effects
        task = self._tracked_task
        if progress.terminal and task is not None and progress.outcome == "DONE":
            self._bind_active_chat()
            self.recover_offered = False   # AGP_RECOVER_OFFER_CLEARS_V1
        if progress.terminal and task is not None:
            if progress.outcome == "DONE" and task.key == "release":
                text += self._manual_release_hint()
            if progress.outcome == "DONE" and task.follow_up:
                text += f"\nAls Nächstes empfohlen: „{task.follow_up}“."
                self.follow_up_key = next((v.key for v in VERBS if v.label == task.follow_up), None)
            if progress.outcome == "STOPPED" and stopped_by_assistant_timeout(current) \
                    and current.get("mission_id") == mission_id:
                # AGP_LATE_COMPLETION_CHECK_V1: verified against the Lagebericht below.
                self._late_check = True
                text += "\nDie Remote-Antwort kam nicht rechtzeitig — das Cockpit prüft den Stand lokal …"
            if progress.outcome != "DONE" and task.offers_recover_on_interrupt:
                if self._effects_executed():
                    # R6: an interrupted Abschließen with executed effects
                    # offers Wiederherstellen.
                    self.recover_offered = True
                    text += (f"\n{task.label} wurde unterbrochen — „Wiederherstellen“ ist freigeschaltet "
                             "und empfohlen.")
                else:
                    # Live 2026-10-02: a send failure before any effect left
                    # nothing to recover; the task can simply be started again.
                    text += f"\n{task.label} wurde vor jeder Wirkung unterbrochen — einfach erneut starten."
        self.status_var.set(text)
        self._status_detail = progress.detail
        if progress.terminal:
            self._task_active = False   # AGP_AMPEL_TASK_ACTIVE_V1
            self._last_outcome = progress.outcome
            self.update_ampel()
        if not progress.terminal:
            self._poll_job = self.after(2000, self.refresh_progress)
        else:
            self.refresh_lage()   # the finished task changed the repository state


def pending_standard_decision(mission: dict, tasks) -> tuple[StandardTask | None, str]:
    """The standard task a NEEDS_HUMAN mission belongs to (title "Standard · <label>[ · …]")."""
    title = str(mission.get("title") or "")
    if mission.get("state") != "NEEDS_HUMAN" or not title.startswith("Standard · "):
        return None, ""
    label = title[len("Standard · "):].split(" · ")[0]
    task = next((t for t in tasks if t.label == label), None)
    return task, str(mission.get("mission_id") or "") if task is not None else ""
