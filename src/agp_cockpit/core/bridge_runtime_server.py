from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import secrets

from agp_cockpit.core.bridge_server import (
    BridgeServerConfig,
    CockpitBridgeServer,
)


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
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.local_root = (
            runtime_root.expanduser().resolve()
            if runtime_root is not None
            else (self.repository_root / ".local" / "agp-cockpit" / "bridge")
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
