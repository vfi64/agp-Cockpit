from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from agp_cockpit.core import work_facts
from agp_cockpit.core.ampel import work_ampel
from agp_cockpit.core.chrome_automation import require_allowed_active_chat
from agp_cockpit.core.human_decision import decision_mission_text
from agp_cockpit.core.mission_http_client import create_live_full_auto, record_decision
from agp_cockpit.core.mission_http_client import status as mission_status
from agp_cockpit.core.standard_task_progress import describe_standard_task_progress
from agp_cockpit.core.start_request_client import request_task_start
from agp_cockpit.core.task_contract_text import (
    contract_from_text,
    editor_text_from_file,
)
from agp_cockpit.core.task_operator_api import TaskOperatorAPI
from agp_cockpit.ui.flow_row import FlowRow
from agp_cockpit.ui.scrollable import follow_viewport

EDITOR_LINES = 8      # AGP_FIXED_EDITOR_V1
QUESTION_LINES = 5    # AGP_DECISION_BOX_V2


class SimpleTaskPanel(ttk.Frame):
    """Default task-first surface. Expert controls stay elsewhere."""

    def __init__(self, master: tk.Misc, *, repository_root: Path, local_contract=None,
                 on_task_event=None, repo_light=None) -> None:
        super().__init__(master, padding=16)
        self.on_task_event = on_task_event   # AGP_WORK_TAB_HANDOFF_V1
        self.repository_root = repository_root.expanduser().resolve()
        self.api = TaskOperatorAPI(self.repository_root, local_contract=local_contract)
        self.contract: dict | None = None
        self._mission_id = ""
        self.workflow_phase = "EMPTY"

        self.columnconfigure(0, weight=1)
        self.rowconfigure(7, weight=1)        # spare space stays below the boxes
        self._wrapping: list[ttk.Label] = []
        self._repo_light = repo_light         # AGP_WORK_AMPEL_V1: Lage light at rest
        self._last_outcome = ""
        self._waiting_note = ""
        self.ampel_state = None

        # AGP_WORK_AMPEL_V1 (owner 2026-10-06): one light, as in „Standard Tasks“.
        light = ttk.Frame(self)
        light.grid(row=0, column=0, sticky="ew")
        light.columnconfigure(1, weight=1)
        self.ampel_dot = ttk.Label(light, text="●", font=("TkDefaultFont", 22), foreground="#888888")
        self.ampel_dot.grid(row=0, column=0, sticky="w")
        self.ampel_var = tk.StringVar(value="Grau — Lage wird geprüft")
        self._wrap(ttk.Label(light, textvariable=self.ampel_var, font=("TkDefaultFont", 13, "bold"),
                             justify="left"), 80).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._wrap(ttk.Label(
            self,
            text=(
                "Ein Auftrag hinein; das Cockpit prüft und überwacht ihn und behandelt technische "
                "Fehler selbst. Gefragt wirst du nur bei "
                "strategischen oder ausdrücklich menschlichen Entscheidungen."
            ),
            foreground="#888888",
            justify="left",
        ), 20).grid(row=1, column=0, sticky="ew", pady=(2, 8))

        # AGP_FLOW_ROW_V1: the buttons wrap with the window instead of being cut off.
        actions = FlowRow(self)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.actions = actions

        self.load_button = actions.add(ttk.Button(actions, text="Auftrag laden", command=self.load_contract))
        self.new_button = actions.add(ttk.Button(actions, text="Neuer Auftrag", command=self.new_task))
        self.start_button = actions.add(ttk.Button(
            actions, text="Task starten", command=self.start_task, state="disabled"
        ))
        self.pause_button = actions.add(ttk.Button(actions, text="Pause", command=self.pause_file_loop))
        self.resume_button = actions.add(ttk.Button(actions, text="Fortsetzen", command=self.resume_file_loop))
        self.stop_button = actions.add(ttk.Button(actions, text="Stop", command=self.stop_file_loop))
        self.reset_button = actions.add(ttk.Button(actions, text="Reset", command=self.reset_file_loop))
        self.approve_button = actions.add(ttk.Button(
            actions,
            text="Entscheidung freigeben",
            command=self.approve_checkpoint,
            state="disabled",
        ))

        # AGP_TASK_EDITOR_V1: the task is typed, pasted (Cmd+V) or loaded into
        # this editor and can be changed until it is started.
        # AGP_FIXED_EDITOR_V1 (owner 2026-10-06): a fixed height with its own scroll
        # bar; the window's spare room stays for the decision box and its buttons.
        editor_frame = ttk.LabelFrame(
            self,
            text="Auftrag (Text oder JSON-Task-Contract)",
            padding=4,
        )
        editor_frame.grid(row=3, column=0, sticky="ew")
        editor_frame.columnconfigure(0, weight=1)
        self.editor = tk.Text(editor_frame, height=EDITOR_LINES, width=40, wrap="word", undo=True,
                              font="TkFixedFont")
        self.editor.grid(row=0, column=0, sticky="ew")
        scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=scrollbar.set)
        self.editor.bind("<<Modified>>", self._on_editor_modified)

        # AGP_HUMAN_DECISION_V1: answer a NEEDS_HUMAN question and continue the
        # same task; "Freigeben" is a one-shot approval of remote effects.
        # AGP_DECISION_BOX_V2 (owner 2026-10-06): right under the editor; the question
        # scrolls in a box of fixed height, the buttons sit beside it and stay visible,
        # and the Cockpit's own facts (branch, commit, files) stand next to the claims.
        self._decision_mission_id = ""
        self._decision_question = ""
        self._decision_facts = None
        self.decision_frame = ttk.LabelFrame(self, text="Deine Entscheidung ist gefragt", padding=8)
        self.decision_frame.columnconfigure(0, weight=1)
        self.decision_question = tk.Text(self.decision_frame, height=QUESTION_LINES, width=30,
                                         wrap="word", relief="flat", takefocus=0)
        self.decision_question.grid(row=0, column=0, sticky="ew")
        question_bar = ttk.Scrollbar(self.decision_frame, orient="vertical",
                                     command=self.decision_question.yview)
        question_bar.grid(row=0, column=1, sticky="ns")
        self.decision_question.configure(yscrollcommand=question_bar.set, state="disabled")
        buttons = ttk.Frame(self.decision_frame)
        buttons.grid(row=0, column=2, rowspan=3, sticky="ne", padx=(8, 0))
        self.approve_decision_button = ttk.Button(
            buttons, text="Freigeben", command=lambda: self.decide("APPROVE")
        )
        self.approve_decision_button.grid(row=0, column=0, sticky="ew")
        self.reject_decision_button = ttk.Button(
            buttons, text="Ablehnen", command=lambda: self.decide("REJECT")
        )
        self.reject_decision_button.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.diff_button = ttk.Button(buttons, text="Änderungen ansehen", command=self.show_changes)
        self.diff_button.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.decision_facts_var = tk.StringVar(value="")
        self._wrap(ttk.Label(self.decision_frame, textvariable=self.decision_facts_var,
                             foreground="#888888", justify="left"), 200).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        note_row = ttk.Frame(self.decision_frame)
        note_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        note_row.columnconfigure(1, weight=1)
        ttk.Label(note_row, text="Hinweis (optional):").grid(row=0, column=0, sticky="nw", padx=(0, 6))
        self.decision_note = tk.Text(note_row, height=2, width=20, wrap="word", undo=True)
        self.decision_note.grid(row=0, column=1, sticky="ew")
        self.decision_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.decision_frame.grid_remove()

        self.state_var = tk.StringVar(value="Bereit — Auftrag eingeben, einfügen oder laden.")
        self._wrap(ttk.Label(
            self,
            textvariable=self.state_var,
            justify="left",
        ), 20).grid(row=5, column=0, sticky="ew", pady=(8, 0))

        self.activity_var = tk.StringVar(
            value="Aktivität: noch kein automatischer Arbeitsschritt gestartet."
        )
        self._wrap(ttk.Label(
            self,
            textvariable=self.activity_var,
            justify="left",
        ), 20).grid(row=6, column=0, sticky="ew", pady=(4, 0))
        self.bind("<Configure>", self._rewrap, add="+")
        self._viewport_width = 0
        follow_viewport(self, self._follow_viewport)

        self.after(750, self.refresh_status)

    def _follow_viewport(self, width: int) -> None:
        self._viewport_width = width
        self._rewrap()

    def _wrap(self, label: ttk.Label, margin: int) -> ttk.Label:
        """Wrap at the panel width minus ``margin`` pixels (as in „Standard Tasks“)."""
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

    def update_ampel(self) -> None:
        """AGP_WORK_AMPEL_V1: recompute the light of this tab."""
        repo_light = None
        if self._repo_light is not None:
            try:
                repo_light = self._repo_light()
            except Exception:  # noqa: BLE001 - the light never breaks the panel
                repo_light = None
        light = work_ampel(self.workflow_phase, outcome=self._last_outcome,
                           decision_pending=bool(self._decision_mission_id),
                           waiting=self._waiting_note, repo_light=repo_light)
        if light != self.ampel_state:
            self.ampel_state = light
            self.ampel_var.set(light.text)
            self.ampel_dot.configure(foreground=light.hex)

    def _show_file_loop_state(self, snapshot: dict) -> None:
        self.activity_var.set(f"File-Loop: {snapshot['state']} · Generation {snapshot['generation']}")
    def pause_file_loop(self) -> None:
        self._show_file_loop_state(self.api.file_loop_pause())
    def resume_file_loop(self) -> None:
        self._show_file_loop_state(self.api.file_loop_resume())
    def stop_file_loop(self) -> None:
        self._show_file_loop_state(self.api.file_loop_stop())
    def reset_file_loop(self) -> None:
        self._show_file_loop_state(self.api.file_loop_reset())

    def approve_checkpoint(self) -> None:
        try:
            status = self.api.approve_checkpoint()
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces checkpoint failures.
            self.state_var.set(f"Freigabe fehlgeschlagen — {exc}")
            return
        self.approve_button.configure(state="disabled")
        self.state_var.set(
            self._human_runtime_state(
                status.get("state"), status.get("suspension_reason")
            )
        )

    def _editor_text(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def _set_editor(self, text: str, *, editable: bool = True) -> None:
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.editor.configure(state="normal" if editable else "disabled")
        self._update_start_button()

    def _update_start_button(self) -> None:
        startable = self.workflow_phase != "STARTED" and bool(self._editor_text().strip())
        self.start_button.configure(state="normal" if startable else "disabled")

    def _on_editor_modified(self, _event=None) -> None:
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        if self.workflow_phase == "STARTED":
            return
        self.workflow_phase = "LOADED" if self._editor_text().strip() else "EMPTY"
        self._update_start_button()
        self.state_var.set(
            "Auftrag bereit — kann gestartet werden."
            if self.workflow_phase == "LOADED"
            else "Bereit — Auftrag eingeben, einfügen oder laden."
        )

    def _show_decision(self, mission_id: str, question: str) -> None:
        if self._decision_mission_id == mission_id:
            return
        self._decision_mission_id = mission_id
        self._decision_question = question
        self.decision_question.configure(state="normal")
        self.decision_question.delete("1.0", "end")
        self.decision_question.insert("1.0", question or "Die Remote-Seite braucht eine Entscheidung.")
        self.decision_question.configure(state="disabled")
        self.refresh_decision_facts()
        self.decision_note.delete("1.0", "end")
        self.decision_frame.grid()
        self.approve_decision_button.focus_set()
        self.update_ampel()
        self.after_idle(self._scroll_to_decision)

    def _scroll_to_decision(self) -> None:
        """AGP_DECISION_BOX_V2: in a small window the tab scrolls so that the box is in view."""
        tab = self.master
        while tab is not None and not (hasattr(tab, "canvas") and hasattr(tab, "inner")):
            tab = getattr(tab, "master", None)
        if tab is None or not self.decision_frame.winfo_ismapped():
            return
        self.update_idletasks()
        total = max(1, tab.inner.winfo_height())
        top = self.decision_frame.winfo_rooty() - tab.inner.winfo_rooty()
        tab.canvas.yview_moveto(max(0.0, (top - 8) / total))

    def refresh_decision_facts(self) -> None:
        """AGP_DECISION_FACTS_V1: the Cockpit's own read-only view of the repository."""
        try:
            self._decision_facts = work_facts.observe(self.repository_root)
            self.decision_facts_var.set(work_facts.facts_line(self._decision_facts))
        except Exception as exc:  # noqa: BLE001 - facts never block the decision
            self._decision_facts = None
            self.decision_facts_var.set(f"Vom Cockpit geprüft: nicht lesbar ({exc}).")

    def show_changes(self) -> None:
        """„Änderungen ansehen“: the diff against origin/main in a read-only window."""
        self.refresh_decision_facts()
        facts = self._decision_facts or work_facts.observe(self.repository_root)
        window = tk.Toplevel(self)
        window.title(f"Änderungen — {facts.branch or self.repository_root.name}")
        window.geometry("900x600")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        text = tk.Text(window, wrap="none", font="TkFixedFont")
        text.grid(row=0, column=0, sticky="nsew")
        vbar = ttk.Scrollbar(window, orient="vertical", command=text.yview)
        vbar.grid(row=0, column=1, sticky="ns")
        hbar = ttk.Scrollbar(window, orient="horizontal", command=text.xview)
        hbar.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        text.insert("1.0", work_facts.diff_text(self.repository_root, facts))
        text.configure(state="disabled")
        ttk.Button(window, text="Schließen", command=window.destroy).grid(row=2, column=0, sticky="e",
                                                                          padx=8, pady=6)
        self.changes_window = window

    def _hide_decision(self) -> None:
        self._decision_mission_id = ""
        self._decision_question = ""
        self.decision_frame.grid_remove()
        self.update_ampel()

    def decide(self, decision: str) -> None:
        mission_id = self._decision_mission_id
        if not mission_id or self.contract is None:
            return
        from agp_cockpit.core.build_freshness import start_block_reason
        blocked = start_block_reason(self.repository_root)
        if blocked:   # AGP_STALE_APP_GUARD_V1: the continuation would run the old build
            self.state_var.set(blocked)
            return
        note = self.decision_note.get("1.0", "end-1c").strip()
        try:
            record_decision(mission_id=mission_id, decision=decision, note=note)
            # The NEEDS_HUMAN stop left a durable STOP; the continuation of
            # the same task starts from a clean running control state.
            self.api.operator_control.request("RESUME")
            mission = create_live_full_auto(
                title="Task · " + str(
                    self.contract.get("title") or self.contract.get("task_id") or "AGP Task"
                ) + " · Entscheidung",
                mission_text=decision_mission_text(
                    goal_text=self._remote_mission_text(),
                    decision=decision,
                    question=self._decision_question,
                    note=note,
                ),
                conversation_url=require_allowed_active_chat().url,
            )["mission"]
            request_task_start(
                str(mission["mission_id"]),
                task_id=str(self.contract.get("task_id") or ""),
            )
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces decision failures.
            self.state_var.set(f"Entscheidung nicht übermittelt — {exc}")
            return
        self._mission_id = str(mission["mission_id"])
        self._hide_decision()
        self.workflow_phase = "STARTED"
        self._last_outcome = ""
        self.update_ampel()
        self.editor.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.state_var.set(
            ("Freigegeben" if decision == "APPROVE" else "Abgelehnt")
            + " — der Auftrag läuft im selben Chat weiter."
        )

    def new_task(self) -> None:
        if self.workflow_phase == "STARTED":
            self.state_var.set("Ein Auftrag läuft noch — erst stoppen oder abschließen lassen.")
            return
        self.contract = None
        self._mission_id = ""
        self._last_outcome = ""
        self.workflow_phase = "EMPTY"
        self._hide_decision()
        self._set_editor("")
        self.editor.focus_set()
        self.state_var.set("Bereit — Auftrag eingeben, einfügen oder laden.")

    def load_contract(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Auftrag auswählen",
            filetypes=[("Textaufträge", "*.txt"), ("JSON-Aufträge", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        if self.workflow_phase == "STARTED":
            self.state_var.set("Ein Auftrag läuft noch — erst stoppen oder abschließen lassen.")
            return
        try:
            text = editor_text_from_file(Path(path))
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces file errors.
            messagebox.showerror("Auftrag laden", str(exc), parent=self.winfo_toplevel())
            return

        self.workflow_phase = "LOADED"
        self._set_editor(text)
        self.start_button.focus_set()
        self.state_var.set("Auftrag geladen ✓ — bereit zum Starten; vor dem Start im Editor änderbar.")

    def _remote_mission_text(self) -> str:
        assert self.contract is not None
        return (
            "Execute the following overall AGP Cockpit Task Contract. "
            "Continue autonomously across technical failures and recovery when the "
            "contract and Agentic Project Kit permit it. Return exactly one executable "
            "work order per turn. Do not bypass Kit BLOCKED/FAIL. Ask the human only "
            "for explicit human checkpoints or a genuinely strategic decision that "
            "cannot be resolved from repository authority.\n\nTASK CONTRACT:\n"
            + json.dumps(self.contract, ensure_ascii=False, indent=2)
        )

    def start_task(self) -> None:
        # AGP_STALE_APP_GUARD_V1: never start a task on an outdated app.
        from agp_cockpit.core.build_freshness import start_block_reason
        blocked = start_block_reason(self.repository_root)
        if blocked:
            self.state_var.set(blocked)
            return
        # AGP_ONE_TASK_ALL_TABS_V1 (R5, live 2026-10-04): a start here while „Arbeit beginnen“
        # still ran replaced its mission; its work order then landed in this task without scope.
        from agp_cockpit.core.mission_http_client import task_running
        if task_running():
            self.state_var.set("Blockiert — es läuft bereits ein Task (z. B. „Arbeit beginnen“); "
                               "neue Aufträge erst nach seinem Ende (R5).")
            return
        try:
            self.contract = contract_from_text(self._editor_text())
        except ValueError as exc:
            self.state_var.set(f"Auftrag nicht startbereit — {exc}")
            return
        try:
            self.contract = self.api.prepare_task_contract(self.contract)
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces validation failures.
            self.state_var.set(f"Auftrag nicht startbereit — automatische technische Prüfung fehlgeschlagen: {exc}")
            return
        if not messagebox.askyesno(
            "Task starten",
            "Der geprüfte Gesamtauftrag wird jetzt als dauerhafter Task angelegt.\n\nFortfahren?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            status = self.api.start_task_from_contract(self.contract)
            conversation_url = require_allowed_active_chat().url
            mission_response = create_live_full_auto(
                title="Task · " + str(
                    self.contract.get("title") or self.contract.get("task_id") or "AGP Task"
                ),
                mission_text=self._remote_mission_text(),
                conversation_url=conversation_url,
            )
            mission = mission_response["mission"]
            self._mission_id = str(mission["mission_id"])
            request_task_start(
                str(mission["mission_id"]),
                task_id=str(self.contract.get("task_id") or ""),
            )
        except Exception as exc:  # noqa: BLE001 - UI boundary surfaces start failures.
            self.state_var.set(f"Blockiert — Start fehlgeschlagen: {exc}")
            return
        self.workflow_phase = "STARTED"
        self._last_outcome = ""
        self._emit("started")
        self._hide_decision()
        self.start_button.configure(state="disabled")
        self.editor.configure(state="disabled")
        self.state_var.set(
            self._human_runtime_state(status.get("state"), status.get("suspension_reason"))
        )

    @staticmethod
    def _human_runtime_state(state: str | None, reason: str | None = None) -> str:
        if reason == "WAITING_FOR_HUMAN":
            return "Deine Entscheidung ist erforderlich — die automatische Bearbeitung ist angehalten."
        if state == "VERIFIED_COMPLETE":
            return "Auftrag abgeschlossen ✓ — Ergebnis wurde verifiziert."
        if state == "REMOTE_DONE":
            return "Auftrag abgeschlossen — von der Remote-Seite gemeldet, lokal nicht geprüft."
        if state in {"ACTIVE", "WAITING_FOR_REMOTE", "COMPLETE_PROPOSED"}:
            return (
                "Auftrag läuft — das Cockpit arbeitet bzw. wartet auf die nächste "
                "automatische Verarbeitung. Du musst momentan nichts tun."
            )
        if state == "SUSPENDED":
            return f"Auftrag angehalten — {reason or 'Grund unbekannt'}."
        return "Cockpit bereit."

    def task_active(self) -> bool:
        """AGP_LAGE_ALL_TABS_V1: a task started here runs until its progress is terminal."""
        return self.workflow_phase == "STARTED"

    def _emit(self, event: str, text: str = "") -> None:
        if self.on_task_event is not None:
            try:
                self.on_task_event(event, text)
            except Exception:  # noqa: BLE001 - the other tab never breaks this one
                pass

    def refresh_status(self) -> None:
        self.update_ampel()
        try:
            # Vor dem tatsächlichen Start gehört die Statuszeile dem lokalen
            # Laden/Prüfen-Ablauf. Ein alter persistenter Task darf das
            # Prüfergebnis nicht mit WAITING_FOR_REMOTE überschreiben.
            if self.workflow_phase != "STARTED":
                self.after(1000, self.refresh_status)
                return
            status = self.api.status()
            waiting_for_human = (
                status.get("suspension_reason") == "WAITING_FOR_HUMAN"
            )
            self.approve_button.configure(
                state="normal" if waiting_for_human else "disabled"
            )
            self.state_var.set(
                self._human_runtime_state(
                    status.get("state"), status.get("suspension_reason")
                )
            )
            mission_status_payload = mission_status()
            mission = mission_status_payload.get("mission")
            # AGP_TASK_PROGRESS_FROM_MISSION_V1: live 2026-09-30 the panel said
            # "Auftrag läuft" while the mission was STOPPED, because it showed
            # only the durable task state. The started mission decides.
            if getattr(self, "_mission_id", "") and not waiting_for_human:
                progress = describe_standard_task_progress(
                    mission_id=self._mission_id,
                    task_status=status,
                    bridge_status=mission_status_payload,
                    locally_verified=False,
                )
                self.state_var.set(progress.text)
                current = mission_status_payload.get("mission") or {}
                if (
                    progress.outcome == "HUMAN_REQUIRED"
                    and current.get("state") == "NEEDS_HUMAN"
                    and current.get("mission_id") == self._mission_id
                ):
                    self._show_decision(self._mission_id, str(current.get("last_summary") or ""))
                if progress.terminal:
                    # The finished task stays in the editor and can be
                    # changed and started again.
                    self.workflow_phase = "LOADED"
                    self._last_outcome = progress.outcome
                    self._waiting_note = ""
                    self.update_ampel()
                    self._emit("finished_done" if progress.outcome == "DONE" else "finished",
                               progress.text)
                    self.editor.configure(state="normal")
                    self._update_start_button()
            if mission is None:
                self.activity_var.set(
                    "Aktivität: Task ist angelegt; Browser-Mission wurde noch nicht beobachtet."
                )
            else:
                transport_event = mission.get("browser_transport_event", "")
                self._waiting_note = ("wartet auf das ChatGPT-Anhangslimit"
                                      if transport_event == "K07_ATTACHMENT_LIMIT_HOLD" else "")
                if transport_event in {"NATIVE_TRANSPORT_FAILED", "MISSION_BOOTSTRAP_SEND_FAILED"}:
                    self.state_var.set("Browser-Übertragung fehlgeschlagen — der Auftrag wartet auf Wiederaufnahme.")
                    self.activity_var.set("Aktivität: " + str(mission.get("browser_transport_note") or transport_event))
                    self.after(1000, self.refresh_status)
                    return
                if transport_event == "MISSION_TOUCHPOINT_SELFTEST_FAILED":
                    # AGP_MISSION_TOUCHPOINT_SELFTEST_V1: stopped before any send.
                    self.state_var.set("Selbsttest vor dem Start fehlgeschlagen — nichts gesendet; Seite prüfen, dann erneut starten.")
                    self.activity_var.set("Aktivität: " + str(mission.get("browser_transport_note") or transport_event))
                    self.after(1000, self.refresh_status)
                    return
                if transport_event == "SEND_INDETERMINATE":
                    self.state_var.set("Browser-Übertragung unbestätigt — Ergebnis wird geprüft; kein erneutes Senden.")
                turns = int(mission.get("turn_count", 0) or 0)
                steps = int(mission.get("step_count", 0) or 0)
                mstate = str(mission.get("state") or mission_status_payload.get("state") or "")
                if mstate in {"DONE", "COMPLETED", "VERIFIED_COMPLETE"}:
                    self.activity_var.set(
                        f"Aktivität: abgeschlossen · {turns} Remote-Turns · {steps} Schritte."
                    )
                elif mstate == "NEEDS_HUMAN":
                    self.activity_var.set(
                        f"Aktivität: wartet auf deine Entscheidung · {turns} Remote-Turns · {steps} Schritte."
                    )
                elif mstate in {"ERROR", "FAILED", "STOPPED", "CANCELLED", "BLOCKED"}:
                    self.activity_var.set(
                        f"Aktivität: angehalten/fehlgeschlagen · {turns} Remote-Turns · {steps} Schritte."
                    )
                elif turns > 0 or steps > 0:
                    self.activity_var.set(
                        f"Aktivität: Browser-Mission arbeitet · {turns} Remote-Turns · {steps} Schritte."
                    )
                else:
                    self.activity_var.set(
                        "Aktivität: Browser-Mission angelegt; wartet auf den ersten Remote-Turn."
                    )
        except Exception:  # noqa: BLE001 - polling remains alive across transient UI errors.
            self.activity_var.set("Aktivität: Status momentan nicht verfügbar.")
        self.after(1000, self.refresh_status)
