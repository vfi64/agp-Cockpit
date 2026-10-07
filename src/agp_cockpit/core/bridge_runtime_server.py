from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.runtime_paths import runtime_dir
from agp_cockpit.core.bridge_server import (
    BridgeServerConfig,
    CockpitBridgeServer,
)
from agp_cockpit.core.task_contract import LocalTaskContract


@dataclass(frozen=True)
class RuntimeServerInfo:
    host: str
    port: int
    token: str


class BridgeRuntimeServer:
    def __init__(
        self,
        repository_root: Path,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: str | None = None,
        runtime_root: Path | None = None,
        local_task_contract: LocalTaskContract | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.local_root = (
            runtime_root.expanduser().resolve()
            if runtime_root is not None
            else runtime_dir(self.repository_root, "bridge")   # AGP_RUNTIME_HOME_V1
        )
        self.local_root.mkdir(parents=True, exist_ok=True)

        token_path = self.local_root / "token.txt"

        if token is None:
            if token_path.exists():
                token = token_path.read_text(
                    encoding="utf-8"
                ).strip()
            else:
                token = secrets.token_urlsafe(32)
                token_path.write_text(
                    token + "\n",
                    encoding="utf-8",
                )

        if not token:
            raise ValueError("bridge token must not be empty")

        self.server = CockpitBridgeServer(
            self.repository_root,
            config=BridgeServerConfig(
                host=host,
                port=port,
                token=token,
            ),
            runtime_root=self.local_root,
            local_task_contract=local_task_contract,
        )

    @property
    def info(self) -> RuntimeServerInfo:
        server = self.server._server
        port = (
            self.server.config.port
            if server is None
            else server.server_address[1]
        )
        return RuntimeServerInfo(
            host=self.server.config.host,
            port=port,
            token=self.server.config.token,
        )

    def start(self) -> RuntimeServerInfo:
        self.server.start()
        info = self.info

        # A desktop restart is a new authority boundary. Do not let a stale
        # browser reconnect revive the previous mission automatically.
        self.server.engine.runtime.stop_stale_on_desktop_start()

        runtime_path = self.local_root / "runtime.json"
        runtime_path.write_text(
            json.dumps(
                {
                    "host": info.host,
                    "port": info.port,
                    "token_file": str(
                        self.local_root / "token.txt"
                    ),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return info

    def stop(self) -> None:
        self.server.stop()
