from __future__ import annotations

from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import secrets
import threading
from urllib.parse import urlparse

from agp_cockpit.core.bridge_engine import BridgeEngine
from agp_cockpit.core.bridge_protocol import (
    encode_turn_response,
    parse_turn_request,
)
from agp_cockpit.core.diagnostic_log import DiagnosticLogger
from agp_cockpit.core.transport_protocol_v1 import ActionRegistry, parse_action_frame, parse_result_frame
from agp_cockpit.core.protocol_execution_v1 import execute_direct_action
from agp_cockpit.core.work_order import parse_work_order_json
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_contract import LocalTaskContract


@dataclass(frozen=True)
class BridgeServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    token: str = ""


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
        self.runtime_root = (runtime_root.expanduser().resolve() if runtime_root is not None else (self.repository_root / ".local" / "agp-cockpit" / "bridge"))
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.engine = BridgeEngine(self.repository_root)
        self.diag = DiagnosticLogger(self.repository_root)
        self.protocol_v1_actions = ActionRegistry()
        self.protocol_v1_results: dict[str, str] = {}
        self._durable_db_path = self.runtime_root / "protocol-v1-actions.sqlite3"
        self.local_task_contract = local_task_contract
        self._durable_controllers: dict[str, DurableTaskController] = {}

        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def _durable_controller(self, session_id: str) -> DurableTaskController:
        controller = self._durable_controllers.get(session_id)
        if controller is None:
            controller = DurableTaskController(
                f"protocol-v1-http:{session_id}",
                self._durable_db_path,
                local_contract=self.local_task_contract,
            )
            self._durable_controllers[session_id] = controller
        return controller

    def start(self) -> None:
        if self._server is not None:
            return

        engine = self.engine
        token = self.config.token
        diag = self.diag
        repo_root = self.repository_root
        protocol_v1_actions = self.protocol_v1_actions
        protocol_v1_results = self.protocol_v1_results
        durable_controller_for = self._durable_controller
        runtime_root = self.runtime_root

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
                    raise ValueError("request body must be object")
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

                if path == "/v1/task/start-request":
                    from agp_cockpit.core.start_request import StartRequestStore
                    self._json(200, StartRequestStore(runtime_root).current())
                    return

                if path == "/v1/status":
                    state = engine.runtime.state
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

                try:
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
                            "effect": "E3" if authority_order.kind == "kit" else "E2",
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
                                repo_root
                                / ".local"
                                / "agp-cockpit"
                                / "bridge"
                                / "extension.json"
                            )
                            handshake_path.parent.mkdir(
                                parents=True, exist_ok=True
                            )
                            handshake_path.write_text(
                                json.dumps({
                                    "timestamp_unix": _time.time(),
                                    "version": str(details.get("version", ""))[:80],
                                    "page_url": str(details.get("page_url", ""))[:500],
                                }, indent=2) + "\n",
                                encoding="utf-8",
                            )

                        if event_name == "EXTENSION_HANDSHAKE":
                            import time as _refresh_time

                            handled_refresh_path = (
                                repo_root
                                / ".local"
                                / "agp-cockpit"
                                / "browser"
                                / "handled_refresh.json"
                            )
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
                            except Exception:
                                handled_generation = 0

                            handled_refresh_path.write_text(
                                json.dumps(
                                    {
                                        "generation": handled_generation,
                                        "timestamp_unix": _refresh_time.time(),
                                        "version": str(
                                            details.get("version", "")
                                        )[:80],
                                        "page_url": str(
                                            details.get("page_url", "")
                                        )[:500],
                                    },
                                    indent=2,
                                )
                                + "\n",
                                encoding="utf-8",
                            )

                            refresh_request_path = (
                                repo_root
                                / ".local"
                                / "agp-cockpit"
                                / "browser"
                                / "refresh_request.json"
                            )
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
                            except Exception:
                                refresh_generation = 0

                            client_response[
                                "refresh_generation"
                            ] = refresh_generation

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

                    if path == "/v1/task/start-request":
                        from agp_cockpit.core.start_request import StartRequestStore
                        mission_id=str(data.get("mission_id","")).strip()
                        state=engine.runtime.state
                        if not mission_id or state is None or state.mission_id != mission_id:
                            raise ValueError("start request must target current mission")
                        self._json(200,StartRequestStore(runtime_root).request(mission_id))
                        return

                    if path == "/v1/mission":
                        title = str(
                            data.get("title", "")
                        ).strip()
                        mission_text = str(
                            data.get("mission_text", "")
                        ).strip()
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

                except Exception as exc:
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
