"""Deterministic projection of local results before they go to the remote chat.

AGP_RESULT_PROJECTION_V1 (2026-10-01): return bundles of one finish run
(steps 1547-1555) summed to about 378 KB; one bundle carried a full copy of the
previous bundle and every Kit execution twice (raw stdout and parsed JSON).
The remote side reads all of it on every turn.

The full files stay local and unchanged (their SHA-256 identifies the result
for receipts and replays). The remote side receives a projection that is a
pure function of the file bytes:

* ``previous_*`` keys (copies of earlier results) are replaced by a marker;
* raw ``stdout``/``stdout_tail`` next to a parsed ``json`` value is dropped;
* an execution diagnostic drops its ``stdout`` (the run_next log is attached
  separately) and carries the projections of its candidate return bundles,
  so the remote side does not need an extra step only to read them;
* long strings keep head and tail; failure context (non-zero return code,
  failed status, ``stderr``, ``error``, ``log_excerpt`` ...) keeps much more
  than success output.

Every cut names the omitted size and the SHA-256 of the omitted text; the
header names the local file. A detail is obtained with a work order that
prints exactly that part of the local file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROJECTION_VERSION = 1
SUCCESS_TEXT = 1_200        # strings inside a successful execution context
DEFAULT_TEXT = 4_000
FAILURE_TEXT = 12_000       # strings inside a failure context
LOG_HEAD, LOG_TAIL = 3_000, 9_000   # run_next log text
MAX_CANDIDATES = 2
FAILURE_KEYS = frozenset({
    "stderr", "stderr_tail", "error", "errors", "log_excerpt", "failure_reason",
    "failed_checks", "failed_run_diagnostics", "traceback", "violations",
})
FAILED_STATUS = frozenset({"failed", "fail", "blocked", "red", "error", "needs_human"})


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = limit * 3 // 10
    tail = limit - head
    omitted = text[head:len(text) - tail]
    return (text[:head] + f"\n…[agp: {len(omitted)} chars omitted, sha256 {_sha(omitted)}]…\n"
            + text[len(text) - tail:])


def _failing(value: dict) -> bool:
    code = value.get("returncode", value.get("rc"))
    if isinstance(code, int) and not isinstance(code, bool) and code != 0:
        return True
    status = str(value.get("status") or value.get("result_status") or "").strip().lower()
    return status in FAILED_STATUS


def _succeeding(value: dict) -> bool:
    code = value.get("returncode", value.get("rc"))
    return isinstance(code, int) and not isinstance(code, bool) and code == 0


def _marker(reason: str, value) -> dict:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    return {"agp_omitted": reason, "chars": len(text), "sha256": _sha(text)}


def project_value(value, *, limit: int = DEFAULT_TEXT):
    if isinstance(value, str):
        return _cut(value, limit)
    if isinstance(value, list):
        return [project_value(item, limit=limit) for item in value]
    if not isinstance(value, dict):
        return value
    if _failing(value):
        limit = FAILURE_TEXT
    elif _succeeding(value):
        limit = min(limit, SUCCESS_TEXT)
    parsed = isinstance(value.get("json"), (dict, list))
    result = {}
    for key, item in value.items():
        if key.startswith("previous_") and isinstance(item, (dict, list)):
            result[key] = _marker("copy of an earlier result, already delivered", item)
        elif parsed and key in {"stdout", "stdout_tail"} and isinstance(item, str) and item:
            result[key] = _marker("raw output; its parsed form is in \"json\"", item)
        else:
            result[key] = project_value(item, limit=FAILURE_TEXT if key in FAILURE_KEYS else limit)
    return result


def _header(path: Path, raw: bytes) -> dict:
    return {
        "version": PROJECTION_VERSION,
        "source": path.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "note": ("Shortened deterministically by the AGP Cockpit; the complete file stays local at "
                 f"Download/{path.name}. Markers \"agp_omitted\" and \"…[agp: … omitted …]…\" show cuts. "
                 "To read an omitted part, return a work order that prints exactly that part."),
    }


def project_bundle(path: Path) -> dict | None:
    """Projection of a JSON result file, or None if it is not a JSON object."""
    raw = Path(path).read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("kind") == "agp_cockpit_file_loop_execution_diagnostic":
        data = dict(data)
        if isinstance(data.get("stdout"), str) and data.get("run_next_output"):
            data["stdout"] = _marker("same text as the attached run_next log", data["stdout"])
        candidates = {}
        for name in list(data.get("candidate_return_bundles") or [])[:MAX_CANDIDATES]:
            candidate = Path(str(name))
            if candidate.is_file():
                projected = project_bundle(candidate)
                if projected is not None:
                    candidates[candidate.name] = projected
        if candidates:
            data["candidate_return_bundle_projections"] = candidates
    projected = project_value(data)
    return {"agp_projection": _header(Path(path), raw), **projected}


def project_log(path: Path) -> str:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if len(text) <= LOG_HEAD + LOG_TAIL:
        return text
    omitted = text[LOG_HEAD:len(text) - LOG_TAIL]
    return (text[:LOG_HEAD] + f"\n…[agp: {len(omitted)} chars of the local log {Path(path).name} omitted, "
            f"sha256 {_sha(omitted)}]…\n" + text[len(text) - LOG_TAIL:])


def delivery_files(repository_root: Path, result_file: Path, output_file: Path | None) -> dict:
    """Files to attach: projections where they are smaller, the originals otherwise.

    Projections keep the original file names (the remote side refers to them)
    and live under ``.local/agp-cockpit/delivery/``.
    """
    target_dir = Path(repository_root) / ".local" / "agp-cockpit" / "delivery"
    stats = {"result_file": str(result_file), "output_file": str(output_file) if output_file else None,
             "bytes_before": 0, "bytes_after": 0, "projected": []}

    def write(name: str, payload: str) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / name
        if not target.is_file() or target.read_text(encoding="utf-8") != payload:
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(target)
        return target

    result_file = Path(result_file)
    original = result_file.stat().st_size
    stats["bytes_before"] += original
    projected = project_bundle(result_file)
    payload = json.dumps(projected, ensure_ascii=False, indent=1) + "\n" if projected is not None else None
    if payload is not None and len(payload.encode("utf-8")) < original:
        stats["result_file"] = str(write(result_file.name, payload))
        stats["projected"].append(result_file.name)
        stats["bytes_after"] += len(payload.encode("utf-8"))
    else:
        stats["bytes_after"] += original
    if output_file is not None and Path(output_file).is_file():
        output_file = Path(output_file)
        original = output_file.stat().st_size
        stats["bytes_before"] += original
        text = project_log(output_file)
        if len(text.encode("utf-8")) < original:
            stats["output_file"] = str(write(output_file.name, text))
            stats["projected"].append(output_file.name)
            stats["bytes_after"] += len(text.encode("utf-8"))
        else:
            stats["bytes_after"] += original
    return stats
