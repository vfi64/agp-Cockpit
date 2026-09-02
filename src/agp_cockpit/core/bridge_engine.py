from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agp_cockpit.core.automation_guard import (
    AutomationGuard,
    AutomationLimits,
)
from agp_cockpit.core.bridge_execution import (
    ExecutedBridgeStep,
    execute_structured_work_order,
    order_argv,
    order_kind,
    order_label,
    preview_structured_work_order,
)
from agp_cockpit.core.bridge_protocol import (
    BrowserTurnRequest,
    BrowserTurnResponse,
)
from agp_cockpit.core.bridge_runtime import BridgeRuntime
from agp_cockpit.core.kit_error_report import (
    KitErrorEvidence,
    build_kit_error_report,
    write_kit_error_report,
)
from agp_cockpit.core.mission_control import parse_mission_signal
from agp_cockpit.core.response_pickup import extract_work_order_from_response


@dataclass
class BridgeEngine:
    repository_root: Path
    limits: AutomationLimits = field(default_factory=AutomationLimits)
    guard: AutomationGuard = field(init=False)

    def __post_init__(self) -> None:
        self.repository_root = self.repository_root.resolve()
        self.kit_binary = self.repository_root / ".venv/bin/agentic-kit"
        self.report_root = self.repository_root / ".local" / "kit-error-reports"
        self.runtime = BridgeRuntime(self.repository_root)
        self.guard = AutomationGuard(self.limits)

    def _require_runnable(self):
        state = self.runtime.require_state()

        if state.state == "WAITING_NEXT_STEP":
            return BrowserTurnResponse(
                action="stop",
                prompt="",
                state="WAITING_NEXT_STEP",
                note=(
                    "Single-step mission is waiting for explicit operator resume."
                ),
            )

        if state.state not in {"READY", "RUNNING"}:
            return BrowserTurnResponse(
                action="stop",
                prompt="",
                state=state.state,
                note=state.last_error,
            )

        return None

    @staticmethod
    def _is_kit_order(step: ExecutedBridgeStep) -> bool:
        argv = order_argv(step.order)
        return (
            order_kind(step.order) == "kit"
            or (argv and Path(argv[0]).name == "agentic-kit")
        )

    def _report_kit_failure(
        self,
        step: ExecutedBridgeStep,
    ) -> tuple[Path, Path]:
        argv = list(order_argv(step.order))
        label = order_label(step.order)

        report = build_kit_error_report(
            repository_root=self.repository_root,
            classification="AUTOMATED_WORKFLOW_KIT_DEFECT_CANDIDATE",
            title=f"Kit command failed during automated mission: {label}",
            summary=(
                "A Kit-owned command returned a non-zero result during "
                "the AGP Cockpit automated mission loop."
            ),
            workflow_phase="full-auto-browser-mission",
            expected_behavior=(
                "Validated Kit work order completes or returns a documented "
                "recoverable workflow state."
            ),
            observed_behavior=(
                f"returncode={step.returncode}; timed_out={step.timed_out}"
            ),
            reproduction_steps=[
                f"Open repository {self.repository_root}",
                "Use the same installed agentic-project-kit version.",
                "Run the captured command shown in Evidence.",
            ],
            evidence=[
                KitErrorEvidence(
                    command=argv,
                    returncode=step.returncode,
                    stdout=step.stdout,
                    stderr=step.stderr,
                )
            ],
            suspected_component=(
                argv[1] if len(argv) > 1 else "agentic-kit"
            ),
            impact="Mission progression interrupted.",
            regression_risk=(
                "Potential repeat failure for external workspaces using "
                "the same Kit route."
            ),
            notes=[
                "Generated automatically by AGP Cockpit.",
                "Classification is a defect candidate, not proof.",
                "Report is machine-local and not automatically committed.",
            ],
        )

        return write_kit_error_report(
            report,
            output_root=self.report_root,
        )

    def _next_prompt(self, result_block: str, *, passed: bool) -> str:
        if passed:
            prefix = "AGP Cockpit executed the bounded work order successfully."
        else:
            prefix = "The bounded work order FAILED."

        return (
            prefix
            + "\n\n"
            + result_block
            + "\n\nContinue the SAME overall mission with exactly ONE "
            "next bounded work order as one JSON object with keys kind, cwd, "
            "argv, timeout_seconds, label. "
            "If complete, return only "
            '{"mission_state":"DONE","summary":"<evidence-backed summary>"}. '
            "If human input is required, return only "
            '{"mission_state":"NEEDS_HUMAN","summary":"<decision required>"}.'
        )

    def handle_turn(
        self,
        request: BrowserTurnRequest,
    ) -> BrowserTurnResponse:
        try:
            blocked = self._require_runnable()
            if blocked is not None:
                return blocked

            state = self.runtime.require_state()
            self.runtime.mark_running()

            self.guard.before_turn()
            self.guard.record_assistant(request.assistant_text)
            self.runtime.record_assistant(request.assistant_text)

            signal = parse_mission_signal(request.assistant_text)
            if signal is not None:
                self.runtime.final(signal.state, signal.summary)
                return BrowserTurnResponse(
                    action="stop",
                    prompt="",
                    state=signal.state,
                    note=signal.summary,
                )

            extraction = extract_work_order_from_response(
                request.assistant_text
            )
            if extraction.work_order_text is None:
                self.guard.error()
                self.runtime.final(
                    "BLOCKED",
                    "No unique work order or final mission signal.",
                )
                return BrowserTurnResponse(
                    action="stop",
                    prompt="",
                    state="NEEDS_STRUCTURED_STEP",
                    note="No unique structured step.",
                )

            if state.execution_mode == "DRY_RUN":
                preview = preview_structured_work_order(
                    extraction.work_order_text,
                    repository_root=self.repository_root,
                    kit_binary=self.kit_binary,
                )
                prompt = (
                    "AGP Cockpit DRY_RUN accepted and previewed the work order "
                    "without executing it.\n\n"
                    + preview.preview_text
                )
                self.runtime.record_step_result(
                    result=preview.preview_text,
                    prompt=prompt,
                    passed=True,
                )
                return BrowserTurnResponse(
                    action="stop",
                    prompt="",
                    state="DRY_RUN_PREVIEW",
                    note=preview.preview_text,
                )

            step = execute_structured_work_order(
                extraction.work_order_text,
                repository_root=self.repository_root,
                kit_binary=self.kit_binary,
            )

            report_paths = None
            passed = (
                step.returncode == 0
                and not step.timed_out
            )

            if not passed and self._is_kit_order(step):
                report_paths = self._report_kit_failure(step)

            result_block = step.result_block
            if report_paths:
                result_block += (
                    "\n\nKIT DEFECT CANDIDATE REPORTS:\n"
                    f"JSON: {report_paths[0]}\n"
                    f"Markdown: {report_paths[1]}"
                )

            prompt = self._next_prompt(
                result_block,
                passed=passed,
            )

            self.guard.record_prompt(prompt)
            self.guard.success()

            updated = self.runtime.record_step_result(
                result=result_block,
                prompt=prompt,
                passed=passed,
            )

            if updated.run_mode == "SINGLE_STEP":
                return BrowserTurnResponse(
                    action="stop",
                    prompt="",
                    state="WAITING_NEXT_STEP",
                    note=result_block,
                )

            return BrowserTurnResponse(
                action="continue",
                prompt=prompt,
                state="STEP_PASS" if passed else "STEP_FAILED",
                note=f"turn={self.guard.turns}",
            )

        except Exception as exc:
            try:
                self.guard.error()
            except Exception as guard_exc:
                exc = guard_exc

            try:
                self.runtime.final(
                    "FAILED",
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass

            return BrowserTurnResponse(
                action="stop",
                prompt="",
                state="AUTOMATION_STOP",
                note=f"{type(exc).__name__}: {exc}",
            )
