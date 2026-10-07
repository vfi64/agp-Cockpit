from __future__ import annotations

import json
import secrets
import threading
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agp_cockpit import __version__
from agp_cockpit.adapters.macos_extension import (
    _manifest_build_id,
    _manifest_version,
    local_extension_root,
)
from agp_cockpit.core import result_projection
from agp_cockpit.core.bridge_engine import BridgeEngine
from agp_cockpit.core.bridge_protocol import (
    encode_turn_response,
    parse_turn_request,
)
from agp_cockpit.core.browser_refresh import (
    refresh_request_target,
    request_browser_refresh,
)
from agp_cockpit.core.command_file_contract import (
    WORK_ORDER_KIT_RULE,
    validate_command_content,
)
from agp_cockpit.core.diagnostic_log import DiagnosticLogger
from agp_cockpit.core.download_ingress import read_downloaded_command
from agp_cockpit.core.file_loop_orchestrator import (
    consume_command_file,
    mark_result_delivered,
    withhold_result_delivery,
)
from agp_cockpit.core.file_loop_protocol import (
    next_step_number,
    reserve_remote_issued_steps,
)
from agp_cockpit.core.file_loop_runner import RunNextProcessController
from agp_cockpit.core.handoff_completion import (
    FINAL_RECEIPT_PROMPT,
    acknowledge_delivery,
    contract_enabled,
    package_snapshot,
    prepare_receipt,
)
from agp_cockpit.core.protocol_execution_v1 import execute_direct_action
from agp_cockpit.core.runtime_paths import runtime_dir
from agp_cockpit.core.task_contract import LocalTaskContract
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_reply_policy import policy_for
from agp_cockpit.core.terminal_reply import (
    is_terminal_filename,
    parse_terminal_reply,
    record_terminal_reply,
)
from agp_cockpit.core.transport_protocol_v1 import (
    ActionRegistry,
    parse_action_frame,
    parse_result_frame,
)
from agp_cockpit.core.work_order import parse_work_order_json
from agp_cockpit.version import BRIDGE_BUILD_ID, BRIDGE_PROTOCOL_VERSION


@dataclass(frozen=True)
class BridgeServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    token: str = ""


_KIT_DIGEST_CACHE: dict[str, tuple[int, str, str]] = {}


def _kit_command_digest(repo_root: Path) -> dict[str, str]:
    """AGP_KIT_COMMAND_CATALOG_V1: digest of the manifest for the mission start."""
    from agp_cockpit.core.kit_command_catalog import KitCommandCatalog

    # AGP_KIT_INSTALLATION_AUTHORITY_V1: the installed Kit's manifest first.
    location = KitCommandCatalog.manifest_location(repo_root)
    if location is None:
        return {}
    manifest = location[0]
    mtime = (str(manifest), manifest.stat().st_mtime_ns)
    cached = _KIT_DIGEST_CACHE.get(str(repo_root))
    if cached is None or cached[0] != mtime:
        catalog = KitCommandCatalog.load(repo_root)
        if catalog is None:
            return {}
        target = catalog.write_digest(
            runtime_dir(repo_root, "kit", "agentic-kit-command-digest.json")   # AGP_RUNTIME_HOME_V1
        )
        cached = (mtime, str(target), catalog.manifest_sha)
        _KIT_DIGEST_CACHE[str(repo_root)] = cached
    return {"kit_command_digest_path": cached[1], "kit_manifest_sha": cached[2]}


MAX_POLICY_REJECTIONS = 3


def _correctable(error: Exception) -> bool:
    text = str(error)
    return ("semantic contract rejected" in text) or ("is not executable Python" in text)


REJECTED_COPY_LIMIT = 256 * 1024


def _keep_rejected_copy(download: Path, step: int, filename: str, content) -> str:
    """AGP_REJECTED_ORDER_KEPT_V1 (proposal 6, owner 2026-10-04: yes): the rejected work order
    is kept beside its rejection record (as .txt, never executable here) so the browser copy
    in ~/Downloads can go like the accepted ones (AGP_DOWNLOAD_HYGIENE_V1)."""
    if not isinstance(content, str) or not content:
        return ""
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in Path(str(filename)).name)[:120] or "order"
    target = download / f"{step}_agp_rejected_{safe}.txt"
    target.write_text(content[:REJECTED_COPY_LIMIT], encoding="utf-8")
    return target.name


def _policy_rejection_response(runtime_root: Path, repo_root: Path, engine, diag, *,
                               filename: str, reason: str, cycle_id: str,
                               terminal: bool = False, content=None) -> dict:
    """AGP_CORRECTABLE_REJECTION_V1: record the rejected work order under the
    expected step (the step is used up) and ask the remote side for a new one;
    after MAX_POLICY_REJECTIONS in one mission the human decides."""
    mission = engine.runtime.state
    store = runtime_root / "policy-rejections.json"
    try:
        counts = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else {}
    except (OSError, json.JSONDecodeError):
        counts = {}
    count = int(counts.get(mission.mission_id, 0)) + 1
    counts[mission.mission_id] = count
    store.write_text(json.dumps(counts, indent=1, sort_keys=True), encoding="utf-8")
    download = repo_root / "Download"
    step = next_step_number(download)
    download.mkdir(parents=True, exist_ok=True)
    kept = _keep_rejected_copy(download, step, filename, content)
    (download / f"{step}_agp_rejected.json").write_text(json.dumps(
        {"rejected_filename": filename, "reason": reason, "count": count, "kept_copy": kept}, indent=1) + "\n",
        encoding="utf-8")
    diag.event("K07_WORK_ORDER_REJECTED", component="file-loop",
               details={"filename": filename, "step": step, "count": count,
                        "reason": reason[:400], "cycle_id": cycle_id})
    if count > MAX_POLICY_REJECTIONS:
        human = (f"Arbeitsaufträge wurden {count}-mal wegen der Kommando-Regeln abgelehnt; "
                 f"zuletzt {filename}: {reason[:600]}")
        if mission.state not in _MISSION_ENDED_STATES:
            engine.runtime.final("NEEDS_HUMAN", human)
        return {"state": "NEEDS_HUMAN", "step": None, "result_file": None, "prompt": None,
                "terminal": True, "human_reason": human, "cycle_id": cycle_id, "replayed": False}
    next_step = next_step_number(download)
    if terminal:
        # AGP_TERMINAL_REPLY_CORRECTION_V1 (live 2026-10-04, step 1724): a terminal reply
        # with keys outside the protocol stopped the task; it is corrected like a work order.
        prompt = (
            "AGP COCKPIT — TERMINAL REPLY NOT ACCEPTED\n\n"
            f"Your terminal reply {filename} was rejected (attempt {count} of "
            f"{MAX_POLICY_REJECTIONS}):\n{reason}\n\n"
            "Return the same decision as a corrected terminal reply: one JSON object with only the "
            "keys \"state\" (DONE or NEEDS_HUMAN), \"reason\" (text; put every report there), "
            "\"step\" and, for a pull request, \"pr\". "
            f"Use exactly {next_step}_agp_terminal.json as the attachment filename and {next_step} as step."
        )
        return {"state": "CONTINUE", "terminal": False, "step": step, "next_step": next_step,
                "result_file": None, "prompt": prompt, "authority": "terminal-format",
                "human_reason": "Abschlussdatei abgelehnt — " + reason[:300], "cycle_id": cycle_id,
                "replayed": False}
    prompt = (
        "AGP COCKPIT — WORK ORDER NOT EXECUTED\n\n"
        f"Your work order {filename} was rejected by the local command authority and was not "
        f"run (attempt {count} of {MAX_POLICY_REJECTIONS}):\n{reason}\n\n"
        "Return a corrected work order. Choose the agentic-kit commands from the attached "
        "command digest of the installed Kit; prefer the most comprehensive orchestrator. "
        f"Use exactly {next_step}_...py as the attachment filename and {next_step} as STEP.\n"
        + WORK_ORDER_KIT_RULE
    )
    return {"state": "CONTINUE", "terminal": False, "step": step, "next_step": next_step,
            "result_file": None, "prompt": prompt, "authority": "command-authority",
            "human_reason": "Auftrag abgelehnt — " + reason[:300], "cycle_id": cycle_id,
            "replayed": False}


_MISSION_ENDED_STATES = frozenset(
    {"DONE", "COMPLETED", "NEEDS_HUMAN", "BLOCKED", "FAILED", "ERROR", "STOPPED", "CANCELLED"}
)


def _approval_grant(runtime_root: Path, engine) -> dict | None:
    """AGP_HUMAN_APPROVAL_SCOPE_V2: the open approval for the current mission.

    Claims the grant for the continuation mission and expires it once that
    mission has ended (or another mission of the task is current).
    """
    from agp_cockpit.core.human_decision import HumanDecisionStore
    from agp_cockpit.core.start_request import resolve_task_binding

    mission = engine.runtime.state
    if mission is None:
        return None
    binding = resolve_task_binding(runtime_root, mission.mission_id)
    task_id = str(binding.get("task_id") or "").strip()
    return HumanDecisionStore(runtime_root).grant_for_mission(
        task_id, mission.mission_id, mission_ended=mission.state in _MISSION_ENDED_STATES
    )


def _current_task_id(runtime_root: Path, engine) -> str:
    from agp_cockpit.core.start_request import resolve_task_binding

    mission = engine.runtime.state
    binding = resolve_task_binding(runtime_root, None if mission is None else mission.mission_id)
    return str(binding.get("task_id") or "").strip()


def _remote_effects_permitted(runtime_root: Path, engine, wanted) -> bool:
    """AGP_HUMAN_DECISION_V1 + AGP_CI_GREEN_COMPLETION_V1: the open approval
    of the bound task covers exactly these remote-effect commands."""
    from agp_cockpit.core.ci_gate import CiGateStore
    from agp_cockpit.core.human_decision import HumanDecisionStore

    if _approval_grant(runtime_root, engine) is None:
        return False
    task_id = _current_task_id(runtime_root, engine)
    return HumanDecisionStore(runtime_root).permits(
        task_id, wanted, ci_gate_active=CiGateStore(runtime_root).required(task_id)
    )


def _runtime_identity_payload() -> dict[str, str | int]:
    payload: dict[str, str | int] = {
        "application_version": __version__,
        "bridge_build_id": BRIDGE_BUILD_ID,
        "bridge_protocol_version": BRIDGE_PROTOCOL_VERSION,
        "extension_expected_version": "",
        "extension_expected_build_id": "",
    }
    try:
        staged = local_extension_root()
        payload["extension_expected_version"] = _manifest_version(staged)
        payload["extension_expected_build_id"] = _manifest_build_id(staged)
    except Exception as exc:  # noqa: BLE001 - status remains useful while staging is repaired.
        payload["extension_identity_error"] = (
            f"{type(exc).__name__}: {str(exc)[:240]}"
        )
    return payload


class CockpitBridgeServer:
    def __init__(
        self,
        repository_root: Path,
        *,
        config: BridgeServerConfig | None = None,
        runtime_root: Path | None = None,
        local_task_contract: LocalTaskContract | None = None,
    ) -> None:
        cfg = config or BridgeServerConfig(
            token=secrets.token_urlsafe(24)
        )

        if cfg.host not in {"127.0.0.1", "localhost"}:
            raise ValueError("bridge must bind to localhost only")
        if not cfg.token:
            raise ValueError("bridge token must not be empty")

        self.repository_root = repository_root.resolve()
        self.config = cfg
        self.runtime_root = (runtime_root.expanduser().resolve() if runtime_root is not None else runtime_dir(self.repository_root, "bridge"))
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._run_next_controller = RunNextProcessController()
        self.engine = BridgeEngine(self.repository_root)
        self.engine.runtime.bind_execution_stop(self._run_next_controller.stop)
        self.diag = DiagnosticLogger(self.repository_root)
        self.protocol_v1_actions = ActionRegistry()
        self.protocol_v1_results: dict[str, str] = {}
        self._durable_db_path = self.runtime_root / "protocol-v1-actions.sqlite3"
        self.local_task_contract = local_task_contract
        self._durable_controllers: dict[str, DurableTaskController] = {}
        self._file_loop_lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def _durable_controller(self, session_id: str) -> DurableTaskController:
        controller = self._durable_controllers.get(session_id)
        if controller is None:
            # Protocol session is transport identity; prefer current task-first identity.
            task_id = f"protocol-v1-http:{session_id}"
            try:
                from agp_cockpit.core.start_request import StartRequestStore
                current = StartRequestStore(self.runtime_root).current()
                requested = str(current.get("task_id") or "").strip()
                if requested:
                    task_id = requested
            except Exception:  # noqa: BLE001 - stale optional task identity is recoverable.
                task_id = f"protocol-v1-http:{session_id}"
            controller = DurableTaskController(
                task_id, self._durable_db_path, local_contract=self.local_task_contract,
            )
            self._durable_controllers[session_id] = controller
        return controller

    def start(self) -> None:
        if self._server is not None:
            return

        # A desktop start request is a one-shot signal for the current bridge
        # lifetime. Never replay a request left behind by a previous process.
        from agp_cockpit.core.start_request import StartRequestStore
        StartRequestStore(self.runtime_root).invalidate_pending()

        engine = self.engine
        token = self.config.token
        diag = self.diag
        repo_root = self.repository_root
        protocol_v1_actions = self.protocol_v1_actions
        protocol_v1_results = self.protocol_v1_results
        task_db_path = self.runtime_root / "tasks.sqlite3"
        durable_controller_for = self._durable_controller
        runtime_root = self.runtime_root
        local_task_contract = self.local_task_contract
        file_loop_lock = self._file_loop_lock
        run_next_controller = self._run_next_controller

        class Handler(BaseHTTPRequestHandler):
            def _cors(self) -> None:
                self.send_header(
                    "Access-Control-Allow-Origin",
                    "https://chatgpt.com",
                )
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Content-Type, X-AGP-Token",
                )
                self.send_header(
                    "Access-Control-Allow-Methods",
                    "GET, POST, OPTIONS",
                )

            def _json(self, status: int, data: dict) -> None:
                payload = json.dumps(
                    data,
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(status)
                self._cors()
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(payload)),
                )
                self.end_headers()
                self.wfile.write(payload)

            def _authorized(self) -> bool:
                return (
                    self.headers.get("X-AGP-Token", "")
                    == token
                )

            def _body(self) -> dict:
                length = int(
                    self.headers.get("Content-Length", "0")
                )
                if length <= 0 or length > 2_000_000:
                    raise ValueError("invalid Content-Length")
                raw = self.rfile.read(length).decode("utf-8")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise TypeError("request body must be object")
                return data

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self._cors()
                self.end_headers()

            def do_GET(self) -> None:
                path = urlparse(self.path).path

                if not self._authorized():
                    diag.event(
                        "HTTP_AUTH_FAILED",
                        component="http",
                        details={"method": "GET", "path": path},
                    )
                    self._json(403, {"error": "forbidden"})
                    return

                if path == "/v1/task/status":
                    from urllib.parse import parse_qs
                    query = parse_qs(urlparse(self.path).query)
                    session_id = str((query.get("session_id") or [""])[0]).strip()
                    if not session_id:
                        raise ValueError("session_id required")
                    durable = durable_controller_for(session_id)
                    self._json(200, {"authority":"DurableTaskController","session_id":session_id,"task":durable.snapshot,"control":durable.control_snapshot})
                    return

                if path == "/v1/file-loop/control":
                    from agp_cockpit.core.operator_control import OperatorControlStore
                    self._json(200, OperatorControlStore(runtime_root).current())
                    return

                if path == "/v1/task/start-request":
                    from agp_cockpit.core.start_request import StartRequestStore
                    request = StartRequestStore(runtime_root).pending()
                    # AGP_EXTENSION_AUTO_REFRESH_V2: polled every second while idle,
                    # so an outdated extension notices the new app within seconds.
                    request = {**request, "extension_expected_build_id": str(
                        _runtime_identity_payload().get("extension_expected_build_id") or BRIDGE_BUILD_ID)}
                    state = engine.runtime.state
                    diag.event("TASK_START_REQUEST_POLLED", mission_id=(None if state is None else state.mission_id), state_after=("IDLE" if state is None else state.state), component="http", details={"generation": request.get("generation"), "request_mission_id": request.get("mission_id"), "request_task_id": request.get("task_id")})
                    self._json(200, request)
                    return

                if path == "/v1/status":
                    state = engine.runtime.state
                    approval_grant = _approval_grant(runtime_root, engine)
                    diag.event(
                        "STATUS_REQUEST",
                        mission_id=(
                            None if state is None else state.mission_id
                        ),
                        state_after=(
                            "IDLE" if state is None else state.state
                        ),
                        component="http",
                    )
                    self._json(
                        200,
                        {
                            **_runtime_identity_payload(),
                            "diagnostics_log_path": str(diag.log_path),
                            "repository_root": str(repo_root),
                            **_kit_command_digest(repo_root),
                            "runtime_root": str(runtime_root),
                            "next_local_step": (
                                next_step_number(repo_root / "Download")
                                if (repo_root / "Download").is_dir()
                                else 1
                            ),
                            "state": (
                                "IDLE"
                                if state is None
                                else state.state
                            ),
                            "mission": (
                                None
                                if state is None
                                else asdict(state)
                            ),
                            "local_authority": (
                                None
                                if local_task_contract is None
                                else {
                                    "repository_root": str(local_task_contract.repository_root),
                                    "allowed_effects": sorted(local_task_contract.allowed_effects),
                                    "allowed_tools": sorted(local_task_contract.allowed_tools),
                                    # AGP_HUMAN_APPROVAL_SCOPE_V2: an open approval
                                    # widens the authority for exactly its one
                                    # work order (consumed on use).
                                    "allow_network": bool(local_task_contract.allow_network)
                                    or approval_grant is not None,
                                    **(
                                        {}
                                        if approval_grant is None
                                        else {"human_approval": {
                                            "scope": (
                                                "the remote-effect Kit commands of this standard task: "
                                                + ", ".join(approval_grant["scope"])
                                                if approval_grant.get("scope")
                                                else "exactly one work order with a remote-effect Kit command"
                                            ),
                                            "approved_question": approval_grant["question"],
                                        }}
                                    ),
                                }
                            ),
                        },
                    )
                    return

                if path == "/v1/diagnostics":
                    self._json(
                        200,
                        {
                            "log_path": str(diag.log_path),
                            "max_bytes": diag.config.max_bytes,
                            "backup_count": diag.config.backup_count,
                        },
                    )
                    return

                self._json(404, {"error": "not found"})

            def do_POST(self) -> None:
                path = urlparse(self.path).path

                if not self._authorized():
                    diag.event(
                        "HTTP_AUTH_FAILED",
                        component="http",
                        details={"method": "POST", "path": path},
                    )
                    self._json(403, {"error": "forbidden"})
                    return

                file_loop_locked = path in {
                    "/v1/file-loop/command",
                    "/v1/file-loop/result-delivered",
                    "/v1/file-loop/delivery-ack",
                    "/v1/file-loop/terminal",
                }
                if file_loop_locked:
                    file_loop_lock.acquire()
                try:
                    # AGP_K07_COMMAND_FILE_HTTP_989
                    if path == "/v1/file-loop/command":
                        length = int(self.headers.get("Content-Length", "0"))
                        if length <= 0 or length > 2_100_000:
                            raise ValueError("invalid Content-Length")
                        raw = self.rfile.read(length).decode("utf-8")
                        data = json.loads(raw)
                        if not isinstance(data, dict):
                            raise ValueError("command-file request must be an object")
                        filename = str(data.get("filename", "")).strip()
                        content = data.get("content")
                        # K07 observational correlation only. This does not
                        # create execution, transport, or task-state authority.
                        import hashlib as _k07_cycle_hash
                        cycle_id = "k07-" + _k07_cycle_hash.sha256(
                            (filename + "\0" + (content if isinstance(content, str) else "")).encode("utf-8")
                        ).hexdigest()[:20]
                        if (
                            not filename
                            or not filename.lower().endswith(".py")
                            or "/" in filename
                            or "\\" in filename
                        ):
                            raise ValueError("exactly one safe .py filename required")
                        if not isinstance(content, str) or not content or len(content) > 2_000_000:
                            raise ValueError("bounded Python command content required")
                        from agp_cockpit.core.kit_command_catalog import (
                            KitCommandCatalog,
                            approval_required_commands,
                            destructive_execute_commands,
                            unknown_effect_commands,
                        )
                        # AGP_DESTRUCTIVE_EXECUTE_GATE_V1: remote effects and
                        # destructive local executes share the approval path.
                        wanted = approval_required_commands(content, KitCommandCatalog.load(repo_root))
                        remote_effects_allowed = bool(wanted) and _remote_effects_permitted(
                            runtime_root, engine, wanted
                        )
                        # AGP_REMOTE_EFFECT_ASKS_HUMAN_V1 (live 1495/1496): a
                        # remote-effect work order without an open approval is
                        # not a technical failure but a decision. When it is
                        # otherwise valid it ends the mission with NEEDS_HUMAN
                        # and is not executed; the human answers in the app.
                        mission_now = engine.runtime.state
                        # AGP_STANDARD_TASK_ORCHESTRATOR_V1 (R2)
                        standard_task = mission_now is not None and str(
                            mission_now.title or ""
                        ).startswith("Standard · ")
                        try:
                            validate_command_content(
                                content, filename=filename, repository_root=repo_root,
                                allow_remote_effects=True, require_orchestrator=standard_task,
                            )
                            # AGP_FINISH_PUBLISHES_ONLY_V1 (PR #272, step 1839): „Abschließen“
                            # publishes; it never repairs code or tests.
                            from agp_cockpit.core import finish_guard
                            if mission_now is not None and finish_guard.is_finish_mission(mission_now.title):
                                from agp_cockpit.core.kit_command_catalog import (
                                    kit_commands_used,
                                )
                                used_names = [str(c.get("qualified_name") or "") for c in
                                              kit_commands_used(content, KitCommandCatalog.load(repo_root))]
                                start = finish_guard.start_state(runtime_root, mission_now.mission_id, repo_root)
                                problems = finish_guard.violations(content, start, used_names)
                                if problems:
                                    raise ValueError("command-file semantic contract rejected: " + "; ".join(problems))
                        except ValueError as rejection:
                            # AGP_CORRECTABLE_REJECTION_V1: a work order that breaks the
                            # command authority is not executed; the remote side gets
                            # the violations and the next step number (bounded).
                            if mission_now is None or not _correctable(rejection):
                                raise
                            self._json(200, _policy_rejection_response(
                                runtime_root, repo_root, engine, diag,
                                filename=filename, reason=str(rejection), cycle_id=cycle_id,
                                content=content,
                            ))
                            return
                        if not remote_effects_allowed and wanted:
                            unknown = unknown_effect_commands(content, KitCommandCatalog.load(repo_root))
                            destructive = destructive_execute_commands(content, KitCommandCatalog.load(repo_root))
                            question = (
                                f"Arbeitsauftrag {filename} will "
                                + ("einen Schritt, der den lokalen Verlauf oder lokale Dateien verändert "
                                   f"({', '.join(destructive)}; die Kit-Route sichert vorher alles auf einem "
                                   "Rescue-Branch bzw. prüft die Signatur des Probelaufs), "
                                   if destructive else "")
                                + ("eine Wirkung nach außen "
                                   if set(wanted) - set(destructive) else "")
                                + (f"oder eine noch nicht eingestufte Wirkung ({', '.join(unknown)}) "
                                   if unknown else "")
                                + f"ausführen: {', '.join(wanted)}. Es liegt keine offene "
                                "Freigabe vor (keine erteilt, oder die letzte wurde von "
                                "einem früheren Auftrag verbraucht). Der Auftrag wurde "
                                "nicht ausgeführt. Darf er ausgeführt werden?"
                            )
                            mission = engine.runtime.state
                            if mission is not None and mission.state not in _MISSION_ENDED_STATES:
                                engine.runtime.final("NEEDS_HUMAN", question)
                            # A NEEDS_HUMAN ends the mission: an unused
                            # approval of this mission expires with it.
                            _approval_grant(runtime_root, engine)
                            diag.event(
                                "REMOTE_EFFECT_APPROVAL_REQUESTED",
                                component="file-loop",
                                details={"filename": filename, "commands": wanted,
                                         "cycle_id": cycle_id},
                            )
                            self._json(200, {
                                "state": "NEEDS_HUMAN",
                                "step": None,
                                "result_file": None,
                                "prompt": None,
                                "terminal": True,
                                "human_reason": question,
                                "cycle_id": cycle_id,
                                "replayed": False,
                            })
                            return
                        # AGP_K07_DOWNLOAD_PROVENANCE_V1: when the browser
                        # materialized the payload through /download, the
                        # submitted content must be byte-identical to it.
                        download_sha256 = str(data.get("download_sha256") or "").strip()
                        if download_sha256 and download_sha256 != _k07_cycle_hash.sha256(
                            content.encode("utf-8")
                        ).hexdigest():
                            raise ValueError("command content does not match the materialized browser download")

                        from agp_cockpit.core.operator_control import (
                            OperatorControlStore,
                        )
                        operator_action = str(
                            OperatorControlStore(runtime_root).current().get("action") or ""
                        ).upper()
                        if operator_action in {"PAUSE", "STOP"}:
                            raise RuntimeError(
                                f"file-loop admission blocked by operator control: {operator_action}"
                            )

                        from agp_cockpit.core.start_request import resolve_task_binding
                        current_start = resolve_task_binding(
                            runtime_root,
                            None if engine.runtime.state is None else engine.runtime.state.mission_id,
                        )
                        current_task_id = str(current_start.get("task_id") or "").strip()
                        handoff_contract = False
                        if current_task_id:
                            durable = DurableTaskController(current_task_id, task_db_path)
                            try:
                                if durable.snapshot.get("suspension_reason") == "WAITING_FOR_HUMAN":
                                    raise RuntimeError("WAITING_FOR_HUMAN")
                                handoff_contract = contract_enabled(durable)
                                if handoff_contract and durable.snapshot["state"] == "VERIFIED_COMPLETE":
                                    raise ValueError("handoff task is already complete; no further command permitted")
                            finally:
                                durable.close()

                        incoming_root = runtime_root / "file-loop-incoming"
                        incoming_root.mkdir(parents=True, exist_ok=True)
                        incoming = incoming_root / filename
                        incoming.write_text(content, encoding="utf-8")
                        diag.event(
                            "K07_COMMAND_ACCEPTED",
                            component="file-loop",
                            details={
                                "cycle_id": cycle_id,
                                "filename": filename,
                                "command_sha256": _k07_cycle_hash.sha256(content.encode("utf-8")).hexdigest(),
                                "task_id": current_task_id or None,
                            },
                        )

                        state_file = runtime_root / "file-loop-state.json"
                        handoff_before = package_snapshot(repo_root) if handoff_contract else {}
                        # AGP_CI_LIFECYCLE_COMPLETION_V2: the local work a publishing
                        # run starts from; a merged PR must contain it.
                        pre_run_work = None
                        pre_run_refs = None
                        if wanted:
                            from agp_cockpit.core import ci_gate as _ci_pre
                            pre_run_work = (
                                _ci_pre.git_value(repo_root, "branch", "--show-current"),
                                _ci_pre.git_value(repo_root, "rev-parse", "HEAD"),
                            )
                            # AGP_EFFECT_REFUND_V1
                            pre_run_refs = _ci_pre.remote_refs(repo_root)
                        outcome = consume_command_file(
                            incoming,
                            repo_root,
                            state_file,
                            stem=Path(filename).stem,
                            mission_id=(
                                None
                                if engine.runtime.state is None
                                else engine.runtime.state.mission_id
                            ),
                            guard=engine.guard,
                            process_controller=run_next_controller,
                            # AGP_TASK_REPLY_POLICY_V1: a locally verified task
                            # is never offered a remote DONE.
                            reply_policy=policy_for(handoff_contract),
                        )
                        terminal_loop = outcome.state.value in {"BLOCKED", "NEEDS_HUMAN", "DONE"}
                        # AGP_K07_POST_EXECUTION_OPERATOR_CONTROL_V1: STOP or
                        # PAUSE requested while run_next was executing must
                        # suppress the outgoing continuation. The result stays
                        # PENDING (PAUSE: re-delivered on resume via replay) or
                        # WITHHELD (STOP).
                        post_operator_action = str(
                            OperatorControlStore(runtime_root).current().get("action") or ""
                        ).upper()
                        held_by_operator = (
                            outcome.run is not None
                            and not terminal_loop
                            and post_operator_action in {"PAUSE", "STOP"}
                        )
                        if outcome.run is None and terminal_loop:
                            if outcome.state.value == "BLOCKED" and engine.runtime.state is not None:
                                engine.runtime.final("BLOCKED", outcome.human_reason or "file-loop guard blocked")
                            self._json(
                                200,
                                {
                                    "state": outcome.state.value,
                                    "step": None,
                                    "result_file": None,
                                    "prompt": None,
                                    "terminal": True,
                                    "human_reason": outcome.human_reason,
                                    "cycle_id": cycle_id,
                                    "replayed": outcome.replayed,
                                },
                            )
                            return
                        if outcome.run is None or (outcome.continuation_text is None and not terminal_loop):
                            raise RuntimeError("command-file execution produced no return bundle")
                        if not outcome.replayed and engine.runtime.state is not None:
                            engine.runtime.record_assistant(content)
                            engine.runtime.record_local_step()
                        # AGP_HUMAN_DECISION_V1: an executed remote-effect work
                        # order consumes the one-shot approval.
                        if not outcome.replayed and outcome.run is not None and remote_effects_allowed:
                            from agp_cockpit.core.human_decision import (
                                HumanDecisionStore,
                            )
                            from agp_cockpit.core.kit_command_catalog import (
                                KitCommandCatalog,
                                approval_required_commands,
                                destructive_execute_commands,
                            )
                            used = approval_required_commands(content, KitCommandCatalog.load(repo_root))
                            # AGP_EFFECT_REFUND_V1: nothing changed on origin -> the
                            # run had no remote effect (e.g. blocked by a Kit gate);
                            # the approval budget is kept. Unreadable refs consume.
                            # AGP_DESTRUCTIVE_EXECUTE_GATE_V1: a destructive local
                            # execute always consumes (origin never shows its effect).
                            unchanged_remote = False
                            if used and pre_run_refs is not None and not destructive_execute_commands(
                                content, KitCommandCatalog.load(repo_root)
                            ):
                                from agp_cockpit.core.ci_gate import (
                                    remote_refs as _refs_after,
                                )
                                unchanged_remote = _refs_after(repo_root) == pre_run_refs
                            if used and unchanged_remote:
                                diag.event(
                                    "HUMAN_APPROVAL_NOT_CONSUMED",
                                    component="file-loop",
                                    details={"task_id": current_task_id, "commands": used,
                                             "reason": "no ref of origin changed", "cycle_id": cycle_id},
                                )
                            if used and not unchanged_remote:
                                HumanDecisionStore(runtime_root).consume(
                                    current_task_id,
                                    _k07_cycle_hash.sha256(content.encode("utf-8")).hexdigest(),
                                    used,
                                    step=outcome.run.step,
                                )
                                # AGP_CI_GREEN_COMPLETION_V1: a task that published
                                # work is complete only when GitHub is verified green
                                # (after a merging command: the merged lifecycle).
                                from agp_cockpit.core import ci_gate as _ci_gate
                                if set(used) & _ci_gate.PUBLISHING_COMMANDS and current_task_id:
                                    gate = _ci_gate.CiGateStore(runtime_root)
                                    gate.activate(
                                        current_task_id,
                                        reason=_k07_cycle_hash.sha256(content.encode("utf-8")).hexdigest(),
                                        merge=_ci_gate.merge_expected(used, content),
                                    )
                                    if pre_run_work and pre_run_work[0] not in {"", "main"} and pre_run_work[1]:
                                        gate._update(current_task_id, work_branch=pre_run_work[0],
                                                     work_head=pre_run_work[1])
                                diag.event(
                                    "HUMAN_APPROVAL_CONSUMED",
                                    component="file-loop",
                                    details={"task_id": current_task_id, "commands": used, "cycle_id": cycle_id},
                                )
                        if terminal_loop and outcome.state.value == "BLOCKED" and engine.runtime.state is not None:
                            engine.runtime.final(
                                "BLOCKED",
                                outcome.human_reason or "file-loop reached a terminal blocked state",
                            )
                        result_path = Path(outcome.run.return_bundle)
                        result_sha256 = _k07_cycle_hash.sha256(result_path.read_bytes()).hexdigest()
                        output_path = Path(outcome.run.run_next_output)
                        output_sha256 = _k07_cycle_hash.sha256(output_path.read_bytes()).hexdigest()
                        completion_pending = False
                        if held_by_operator:
                            if post_operator_action == "STOP":
                                withhold_result_delivery(state_file, result_sha256)
                            diag.event(
                                "K07_RESULT_DELIVERY_HELD",
                                component="file-loop",
                                details={
                                    "cycle_id": cycle_id,
                                    "step": outcome.run.step,
                                    "operator_action": post_operator_action,
                                    "result_sha256": result_sha256,
                                },
                            )
                            self._json(
                                200,
                                {
                                    "state": "STOPPED" if post_operator_action == "STOP" else outcome.state.value,
                                    "step": outcome.run.step,
                                    "result_file": str(outcome.run.return_bundle),
                                    "prompt": None,
                                    "terminal": post_operator_action == "STOP",
                                    "held": post_operator_action == "PAUSE",
                                    "delivery_pending": post_operator_action == "PAUSE",
                                    "human_reason": (
                                        f"operator {post_operator_action} during local execution; "
                                        "result retained locally and not delivered"
                                    ),
                                    "cycle_id": cycle_id,
                                    "result_sha256": result_sha256,
                                    "replayed": outcome.replayed,
                                },
                            )
                            return
                        if (
                            handoff_contract
                            and outcome.replayed
                            and outcome.delivery_pending
                            and (runtime_root / "handoff-completion.json").is_file()
                        ):
                            receipt = json.loads(
                                (runtime_root / "handoff-completion.json").read_text(encoding="utf-8")
                            )
                            completion_pending = (
                                receipt.get("cycle_id") == cycle_id
                                and receipt.get("result_sha256") == result_sha256
                                and receipt.get("delivered") is False
                            )
                        if handoff_contract and not outcome.replayed and not terminal_loop:
                            mission = engine.runtime.state
                            if mission is None or current_start.get("mission_id") != mission.mission_id:
                                raise ValueError("handoff task does not match active mission")
                            completion_pending = prepare_receipt(
                                repo_root, runtime_root, mission_id=mission.mission_id,
                                task_id=current_task_id, cycle_id=cycle_id,
                                run=outcome.run, before=handoff_before,
                            ) is not None
                        try:
                            parsed_result = json.loads(result_path.read_text(encoding="utf-8"))
                            result_validation = {"valid": isinstance(parsed_result, dict), "error": None if isinstance(parsed_result, dict) else "result artifact must be a JSON object"}
                        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                            result_validation = {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
                        diag.event(
                            "K07_RESULT_BUNDLE_CREATED",
                            component="file-loop",
                            details={
                                "cycle_id": cycle_id,
                                "task_id": current_task_id or None,
                                "step": outcome.run.step,
                                "result_file": str(result_path),
                                "result_sha256": result_sha256,
                                "output_file": str(output_path),
                                "output_sha256": output_sha256,
                                "artifact_kind": outcome.run.artifact_kind,
                                "result_validation": result_validation,
                            },
                        )
                        # AGP_RESULT_PROJECTION_V1: attach deterministic projections;
                        # the full files stay local and keep identifying the result.
                        try:
                            delivery = result_projection.delivery_files(repo_root, result_path, output_path)
                        except (OSError, ValueError) as exc:
                            delivery = {"result_file": str(result_path), "output_file": str(output_path),
                                        "error": f"{type(exc).__name__}: {exc}"}
                        diag.event(
                            "K07_RESULT_PROJECTED",
                            component="file-loop",
                            details={"cycle_id": cycle_id, "step": outcome.run.step,
                                     "bytes_before": delivery.get("bytes_before"),
                                     "bytes_after": delivery.get("bytes_after"),
                                     "projected": delivery.get("projected"),
                                     "error": delivery.get("error")},
                        )
                        self._json(
                            200,
                            {
                                "state": outcome.state.value,
                                "step": outcome.run.step,
                                "next_step": next_step_number(
                                    repo_root / "Download",
                                    minimum_step=outcome.run.step,
                                ),
                                "result_file": delivery["result_file"],
                                "prompt": FINAL_RECEIPT_PROMPT if completion_pending else outcome.continuation_text,
                                "completion_pending": completion_pending,
                                "terminal": terminal_loop,
                                "human_reason": outcome.human_reason,
                                "cycle_id": cycle_id,
                                "result_sha256": result_sha256,
                                "output_file": delivery["output_file"],
                                "output_sha256": output_sha256,
                                "artifact_kind": outcome.run.artifact_kind,
                                "result_validation": result_validation,
                                "result_status": parsed_result.get("status") if isinstance(parsed_result, dict) else None,
                                "result_execution": parsed_result.get("execution") if isinstance(parsed_result, dict) else None,
                                "failure_reason": parsed_result.get("failure_reason") if isinstance(parsed_result, dict) else None,
                                "replayed": outcome.replayed,
                                "delivery_pending": bool(outcome.delivery_pending and not terminal_loop),
                            },
                        )
                        return

                    # AGP_K07_TERMINAL_REPLY_FILE_V1 (D4): a terminal remote
                    # answer is a step-scoped JSON file, never visible prose.
                    if path == "/v1/file-loop/terminal":
                        data = self._body()
                        filename = str(data.get("filename") or "").strip()
                        content = data.get("content")
                        try:
                            reply = parse_terminal_reply(filename, content)
                        except ValueError as rejection:
                            # AGP_TERMINAL_REPLY_CORRECTION_V1: a malformed terminal reply of a
                            # running mission is corrected (bounded), not a stop.
                            mission_now = engine.runtime.state
                            if (mission_now is None or mission_now.state in _MISSION_ENDED_STATES
                                    or not is_terminal_filename(filename)
                                    or not isinstance(content, str) or not content.strip()):
                                raise
                            self._json(200, _policy_rejection_response(
                                runtime_root, repo_root, engine, diag, filename=filename,
                                reason=str(rejection), cycle_id=str(data.get("cycle_id") or ""),
                                terminal=True, content=content,
                            ))
                            return
                        download_sha256 = str(data.get("download_sha256") or "").strip()
                        if download_sha256 and download_sha256 != reply.sha256:
                            raise ValueError("terminal reply does not match the materialized browser download")
                        from agp_cockpit.core.operator_control import (
                            OperatorControlStore,
                        )
                        operator_action = str(
                            OperatorControlStore(runtime_root).current().get("action") or ""
                        ).upper()
                        if operator_action in {"PAUSE", "STOP"}:
                            raise RuntimeError(
                                f"terminal reply blocked by operator control: {operator_action}"
                            )
                        download_dir = repo_root / "Download"
                        replayed = record_terminal_reply(
                            download_dir, reply, content, next_step_number(download_dir)
                        )
                        from agp_cockpit.core.start_request import resolve_task_binding
                        mission = engine.runtime.state
                        binding = resolve_task_binding(
                            runtime_root, None if mission is None else mission.mission_id
                        )
                        task_id = str(binding.get("task_id") or "").strip()
                        contract_pending = False
                        if task_id:
                            durable = DurableTaskController(task_id, task_db_path)
                            try:
                                contract_pending = (
                                    contract_enabled(durable)
                                    and durable.snapshot["state"] != "VERIFIED_COMPLETE"
                                )
                            finally:
                                durable.close()
                        state = reply.state
                        authority = "remote-declared"
                        human_reason = reply.reason
                        if state == "DONE" and contract_pending:
                            # Remote DONE is only a request. A task with a local
                            # completion contract is complete only by local
                            # verification, which has not happened.
                            state = "NEEDS_HUMAN"
                            authority = "completion-contract-rejected"
                            human_reason = (
                                "Remote meldet DONE ohne lokal verifizierten Abschluss: " + reply.reason
                            )
                        # AGP_CI_GREEN_COMPLETION_V1: once the task pushed, DONE
                        # needs green CI for the local HEAD, checked here with the
                        # Kit. Red or unfinished CI rejects the DONE and continues
                        # the task with the finding (bounded by ci_gate limits).
                        if state == "DONE" and task_id:
                            from agp_cockpit.core import ci_gate
                            gate = ci_gate.CiGateStore(runtime_root)
                            if gate.required(task_id):
                                gate_entry = gate.get(task_id)
                                ci_head = ci_gate.git_value(repo_root, "rev-parse", "HEAD")
                                ci_branch = ci_gate.git_value(repo_root, "branch", "--show-current")
                                ci_pr = reply.pr or gate_entry.get("pr")
                                ci_decision: dict = {}
                                ci_facts: dict = {}
                                if not ci_pr:
                                    verdict = ci_gate.CiVerdict(
                                        "no-pr", "no pull request was named for the published work"
                                    )
                                else:
                                    ci_decision = ci_gate.run_pr_status(
                                        repo_root, engine.kit_binary, int(ci_pr)
                                    )
                                    if (gate_entry.get("merge_expected")
                                            or str(ci_decision.get("state") or "") == "MERGED"):
                                        # AGP_CI_LIFECYCLE_COMPLETION_V2
                                        verdict, ci_facts = ci_gate.verify_merged(
                                            repo_root, engine.kit_binary, pr_decision=ci_decision,
                                            work_head=str(gate_entry.get("work_head") or ""),
                                        )
                                    else:
                                        verdict = ci_gate.evaluate(ci_decision, head=ci_head)
                                gate_entry = gate.record_check(
                                    task_id, head=ci_head, pr=ci_pr, verdict=verdict.kind
                                )
                                evidence = ci_gate.write_evidence(
                                    repo_root, head=ci_head, pr=ci_pr, decision=ci_decision,
                                    verdict=verdict, facts=ci_facts,
                                )
                                diag.event(
                                    "CI_GATE_CHECKED",
                                    component="task",
                                    details={"task_id": task_id, "pr": ci_pr, "head": ci_head,
                                             "verdict": verdict.kind, "summary": verdict.summary[:300],
                                             "evidence": str(evidence),
                                             "red_heads": len(gate_entry.get("red_heads") or []),
                                             "checks": gate_entry.get("checks")},
                                )
                                exhausted = (
                                    len(gate_entry.get("red_heads") or []) > ci_gate.MAX_RED_HEADS
                                    or int(gate_entry.get("checks") or 0) > ci_gate.MAX_CHECKS
                                )
                                if verdict.kind == "green":
                                    authority = "ci-verified"
                                    merged = bool(ci_facts)
                                    human_reason = (
                                        f"CI grün geprüft (PR #{ci_pr} "
                                        + ("gemergt, main " if merged else "")
                                        + f"{ci_head[:12]}) · {reply.reason}"
                                    )
                                elif verdict.kind == "blocked" or exhausted:
                                    state = "NEEDS_HUMAN"
                                    authority = "ci-gate-exhausted" if exhausted else "ci-gate-blocked"
                                    human_reason = (
                                        "Remote meldet DONE, die CI ist nicht grün"
                                        + (" (Reparaturversuche erschöpft)" if exhausted else "")
                                        + f": {verdict.summary}. Nachweis: {evidence.name}"
                                    )
                                else:
                                    continuation = ci_gate.continuation_prompt(
                                        verdict, pr=ci_pr, head=ci_head, branch=ci_branch,
                                        next_step=next_step_number(download_dir), entry=gate_entry,
                                    )
                                    rejected_reason = "Abschluss abgelehnt — " + verdict.summary
                                    diag.event(
                                        "K07_TERMINAL_REPLY_CONTINUED",
                                        component="file-loop",
                                        details={"filename": reply.filename, "verdict": verdict.kind,
                                                 "next_step": next_step_number(download_dir)},
                                    )
                                    self._json(200, {
                                        "state": "CONTINUE",
                                        "remote_state": reply.state,
                                        "terminal": False,
                                        "step": reply.step,
                                        "next_step": next_step_number(download_dir),
                                        "prompt": continuation,
                                        "human_reason": rejected_reason,
                                        "authority": "ci-gate",
                                        "replayed": replayed,
                                    })
                                    return
                        # AGP_STANDARD_VERIFIER_V1 (plan P5): a standard task with a
                        # local verifier is DONE only when the verifier passes.
                        # AGP_RELEASE_VERIFIER_V1 (P11): a verifier contract also runs after a
                        # CI-verified merge (Release: the tag comes after the merge).
                        if state == "DONE" and task_id:
                            from agp_cockpit.core import standard_verifier as _sv
                            durable = DurableTaskController(task_id, task_db_path)
                            try:
                                verifier_contract = _sv.contract_of(durable.store, task_id)
                            finally:
                                durable.close()
                            if verifier_contract is not None:
                                verified, finding = _sv.verify(repo_root, verifier_contract)
                                diag.event(
                                    "STANDARD_VERIFIER_CHECKED",
                                    component="task",
                                    details={"task_id": task_id,
                                             "verifier": verifier_contract.get("verifier"),
                                             "passed": verified, "finding": finding[:300]},
                                )
                                if verified and authority == "ci-verified":
                                    human_reason = f"{human_reason} · Lokal geprüft ({finding})"
                                elif verified:
                                    authority = "verifier-checked"
                                    human_reason = f"Lokal geprüft ({finding}) · {reply.reason}"
                                else:
                                    checks = _sv.VerifierChecks(runtime_root).bump(task_id)
                                    if checks > _sv.MAX_CHECKS:
                                        state = "NEEDS_HUMAN"
                                        authority = "standard-verifier-exhausted"
                                        human_reason = (f"Remote meldet DONE, die lokale Prüfung schlägt "
                                                        f"fehl ({checks}×): {finding}")
                                    else:
                                        next_local = next_step_number(download_dir)
                                        self._json(200, {
                                            "state": "CONTINUE",
                                            "remote_state": reply.state,
                                            "terminal": False,
                                            "step": reply.step,
                                            "next_step": next_local,
                                            "prompt": (
                                                "AGP COCKPIT — DONE NOT ACCEPTED\n\n"
                                                "The local verifier of this standard task rejected DONE "
                                                f"(attempt {checks} of {_sv.MAX_CHECKS}): {finding}.\n"
                                                "Continue the task with a new work order (expected local "
                                                f"step {next_local}), or NEEDS_HUMAN if a human decision "
                                                "is required.\n" + WORK_ORDER_KIT_RULE
                                            ),
                                            "human_reason": "Abschluss abgelehnt — " + finding,
                                            "authority": "standard-verifier",
                                            "replayed": replayed,
                                        })
                                        return
                        if mission is not None and mission.state not in {
                            "DONE", "NEEDS_HUMAN", "BLOCKED", "FAILED", "STOPPED"
                        }:
                            engine.runtime.final(state, human_reason)
                        _approval_grant(runtime_root, engine)  # expires an unused approval
                        task_state_after = None
                        if state == "DONE" and task_id:
                            durable = DurableTaskController(task_id, task_db_path)
                            try:
                                task_state_after = durable.store.close_after_done(
                                    task_id, verified=authority in {"ci-verified", "verifier-checked"}
                                )
                            finally:
                                durable.close()
                        diag.event(
                            "K07_TERMINAL_REPLY_ACCEPTED",
                            component="file-loop",
                            details={
                                "filename": reply.filename,
                                "step": reply.step,
                                "remote_state": reply.state,
                                "state": state,
                                "authority": authority,
                                "task_state": task_state_after,
                                "sha256": reply.sha256,
                                "replayed": replayed,
                                "cycle_id": str(data.get("cycle_id") or "")[:40],
                            },
                        )
                        self._json(
                            200,
                            {
                                "state": state,
                                "remote_state": reply.state,
                                "terminal": True,
                                "step": reply.step,
                                "human_reason": human_reason,
                                "authority": authority,
                                "replayed": replayed,
                                "sha256": reply.sha256,
                                "mission_state": None if engine.runtime.state is None else engine.runtime.state.state,
                            },
                        )
                        return

                    if path == "/v1/file-loop/result-delivered":
                        from agp_cockpit.core.operator_control import (
                            OperatorControlStore,
                        )
                        from agp_cockpit.core.start_request import resolve_task_binding

                        data = self._body()
                        mission = engine.runtime.state
                        start = resolve_task_binding(
                            runtime_root, None if mission is None else mission.mission_id
                        )
                        if (mission is None or start.get("mission_id") != mission.mission_id
                                or mission.state in {"STOPPED", "BLOCKED", "FAILED", "NEEDS_HUMAN"}
                                or OperatorControlStore(runtime_root).current().get("action") in {"STOP", "PAUSE"}):
                            raise ValueError("no active mission for handoff receipt")
                        durable = DurableTaskController(str(start.get("task_id") or ""), task_db_path)
                        def require_active_handoff():
                            current = engine.runtime.state
                            if (current is None or current.mission_id != mission.mission_id
                                    or current.state in {"STOPPED", "BLOCKED", "FAILED", "NEEDS_HUMAN"}
                                    or resolve_task_binding(runtime_root, current.mission_id) != start
                                    or OperatorControlStore(runtime_root).current().get("action") in {"STOP", "PAUSE"}):
                                raise ValueError("handoff interrupted during completion verification")
                        try:
                            completed = acknowledge_delivery(
                                repo_root, runtime_root, durable, mission_id=mission.mission_id,
                                cycle_id=str(data.get("cycle_id") or ""),
                                result_sha256=str(data.get("result_sha256") or ""),
                                require_active=require_active_handoff,
                            )
                        finally:
                            durable.close()
                        try:
                            mark_result_delivered(
                                runtime_root / "file-loop-state.json",
                                str(data.get("result_sha256") or ""),
                            )
                        except ValueError:
                            pass
                        if mission.state != "DONE":
                            require_active_handoff()
                            engine.runtime.final("DONE", completed["human_reason"])
                        self._json(200, completed)
                        return

                    if path == "/v1/file-loop/delivery-ack":
                        # AGP_K07_DELIVERY_STATE_V1: the browser confirms that
                        # the result evidence and continuation were committed
                        # as a new user turn for exactly this result hash.
                        data = self._body()
                        result_sha256 = str(data.get("result_sha256") or "").strip()
                        if len(result_sha256) != 64:
                            raise ValueError("result_sha256 required")
                        acknowledged = mark_result_delivered(
                            runtime_root / "file-loop-state.json",
                            result_sha256,
                            None if engine.runtime.state is None else engine.runtime.state.mission_id,
                        )
                        diag.event(
                            "K07_RESULT_DELIVERED",
                            component="file-loop",
                            details={
                                "cycle_id": str(data.get("cycle_id") or "")[:40],
                                "result_sha256": result_sha256,
                                "step": acknowledged.get("step"),
                                "idempotent": acknowledged.get("idempotent"),
                                "commit_via": str(data.get("commit_via") or "")[:40],
                            },
                        )
                        self._json(200, {"ok": True, "stage": "RESULT_DELIVERY_ACKNOWLEDGED", **acknowledged})
                        return

                    if path == "/v1/file-loop/download":
                        data = self._body()
                        filename, content, content_type = read_downloaded_command(
                            data.get("download_path", ""),
                            data.get("filename", ""),
                            repo_root,
                            # The approval decision belongs to /v1/file-loop/command
                            # (AGP_REMOTE_EFFECT_ASKS_HUMAN_V1); fetching must not
                            # turn a decision into a hard rejection.
                            allow_remote_effects=True,
                        )
                        self._json(
                            200,
                            {
                                "ok": True,
                                "stage": "COMMAND_FILE_FETCHED",
                                "filename": filename,
                                "href": "chatgpt://assistant-download/" + filename,
                                "content": content,
                                "content_type": content_type,
                                "chars": len(content),
                                "bytes": len(content.encode("utf-8")),
                                "sha256": __import__("hashlib").sha256(content.encode("utf-8")).hexdigest(),
                            },
                        )
                        return

                    if path == "/v1/file-loop/reserve-step":
                        data = self._body()
                        step = int(data.get("step", 0) or 0)
                        if step <= 0:
                            raise ValueError("positive step required")
                        reserved = reserve_remote_issued_steps(
                            repo_root / "Download",
                            [step],
                        )
                        next_step = next_step_number(repo_root / "Download")
                        diag.event(
                            "K07_REMOTE_STEP_RESERVED",
                            component="file-loop",
                            details={
                                "step": step,
                                "next_step": next_step,
                                "reason": str(data.get("reason", ""))[:120],
                            },
                        )
                        self._json(
                            200,
                            {
                                "ok": True,
                                "stage": "REMOTE_STEP_RESERVED",
                                "step": step,
                                "next_step": next_step,
                                **reserved,
                            },
                        )
                        return

                    if path == "/v1/protocol/action":
                        length = int(self.headers.get("Content-Length", "0"))
                        if length <= 0 or length > 2_000_000:
                            raise ValueError("invalid Content-Length")
                        raw = self.rfile.read(length).decode("utf-8")
                        action = parse_action_frame(raw)
                        registration = protocol_v1_actions.register(action)
                        self._json(200, {
                            "protocol_version": action.protocol_version,
                            "session_id": action.session_id,
                            "round_id": action.round_id,
                            "action_id": action.action_id,
                            "decision": registration.decision,
                        })
                        return

                    if path == "/v1/protocol/execute":
                        length = int(self.headers.get("Content-Length", "0"))
                        if length <= 0 or length > 2_000_000:
                            raise ValueError("invalid Content-Length")
                        raw = self.rfile.read(length).decode("utf-8")
                        action = parse_action_frame(raw)
                        durable = durable_controller_for(action.session_id)
                        durable_decision = durable.accept_remote_action(
                            action.action_id,
                            asdict(action),
                        )
                        if durable_decision == "DUPLICATE":
                            cached = protocol_v1_results.get(action.action_id)
                            if cached is None:
                                self._json(200, {
                                    "decision": "DUPLICATE",
                                    "action_id": action.action_id,
                                    "replayed": False,
                                    "reason": "durable duplicate suppressed after restart; no in-memory result replay available",
                                })
                                return
                        registration = protocol_v1_actions.register(action)
                        if registration.decision == "DUPLICATE":
                            cached = protocol_v1_results.get(action.action_id)
                            if cached is None:
                                raise ValueError(
                                    "duplicate action has no completed result; automatic replay forbidden"
                                )
                            self._json(200, {
                                "decision": "REPLAYED",
                                "action_id": action.action_id,
                                "result_frame": cached,
                            })
                            return
                        if not isinstance(action.work_order, dict) or action.work_order.get("type") != "terminal_payload" or not isinstance(action.work_order.get("content"), str):
                            raise PermissionError("ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT")
                        authority_order = parse_work_order_json(action.work_order["content"])
                        authorization_payload = {
                            "effect": "E2",
                            "argv": list(authority_order.argv),
                            "cwd": str(authority_order.cwd),
                        }
                        if not durable.action_authorized(authorization_payload):
                            raise PermissionError("ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT")
                        attempt_no = durable.begin_attempt(action.action_id)
                        try:
                            frame = execute_direct_action(
                                action,
                                repository_root=engine.repository_root,
                                kit_binary=engine.kit_binary,
                                allowed_tools=frozenset(json.loads(durable.store.task_authority(durable.task_id)["allowed_tools_json"])),
                                allow_network=bool(durable.store.task_authority(durable.task_id).get("allow_network", 0)),
                            )
                        except Exception as exc:
                            durable.mark_outcome_unknown(action.action_id, attempt_no, f"execution raised before durable result persistence: {type(exc).__name__}: {exc}")
                            raise
                        observed = parse_result_frame(frame)
                        durable.record_local_result(action.action_id, attempt_no, observed.transport_status, f"Protocol-v1 local execution observed return_code={observed.local_execution.get('return_code')}", observed.transport_status == "BLOCKED")
                        protocol_v1_results[action.action_id] = frame
                        self._json(200, {"decision": "EXECUTED", "action_id": action.action_id, "result_frame": frame})
                        return

                    if path == "/v1/turn":
                        # K04: legacy mission continuation is not an authoritative execution path.
                        self._json(410, {"error": "LEGACY_TURN_AUTHORITY_RETIRED", "next": "/v1/protocol/execute"})
                        return

                    if path == "/v1/turn-legacy-disabled":
                        length = int(
                            self.headers.get(
                                "Content-Length",
                                "0",
                            )
                        )
                        if length <= 0 or length > 2_000_000:
                            raise ValueError(
                                "invalid Content-Length"
                            )

                        raw = self.rfile.read(
                            length
                        ).decode("utf-8")
                        request = parse_turn_request(raw)

                        state_before = engine.runtime.state
                        diag.event(
                            "TURN_SUBMIT_STARTED",
                            mission_id=(
                                None
                                if state_before is None
                                else state_before.mission_id
                            ),
                            turn=(
                                None
                                if state_before is None
                                else state_before.turn_count
                            ),
                            step=(
                                None
                                if state_before is None
                                else state_before.step_count
                            ),
                            state_before=(
                                "IDLE"
                                if state_before is None
                                else state_before.state
                            ),
                            component="http",
                            details={
                                "assistant": DiagnosticLogger.text_meta(
                                    request.assistant_text
                                )
                            },
                        )

                        response = engine.handle_turn(request)
                        state_after = engine.runtime.state

                        diag.event(
                            "TURN_SUBMIT_OK",
                            mission_id=(
                                None
                                if state_after is None
                                else state_after.mission_id
                            ),
                            turn=(
                                None
                                if state_after is None
                                else state_after.turn_count
                            ),
                            step=(
                                None
                                if state_after is None
                                else state_after.step_count
                            ),
                            state_after=response.state,
                            component="http",
                            details={
                                "action": response.action,
                                "note": response.note[:300],
                            },
                        )

                        self._json(
                            200,
                            json.loads(
                                encode_turn_response(
                                    response
                                )
                            ),
                        )
                        return

                    data = self._body()

                    # AGP_HUMAN_DECISION_V1: the human answers a NEEDS_HUMAN
                    # question of the current mission (desktop app only).
                    if path == "/v1/task/decision":
                        from agp_cockpit.core.human_decision import HumanDecisionStore
                        from agp_cockpit.core.start_request import resolve_task_binding
                        mission = engine.runtime.state
                        mission_id = str(data.get("mission_id") or "")
                        if mission is None or mission.mission_id != mission_id:
                            raise ValueError("decision does not belong to the current mission")
                        if mission.state != "NEEDS_HUMAN":
                            raise ValueError(f"mission is {mission.state}, not waiting for a human decision")
                        task_id = str(resolve_task_binding(runtime_root, mission_id).get("task_id") or "")
                        from agp_cockpit.core.human_decision import SCOPES
                        scope_key = str(data.get("scope") or "full")
                        if scope_key not in SCOPES:
                            raise ValueError(f"unknown approval scope: {scope_key}")
                        record = HumanDecisionStore(runtime_root).record(
                            mission_id=mission_id, task_id=task_id,
                            decision=str(data.get("decision") or ""),
                            question=mission.last_summary, note=str(data.get("note") or ""),
                            scope=SCOPES[scope_key],
                        )
                        record["scope_choice"] = scope_key
                        diag.event(
                            "HUMAN_DECISION_RECORDED",
                            component="task",
                            mission_id=mission_id,
                            details={"task_id": task_id, "decision": record["decision"],
                                     "grant": bool(record["grant"])},
                        )
                        self._json(200, record)
                        return

                    if path == "/v1/task/complete-proposal":
                        session_id = str(data.get("session_id", "")).strip()
                        if not session_id:
                            raise ValueError("session_id required")
                        durable = durable_controller_for(session_id)
                        accepted = durable.propose_complete()
                        self._json(200, {"authority":"DurableTaskController","accepted":bool(accepted),"session_id":session_id,"task":durable.snapshot})
                        return

                    if path == "/v1/task/checkpoint/request":
                        session_id = str(data.get("session_id", "")).strip()
                        checkpoint_id = str(data.get("checkpoint_id", "")).strip()
                        revision = str(data.get("revision", "")).strip()
                        artifact_hash = str(data.get("artifact_hash", "")).strip()
                        if not all((session_id, checkpoint_id, revision, artifact_hash)):
                            raise ValueError("complete checkpoint request required")
                        durable = durable_controller_for(session_id)
                        durable.request_human_checkpoint(checkpoint_id, revision, artifact_hash)
                        self._json(200, {"authority":"DurableTaskController","session_id":session_id,"task":durable.snapshot,"control":durable.control_snapshot})
                        return

                    if path == "/v1/task/checkpoint/approve":
                        session_id = str(data.get("session_id", "")).strip()
                        checkpoint_id = str(data.get("checkpoint_id", "")).strip()
                        revision = str(data.get("revision", "")).strip()
                        artifact_hash = str(data.get("artifact_hash", "")).strip()
                        if not all((session_id, checkpoint_id, revision, artifact_hash)):
                            raise ValueError("complete checkpoint approval required")
                        durable = durable_controller_for(session_id)
                        durable.approve_human_checkpoint(checkpoint_id, revision, artifact_hash)
                        self._json(200, {"authority":"DurableTaskController","session_id":session_id,"task":durable.snapshot,"control":durable.control_snapshot})
                        return

                    if path == "/v1/client-event":
                        client_response = {"ok": True}
                        state = engine.runtime.state
                        event_name = str(
                            data.get("event", "CLIENT_EVENT")
                        )[:80]
                        details = data.get("details", {})
                        if not isinstance(details, dict):
                            details = {"value": str(details)[:300]}

                        engine.runtime.record_browser_transport(event_name, details)

                        if event_name == "TASK_START_REQUEST_ACCEPTED":
                            # A start request is a one-shot trigger.  The
                            # browser may continue polling while bootstrap
                            # transport is being reconciled; leaving the
                            # request populated would replay the same mission
                            # after every failed attempt.
                            from agp_cockpit.core.start_request import StartRequestStore

                            pending = StartRequestStore(runtime_root).current()
                            requested_generation = int(details.get("generation", 0) or 0)
                            requested_mission = str(
                                details.get("request_mission_id", "")
                            ).strip()
                            if (
                                requested_generation > 0
                                and requested_generation == int(pending.get("generation", 0) or 0)
                                and requested_mission == str(pending.get("mission_id", "")).strip()
                            ):
                                from agp_cockpit.core.start_request import (
                                    ActiveTaskStore,
                                )

                                # AGP_K07_ACTIVE_TASK_BINDING_V1: keep the
                                # mission's task identity beyond the one-shot
                                # trigger invalidation below.
                                ActiveTaskStore(runtime_root).bind(
                                    requested_mission,
                                    str(pending.get("task_id", "") or ""),
                                    requested_generation,
                                )
                                StartRequestStore(runtime_root).invalidate_pending()
                                client_response["task_start_request"] = "CONSUMED"
                                diag.event(
                                    "TASK_START_REQUEST_CONSUMED",
                                    mission_id=requested_mission,
                                    component="http",
                                    details={"generation": requested_generation},
                                )

                        if event_name == "RESULT_DELIVERED":
                            session_id = str(details.get("session_id", "")).strip()
                            action_id = str(details.get("action_id", "")).strip()
                            if not session_id or not action_id:
                                raise ValueError("RESULT_DELIVERED requires session_id and action_id")
                            durable = durable_controller_for(session_id)
                            pending = [
                                row
                                for row in durable.pending_results()
                                if row.get("action_id") == action_id
                            ]
                            if len(pending) > 1:
                                raise RuntimeError("multiple pending durable results for action")
                            if len(pending) == 1:
                                durable.mark_result_delivered(pending[0]["message_id"])
                                client_response["result_delivery"] = "ACKNOWLEDGED"
                            else:
                                known = durable.store.db.execute(
                                    "SELECT 1 FROM messages "
                                    "WHERE task_id=? AND direction='OUT' AND kind='RESULT' "
                                    "AND action_id=? AND delivered=1 LIMIT 1",
                                    (durable.task_id, action_id),
                                ).fetchone()
                                if known is None:
                                    raise ValueError(
                                        "RESULT_DELIVERED does not match a durable result"
                                    )
                                client_response["result_delivery"] = "ALREADY_ACKNOWLEDGED"

                        if event_name == "EXTENSION_HANDSHAKE":
                            import time as _time
                            handshake_path = (
                                runtime_root / "extension.json"
                            )
                            handshake_path.parent.mkdir(
                                parents=True, exist_ok=True
                            )
                            handshake_path.write_text(
                                json.dumps({
                                    "timestamp_unix": _time.time(),
                                    "version": str(details.get("version", ""))[:80],
                                    "build_id": str(details.get("build_id", ""))[:120],
                                    "page_url": str(details.get("page_url", ""))[:500],
                                }, indent=2) + "\n",
                                encoding="utf-8",
                            )

                        if event_name == "EXTENSION_HANDSHAKE":
                            import time as _refresh_time

                            handled_refresh_path = runtime_dir(repo_root, "browser", "handled_refresh.json")   # AGP_RUNTIME_HOME_V1
                            handled_refresh_path.parent.mkdir(
                                parents=True,
                                exist_ok=True,
                            )

                            handled_generation = 0
                            try:
                                handled_generation = int(
                                    details.get(
                                        "handled_refresh_generation",
                                        0,
                                    )
                                    or 0
                                )
                            except Exception:  # noqa: BLE001 - malformed diagnostic metadata defaults safely.
                                handled_generation = 0

                            handled_refresh_path.write_text(
                                json.dumps(
                                    {
                                        "generation": handled_generation,
                                        "timestamp_unix": _refresh_time.time(),
                                        "version": str(
                                            details.get("version", "")
                                        )[:80],
                                        "build_id": str(
                                            details.get("build_id", "")
                                        )[:120],
                                        "page_url": str(
                                            details.get("page_url", "")
                                        )[:500],
                                    },
                                    indent=2,
                                )
                                + "\n",
                                encoding="utf-8",
                            )

                            refresh_request_path = runtime_dir(repo_root, "browser", "refresh_request.json")   # AGP_RUNTIME_HOME_V1
                            refresh_generation = 0
                            try:
                                refresh_request = json.loads(
                                    refresh_request_path.read_text(
                                        encoding="utf-8"
                                    )
                                )
                                refresh_generation = int(
                                    refresh_request.get(
                                        "generation",
                                        0,
                                    )
                                )
                            except Exception:  # noqa: BLE001 - malformed refresh metadata defaults safely.
                                refresh_generation = 0

                            # AGP_EXTENSION_AUTO_REFRESH_V2 (live 2026-10-01/02: the
                            # old extension ran four hours beside a new app because
                            # the startup worker wrote no request without an early
                            # handshake). The handshake itself decides: a different
                            # build than the staged one gets one refresh per target.
                            expected_build = str(
                                _runtime_identity_payload().get("extension_expected_build_id")
                                or BRIDGE_BUILD_ID
                            )
                            reported_build = str(details.get("build_id", "") or "")
                            if (
                                reported_build
                                and expected_build
                                and reported_build != expected_build
                                and refresh_generation <= handled_generation
                                and refresh_request_target(repo_root) != expected_build
                            ):
                                refresh_generation = request_browser_refresh(
                                    repo_root,
                                    reason="handshake-build-mismatch",
                                    target_build_id=expected_build,
                                ).generation
                            if reported_build and reported_build == expected_build:
                                # AGP_SINGLE_REFRESH_V1: a current extension never reloads
                                # itself; a pending request counts as done (the startup
                                # worker waits for that marker).
                                if refresh_generation > handled_generation:
                                    marker = json.loads(handled_refresh_path.read_text(encoding="utf-8"))
                                    marker["generation"] = refresh_generation
                                    marker["satisfied_by_current_build"] = True
                                    handled_refresh_path.write_text(
                                        json.dumps(marker, indent=2) + "\n", encoding="utf-8")
                                refresh_generation = 0
                            client_response[
                                "refresh_generation"
                            ] = refresh_generation
                            client_response["extension_expected_build_id"] = expected_build

                        diag.event(
                            event_name,
                            mission_id=(
                                None
                                if state is None
                                else state.mission_id
                            ),
                            turn=(
                                None
                                if state is None
                                else state.turn_count
                            ),
                            step=(
                                None
                                if state is None
                                else state.step_count
                            ),
                            state_after=(
                                None
                                if state is None
                                else state.state
                            ),
                            component="chrome",
                            details={
                                key: (
                                    value[:500]
                                    if isinstance(value, str)
                                    else value
                                )
                                for key, value in details.items()
                            },
                        )
                        self._json(200, client_response)
                        return

                    if path == "/v1/file-loop/control":
                        from agp_cockpit.core.operator_control import (
                            OperatorControlStore,
                        )
                        from agp_cockpit.core.start_request import StartRequestStore
                        action = str(data.get("action", "")).strip()
                        control = OperatorControlStore(runtime_root).request(action)
                        if action.upper() == "STOP":
                            if engine.runtime.state is not None:
                                # AGP_STOP_REASON_V1: keep the real cause
                                # (send failure, rejection, build mismatch).
                                stop_reason = " ".join(str(data.get("reason") or "").split())[:300]
                                engine.runtime.stop(stop_reason or "Stopped by operator control")
                                process_stop = engine.runtime.last_execution_stop or {
                                    "requested": False,
                                    "active": False,
                                    "pid": None,
                                }
                                StartRequestStore(runtime_root).invalidate_pending()
                                _approval_grant(runtime_root, engine)  # expires an unused approval
                            else:
                                process_stop = run_next_controller.stop()
                        else:
                            process_snapshot = run_next_controller.snapshot()
                            process_stop = {
                                "requested": False,
                                "active": process_snapshot["active"],
                                "pid": process_snapshot["pid"],
                            }
                        self._json(200, {
                            **control,
                            "process_stop": process_stop,
                            "mission_state": (
                                None
                                if engine.runtime.state is None
                                else engine.runtime.state.state
                            ),
                        })
                        return

                    if path == "/v1/task/start-request":
                        from agp_cockpit.core.runtime_identity import (
                            runtime_identity_status,
                        )
                        from agp_cockpit.core.start_request import StartRequestStore
                        mission_id=str(data.get("mission_id","")).strip()
                        task_id=str(data.get("task_id","")).strip()
                        state=engine.runtime.state
                        if not mission_id or state is None or state.mission_id != mission_id:
                            raise ValueError("start request must target current mission")
                        identity = runtime_identity_status(
                            repo_root,
                            runtime_root,
                            expected_conversation_url=state.conversation_url,
                            max_handshake_age_seconds=engine.limits.max_handshake_age_seconds,
                        )
                        if not identity["ready"]:
                            raise RuntimeError(
                                "runtime identity is not ready: "
                                + ", ".join(identity["reasons"])
                            )
                        if state.browser_transport_blocked:
                            model_recovery = "COMPOSER_MODEL_NOT_VERIFIED" in (
                                state.browser_transport_block_reason or ""
                            )
                            if model_recovery and state.browser_transport_recovery_attempts < 1:
                                state.browser_transport_blocked = False
                                state.browser_transport_recovery_attempts += 1
                                state.browser_transport_event = "COMPOSER_MODEL_RETRY_AUTHORIZED"
                                state.browser_transport_note = (
                                    "one explicit bounded editor-model recovery retry authorized"
                                )
                                engine.runtime.store.save(state)
                            else:
                                raise RuntimeError(
                                    "browser transport is blocked after an unverified send; "
                                    "reload the AGP Cockpit extension and the ChatGPT tab, "
                                    "then retry after a fresh extension handshake"
                                )
                        self._json(
                            200,
                            StartRequestStore(runtime_root).request(
                                mission_id,
                                task_id=task_id,
                            ),
                        )
                        return

                    if path == "/v1/mission":
                        title = str(
                            data.get("title", "")
                        ).strip()
                        mission_text = str(
                            data.get("mission_text", "")
                        ).strip()
                        conversation_url = str(data.get("conversation_url", "")).strip()
                        execution_mode = str(
                            data.get(
                                "execution_mode",
                                "DRY_RUN",
                            )
                        )
                        run_mode = str(
                            data.get(
                                "run_mode",
                                "SINGLE_STEP",
                            )
                        )

                        if not title or not mission_text:
                            raise ValueError(
                                "title and mission_text required"
                            )

                        state = engine.runtime.create_mission(
                            title=title,
                            mission_text=mission_text,
                            conversation_url=conversation_url,
                            execution_mode=execution_mode,
                            run_mode=run_mode,
                        )
                        engine.reset_automation_guard()

                        diag.event(
                            "MISSION_CREATED",
                            mission_id=state.mission_id,
                            turn=state.turn_count,
                            step=state.step_count,
                            state_after=state.state,
                            component="mission",
                            details={
                                "execution_mode": state.execution_mode,
                                "run_mode": state.run_mode,
                                "mission": DiagnosticLogger.text_meta(
                                    state.mission_text
                                ),
                            },
                        )

                        self._json(
                            200,
                            {"mission": asdict(state)},
                        )
                        return

                    if path == "/v1/resume":
                        state = engine.runtime.resume_next_step()
                        diag.event(
                            "SINGLE_STEP_RESUMED",
                            mission_id=state.mission_id,
                            turn=state.turn_count,
                            step=state.step_count,
                            state_after=state.state,
                            component="mission",
                        )
                        self._json(
                            200,
                            {"mission": asdict(state)},
                        )
                        return

                    if path == "/v1/mode":
                        state = engine.runtime.set_modes(
                            execution_mode=data.get(
                                "execution_mode"
                            ),
                            run_mode=data.get(
                                "run_mode"
                            ),
                        )
                        diag.event(
                            "MISSION_MODE_CHANGED",
                            mission_id=state.mission_id,
                            state_after=state.state,
                            component="mission",
                            details={
                                "execution_mode": state.execution_mode,
                                "run_mode": state.run_mode,
                            },
                        )
                        self._json(
                            200,
                            {"mission": asdict(state)},
                        )
                        return

                    self._json(404, {"error": "not found"})

                except Exception as exc:  # noqa: BLE001 - HTTP boundary returns structured diagnostics.
                    error_id = DiagnosticLogger.new_error_id()
                    diag.event(
                        "HTTP_REQUEST_FAILED",
                        component="http",
                        error_id=error_id,
                        details={
                            "path": path,
                            "type": type(exc).__name__,
                            "message": str(exc)[:600],
                        },
                    )
                    self._json(
                        400,
                        {
                            "error": (
                                f"{type(exc).__name__}: {exc}"
                            ),
                            "error_id": error_id,
                        },
                    )
                finally:
                    if file_loop_locked:
                        file_loop_lock.release()

            def log_message(self, format, *args):
                return

        self._server = ThreadingHTTPServer(
            (self.config.host, self.config.port),
            Handler,
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
        )
        self._thread.start()

        diag.event(
            "BRIDGE_SERVER_STARTED",
            component="bridge",
            details={
                "host": self.config.host,
                "port": self._server.server_address[1],
            },
        )

    def stop(self) -> None:
        if self.engine.runtime.state is not None:
            self.engine.runtime.stop("Bridge server stopped")
        else:
            self._run_next_controller.stop()
        if self._server is not None:
            self.diag.event(
                "BRIDGE_SERVER_STOPPING",
                component="bridge",
            )
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None
