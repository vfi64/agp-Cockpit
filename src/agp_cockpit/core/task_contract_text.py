"""Editor text <-> task contract for the "Arbeiten" tab.

AGP_TASK_EDITOR_V1: a task is written, pasted or loaded into an editable
editor; its text is converted into the task contract only at start. Plain
text becomes the goal; text starting with "{" is a JSON task contract.
"""

from __future__ import annotations

import json
from pathlib import Path


def contract_from_text(text: str) -> dict:
    stripped = str(text or "").strip()
    if not stripped:
        raise ValueError("Der Auftrag ist leer.")
    if not stripped.startswith("{"):
        return {"goal": stripped}
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON-Auftrag ist ungültig (Zeile {exc.lineno}, Spalte {exc.colno}): {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("Ein JSON-Auftrag muss ein Objekt sein.")  # noqa: TRY004 - user-facing validation
    return payload


def editor_text_from_file(path: Path) -> str:
    raw = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() == ".json":
        return json.dumps(contract_from_text(raw), ensure_ascii=False, indent=2) + "\n"
    return raw
