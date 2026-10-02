"""Finding status from the Kit repository (AGP_KIT_FINDINGS_SYNC_V1).

The Kit project records its own adjudication of the Greenfield findings in
``docs/reports/*.json`` (``finding_status`` / ``finding_adjudications`` /
``finding``). This module reads a checkout of the public Kit repository at an
exact commit and derives, per KIT-GF id, the latest Kit statement:

* CLOSED  — the Kit says fixed or closed;
* PARTIAL — implemented, mitigated or partially addressed, retest pending;
* OPEN    — open, deferred, retest required.

``fixed_in`` (CLOSED only) is derived from CHANGELOG release dates: a fix on
main is in the first release dated after the report; a statement about a
released package names the last release dated on or before the report.
The result is a pure function of the checkout; it is stored as an overlay in
``.local/agp-cockpit/kit/kit-findings-status.json`` and never edits the
Cockpit's own register.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

KIT_REPO_URL = "https://github.com/vfi64/agentic-project-kit"
OVERLAY = Path(".local/agp-cockpit/kit/kit-findings-status.json")
CACHE = Path(".local/agp-cockpit/kit/kit-repo")
CLOSED, PARTIAL, OPEN = "CLOSED", "PARTIAL", "OPEN"
_RELEASE = re.compile(r"^## v(\d+\.\d+\.\d+) - (\d{4}-\d{2}-\d{2})", re.MULTILINE)
_EXPLICIT = re.compile(r"fixed_in_v(\d+)_(\d+)_(\d+)")


def classify(raw: str) -> str:
    text = str(raw or "").lower()
    if re.match(r"^(fixed|closed)(_|$)", text) or "fixed_in_v" in text or "fixed_released_package" in text \
            or "externally closed" in text or text.startswith("pass |"):
        return CLOSED
    if re.search(r"partial|mitigat|improved|implemented|likely_addressed|mostly|retested_pass", text):
        return PARTIAL
    return OPEN


def releases(changelog: str) -> list[tuple[str, str]]:
    return sorted(((v, d) for v, d in _RELEASE.findall(changelog)), key=lambda r: (r[1], _key(r[0])))


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split("."))


def fixed_in(raw: str, date: str, released: list[tuple[str, str]], report: str = "") -> str:
    explicit = _EXPLICIT.search(str(raw))
    if explicit:
        return ".".join(explicit.groups())
    if "released" in str(raw).lower() or "RELEASED_PACKAGE" in report.upper():
        before = [v for v, d in released if d <= date]
        return max(before, key=_key) if before else ""
    after = [v for v, d in released if d > date]
    return min(after, key=_key) if after else ""


def _statements(report: Path):
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    date = str(data.get("date") or "")
    for key in ("finding_status", "finding_adjudications"):
        for item in data.get(key) or ():
            if isinstance(item, dict) and str(item.get("id", "")).startswith("KIT-GF-"):
                yield str(item["id"]), date, str(item.get("status") or "")
    finding = data.get("finding")
    if isinstance(finding, str) and finding.startswith("KIT-GF-"):
        yield finding, date, f"{data.get('status')} | {data.get('conclusion') or ''}"
    elif isinstance(finding, dict) and str(finding.get("id", "")).startswith("KIT-GF-"):
        yield str(finding["id"]), date, str(finding.get("current_status") or "")


def collect(kit_checkout: Path, commit: str = "") -> dict:
    checkout = Path(kit_checkout)
    changelog = (checkout / "CHANGELOG.md").read_text(encoding="utf-8") if (checkout / "CHANGELOG.md").is_file() else ""
    released = releases(changelog)
    history: dict[str, list[tuple[str, str, str]]] = {}
    for report in sorted((checkout / "docs" / "reports").glob("*.json")):
        for finding_id, date, raw in _statements(report):
            history.setdefault(finding_id, []).append((date, report.name, raw))
    findings = {}
    for finding_id, statements in sorted(history.items()):
        statements.sort()
        date, report, raw = statements[-1]
        state = classify(raw)
        entry = {"kit_state": state, "raw": raw, "date": date, "report": f"docs/reports/{report}",
                 "fixed_in": ""}
        if state == CLOSED:
            # the fix dates from the first statement of the final closed streak
            first = len(statements) - 1
            while first > 0 and classify(statements[first - 1][2]) == CLOSED:
                first -= 1
            f_date, f_report, f_raw = statements[first]
            entry["fixed_in"] = fixed_in(raw, f_date, released, f_report) if _EXPLICIT.search(raw) \
                else fixed_in(f_raw, f_date, released, f_report)
            entry["closed_since"] = f"{f_date} (docs/reports/{f_report})"
        findings[finding_id] = entry
    return {"source": KIT_REPO_URL, "kit_commit": commit,
            "latest_release": max((v for v, _ in released), key=_key) if released else "",
            "findings": findings}


def fetch(repository_root: Path, *, runner=subprocess.run) -> tuple[Path, str]:
    """Shallow read-only clone or fetch of the public Kit repository."""
    cache = Path(repository_root) / CACHE
    def git(*args, cwd=None):
        done = runner(["git", *args], cwd=str(cwd) if cwd else None, text=True,
                      capture_output=True, timeout=180, check=False)
        if done.returncode != 0:
            raise RuntimeError((done.stderr or done.stdout or "git failed").strip()[-400:])
        return (done.stdout or "").strip()
    if (cache / ".git").is_dir():
        git("fetch", "-q", "--depth", "1", "origin", "HEAD", cwd=cache)
        git("reset", "-q", "--hard", "FETCH_HEAD", cwd=cache)
    else:
        cache.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "-q", "--depth", "1", KIT_REPO_URL, str(cache))
    return cache, git("rev-parse", "HEAD", cwd=cache)


def write_overlay(repository_root: Path, overlay: dict) -> Path:
    target = Path(repository_root) / OVERLAY
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(overlay, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_overlay(repository_root: Path) -> dict:
    try:
        data = json.loads((Path(repository_root) / OVERLAY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def sync(repository_root: Path, *, runner=subprocess.run) -> dict:
    checkout, commit = fetch(repository_root, runner=runner)
    overlay = collect(checkout, commit)
    write_overlay(repository_root, overlay)
    return overlay
