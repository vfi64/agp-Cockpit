from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from hashlib import sha256
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiagnosticLogConfig:
    max_bytes: int = 2 * 1024 * 1024
    backup_count: int = 4


class DiagnosticLogger:
    def __init__(
        self,
        repository_root: Path,
        *,
        config: DiagnosticLogConfig | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.config = config or DiagnosticLogConfig()
        self.log_root = (
            self.repository_root
            / ".local"
            / "agp-cockpit"
            / "logs"
        )
        self.log_root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_root / "bridge.log"

        name = f"agp_cockpit_diag_{id(self)}"
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        handler = RotatingFileHandler(
            self.log_path,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    @staticmethod
    def text_meta(text: str | None) -> dict[str, Any]:
        if not text:
            return {
                "chars": 0,
                "sha256": None,
                "preview": "",
            }

        normalized = text.replace("\n", " ").strip()
        return {
            "chars": len(text),
            "sha256": sha256(
                text.encode("utf-8")
            ).hexdigest(),
            "preview": normalized[:160],
        }

    @staticmethod
    def new_error_id() -> str:
        return "ERR-" + secrets.token_hex(4).upper()

    def event(
        self,
        name: str,
        *,
        mission_id: str | None = None,
        turn: int | None = None,
        step: int | None = None,
        state_before: str | None = None,
        state_after: str | None = None,
        component: str = "bridge",
        error_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "event": name,
            "component": component,
            "mission_id": mission_id,
            "turn": turn,
            "step": step,
            "state_before": state_before,
            "state_after": state_after,
            "error_id": error_id,
            "details": details or {},
        }
        self.logger.info(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
