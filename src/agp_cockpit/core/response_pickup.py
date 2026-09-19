from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

FENCED_JSON_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class ClipboardSnapshot:
    digest: str
    length: int


@dataclass(frozen=True)
class ResponseExtraction:
    source_text: str
    work_order_text: str | None
    extraction_kind: str


def snapshot_text(text: str) -> ClipboardSnapshot:
    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()
    return ClipboardSnapshot(
        digest=digest,
        length=len(text),
    )


def clipboard_changed(
    before: ClipboardSnapshot,
    current_text: str,
) -> bool:
    return snapshot_text(current_text).digest != before.digest


def _is_work_order_object(data) -> bool:
    if not isinstance(data, dict):
        return False
    argv = data.get("argv")
    cwd = data.get("cwd")
    return (
        isinstance(argv, list)
        and bool(argv)
        and isinstance(cwd, str)
        and bool(cwd.strip())
    )


def _normalized_json(data: dict) -> str:
    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    )


def extract_work_order_from_response(
    text: str,
) -> ResponseExtraction:
    stripped = text.strip()

    if not stripped:
        return ResponseExtraction(
            source_text=text,
            work_order_text=None,
            extraction_kind="empty",
        )

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        data = None

    if _is_work_order_object(data):
        return ResponseExtraction(
            source_text=text,
            work_order_text=_normalized_json(data),
            extraction_kind="pure-json",
        )

    candidates = FENCED_JSON_RE.findall(text)
    valid = []

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if _is_work_order_object(data):
            valid.append(data)

    if len(valid) == 1:
        return ResponseExtraction(
            source_text=text,
            work_order_text=_normalized_json(valid[0]),
            extraction_kind="fenced-json",
        )

    if len(valid) > 1:
        raise ValueError(
            "LLM-Antwort enthält mehrere plausible JSON-Arbeitsaufträge"
        )

    return ResponseExtraction(
        source_text=text,
        work_order_text=None,
        extraction_kind="prose-only",
    )
