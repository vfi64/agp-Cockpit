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
from agp_cockpit.core.transport_protocol_v1 import ActionRegistry, parse_action_frame


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
        self.engine = BridgeEngine(self.repository_root)
        self.diag = DiagnosticLogger(self.repository_root)
        self.protocol_v1_actions = ActionRegistry()

        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return

        engine = self.engine
        token = self.config.token
        diag = self.diag
        repo_root = self.repository_root
        protocol_v1_actions = self.protocol_v1_actions

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

                    if path == "/v1/turn":
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

                    if path == "/v1/client-event":
                        client_response = {"ok": True}
                        state = engine.runtime.state
                        event_name = str(
                            data.get("event", "CLIENT_EVENT")
                        )[:80]
                        details = data.get("details", {})
                        if not isinstance(details, dict):
                            details = {"value": str(details)[:300]}

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
