from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

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


class SimpleTaskPanel(ttk.Frame):
    """Default task-first surface. Expert controls stay elsewhere."""

    def __init__(self, master: tk.Misc, *, repository_root: Path, local_contract=None) -> None:
        super().__init__(master, padding=16)
        self.repository_root = repository_root.expanduser().resolve()
        self.api = TaskOperatorAPI(self.repository_root, local_contract=local_contract)
        self.contract: dict | None = None
        self._mission_id = ""
        self.workflow_phase = "EMPTY"

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        ttk.Label(self, text="AGP Cockpit", font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            self,
            text=(
                "Ein komplexer Auftrag hinein. Das Cockpit prüft und überwacht ihn. "
                "Technische Fehler und Recovery sollen automatisch behandelt werden; "
                "du wirst nur bei strategischen oder ausdrücklich menschlichen "
                "Entscheidungen wieder gefragt."
            ),
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 12))

        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="w", pady=(0, 10))

        self.load_button = ttk.Button(actions, text="Auftrag laden", command=self.load_contract)
        self.load_button.grid(row=0, column=0, padx=(0, 8))

        self.new_button = ttk.Button(actions, text="Neuer Auftrag", command=self.new_task)
        self.new_button.grid(row=0, column=1, padx=(0, 8))
        self.start_button = ttk.Button(
            actions, text="Task starten", command=self.start_task, state="disabled"
        )
        self.start_button.grid(row=0, column=2)
        self.pause_button = ttk.Button(actions, text="Pause", command=self.pause_file_loop)
        self.pause_button.grid(row=0, column=3, padx=(8, 0))
        self.resume_button = ttk.Button(actions, text="Fortsetzen", command=self.resume_file_loop)
        self.resume_button.grid(row=0, column=4, padx=(8, 0))
        self.stop_button = ttk.Button(actions, text="Stop", command=self.stop_file_loop)
        self.stop_button.grid(row=0, column=5, padx=(8, 0))
        self.reset_button = ttk.Button(actions, text="Reset", command=self.reset_file_loop)
        self.reset_button.grid(row=0, column=6, padx=(8, 0))
        self.approve_button = ttk.Button(
            actions,
            text="Entscheidung freigeben",
            command=self.approve_checkpoint,
            state="disabled",
        )
        self.approve_button.grid(row=0, column=7, padx=(8, 0))

        # AGP_TASK_EDITOR_V1: the task is typed, pasted (Cmd+V) or loaded into
        # this editor and can be changed until it is started.
        editor_frame = ttk.LabelFrame(
            self,
            text="Auftrag — eintippen, einfügen oder mit „Auftrag laden“ übernehmen (Text oder JSON-Task-Contract)",
            padding=4,
        )
        editor_frame.grid(row=3, column=0, sticky="nsew")
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)
        self.editor = tk.Text(editor_frame, height=14, wrap="word", undo=True, font="TkFixedFont")
        self.editor.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=scrollbar.set)
        self.editor.bind("<<Modified>>", self._on_editor_modified)

        self.state_var = tk.StringVar(value="Bereit — Auftrag eingeben, einfügen oder laden.")
        ttk.Label(
            self,
            textvariable=self.state_var,
            wraplength=760,
            justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))

        self.activity_var = tk.StringVar(
            value="Aktivität: noch kein automatischer Arbeitsschritt gestartet."
        )
        ttk.Label(
            self,
            textvariable=self.activity_var,
            wraplength=760,
            justify="left",
        ).grid(row=5, column=0, sticky="ew", pady=(4, 0))

        # AGP_HUMAN_DECISION_V1: answer a NEEDS_HUMAN question and continue the
        # same task; "Freigeben" is a one-shot approval of remote effects.
        self._decision_mission_id = ""
        self._decision_question = ""
        self.decision_frame = ttk.LabelFrame(self, text="Deine Entscheidung ist gefragt", padding=8)
        self.decision_frame.columnconfigure(0, weight=1)
        self.decision_question_var = tk.StringVar(value="")
        ttk.Label(
            self.decision_frame, textvariable=self.decision_question_var, wraplength=760, justify="left"
        ).grid(row=0, column=0, columnspan=3, sticky="ew")
        ttk.Label(self.decision_frame, text="Antwort / Hinweis (optional):").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 2)
        )
        self.decision_note = tk.Text(self.decision_frame, height=3, wrap="word", undo=True)
        self.decision_note.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.approve_decision_button = ttk.Button(
            self.decision_frame, text="Freigeben", command=lambda: self.decide("APPROVE")
        )
        self.approve_decision_button.grid(row=3, column=1, sticky="e", pady=(8, 0), padx=(0, 8))
        self.reject_decision_button = ttk.Button(
            self.decision_frame, text="Ablehnen", command=lambda: self.decide("REJECT")
        )
        self.reject_decision_button.grid(row=3, column=2, sticky="e", pady=(8, 0))
        self.decision_frame.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.decision_frame.grid_remove()

        self.after(750, self.refresh_status)

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
        self.decision_question_var.set(question or "Die Remote-Seite braucht eine Entscheidung.")
        self.decision_note.delete("1.0", "end")
        self.decision_frame.grid()
        self.approve_decision_button.focus_set()

    def _hide_decision(self) -> None:
        self._decision_mission_id = ""
        self._decision_question = ""
        self.decision_frame.grid_remove()

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
        self._hide_decision()
        self.workflow_phase = "EMPTY"
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

    def refresh_status(self) -> None:
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
                    self.editor.configure(state="normal")
                    self._update_start_button()
            if mission is None:
                self.activity_var.set(
                    "Aktivität: Task ist angelegt; Browser-Mission wurde noch nicht beobachtet."
                )
            else:
                transport_event = mission.get("browser_transport_event", "")
                if transport_event in {"NATIVE_TRANSPORT_FAILED", "MISSION_BOOTSTRAP_SEND_FAILED"}:
                    self.state_var.set("Browser-Übertragung fehlgeschlagen — der Auftrag wartet auf Wiederaufnahme.")
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
