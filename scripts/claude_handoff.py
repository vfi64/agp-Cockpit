#!/usr/bin/env python3
"""Claude chat handoff from repository facts (AGP_CLAUDE_HANDOFF_FACTS_V1).

Live 2026-10-05: a hand-written handoff claimed two connected folders that the
new Cowork session did not have, named the previous session id for commit
trailers and stated a guess as a fact. The facts block is therefore generated
from the repository, the next chat re-checks it, and free-text notes must carry
an explicit tag.

  write  collect the facts, merge tagged notes, write the handoff file
  check  recompute the facts and report every difference to a handoff file

Standard library only (Python >= 3.10): it also runs in the Cowork VM.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
from collections import Counter
import sys
from pathlib import Path

HANDOFF_DIR = Path(".local/agp-cockpit/handoff")
FACTS_BEGIN = "<!-- AGP_CLAUDE_HANDOFF_FACTS_V1 -->"
NOTE_TAGS = ("[belegt: ", "[Vermutung]", "[Nächster Schritt]", "[Owner]")
KIT_FOLDER_NAME = "agentic-project-kit"


class HandoffError(Exception):
    pass


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise HandoffError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _match(path: Path, pattern: str, label: str) -> str:
    found = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if not found:
        raise HandoffError(f"{label} not found in {path}")
    return found.group(1)


def collect_facts(root: Path) -> dict:
    """Facts the next chat can re-derive from the repository alone."""
    status = _git(root, "status", "--porcelain")
    version = root / "src/agp_cockpit/version.py"
    protocol = (root / "docs/planning/COMMUNICATION_PROTOCOL.md").read_text(encoding="utf-8")
    rules = re.findall(r"^(\d+)\. .*?\(`([A-Z0-9_]+)`", protocol, re.MULTILINE)
    log = (root / "docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", log, re.MULTILINE)
    findings = json.loads((root / "docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json").read_text(encoding="utf-8"))
    contract = json.loads((root / ".agentic/state/handoff/packages/latest/execution_contract.json").read_text(encoding="utf-8"))
    try:
        origin_main = _git(root, "rev-parse", "--short=12", "origin/main")
    except HandoffError:
        origin_main = ""
    return {
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git(root, "rev-parse", "--short=12", "HEAD"),
        "origin_main": origin_main,
        "worktree_clean": status == "",
        "latest_tag": _git(root, "describe", "--tags", "--abbrev=0"),
        "app_version": _match(version, r'^APP_VERSION = "([^"]+)"', "APP_VERSION"),
        "bridge_build_id": _match(version, r'^BRIDGE_BUILD_ID = "([^"]+)"', "BRIDGE_BUILD_ID"),
        "extension_build_id": _match(root / "chrome_extension/build_identity.js",
                                     r'AGP_EXTENSION_BUILD_ID = "([^"]+)"', "AGP_EXTENSION_BUILD_ID"),
        "kit_ci_pin": _match(root / ".github/workflows/agentic-gate.yaml",
                             r'agentic-project-kit==([0-9][^"\s]*)', "Kit CI pin"),
        "command_manifest_sha": str(contract["command_reference"]["manifest_sha"]),
        "last_protocol_rule": f"{rules[-1][0]} {rules[-1][1]}" if rules else "",
        "last_log_entry": headings[-1] if headings else "",
        # Status counts and the newest id: enough to notice a new or re-classified
        # finding; the adjudication itself stays in the findings file.
        "kit_findings_status": dict(sorted(Counter(f.get("status", "") for f in findings["families"]).items())),
        "kit_findings_latest": max((f["id"] for f in findings["families"] if re.fullmatch(r"KIT-GF-\d+", f["id"])),
                                   key=lambda value: int(value.rsplit("-", 1)[1]), default=""),
    }


def validate_notes(text: str) -> list[str]:
    """Every bullet must say whether it is evidenced, a guess, a next step or the owner's."""
    bullets = [line.strip() for line in text.splitlines() if line.strip().startswith("- ")]
    bad = [line for line in bullets if not line[2:].startswith(NOTE_TAGS)]
    if bad:
        raise HandoffError("untagged note lines (use " + ", ".join(NOTE_TAGS) + "): " + " | ".join(bad))
    return bullets


def _facts_json(facts: dict) -> str:
    """One fact per line, so a diff of two handoffs stays readable."""
    body = ",\n".join(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}" for key, value in facts.items())
    return "{\n" + body + "\n}"


def render(facts: dict, notes: list[str], host_root: str, created: str) -> str:
    kit_root = str(Path(host_root).parent / KIT_FOLDER_NAME)
    start = (
        f"Neuer Claude-Chat für AGP Cockpit. Fordere zuerst Zugriff auf `{host_root}` und "
        f"`{kit_root}` an. Führe dann `python3 scripts/claude_handoff.py check` im Repository aus, "
        "lies die neueste `.local/agp-cockpit/handoff/CLAUDE_HANDOFF_*.md` vollständig und bestätige "
        "den Stand samt jeder Abweichung des Checks, bevor du etwas änderst."
    )
    lines = [
        f"# Claude-Übergabe AGP Cockpit — {created}",
        "",
        "Erzeugt mit `scripts/claude_handoff.py write`. Der Faktenblock stammt aus dem Repository;",
        "`python3 scripts/claude_handoff.py check` vergleicht ihn mit dem aktuellen Stand.",
        "",
        "## Startsatz für den neuen Chat",
        "",
        start,
        "",
        "## Feste Regeln für den Start",
        "",
        f"- Verbundene Ordner sind in einer neuen Cowork-Sitzung nicht vorhanden: `{host_root}` und `{kit_root}` zuerst anfordern.",
        "- Die Session-ID für Commit-Trailer kommt aus der eigenen Umgebung (Systemhinweis), nie aus dieser Datei.",
        "- Was unter „Notizen“ nicht [belegt: …] ist, ist eine Vermutung und wird vor Gebrauch geprüft.",
        "",
        "## Fakten (aus dem Repository)",
        "",
        FACTS_BEGIN,
        "```json",
        _facts_json(facts),
        "```",
        "",
        "## Notizen",
        "",
        *(notes or ["- [Owner] keine Notizen"]),
        "",
    ]
    return "\n".join(lines)


def parse_facts(text: str) -> dict:
    found = re.search(re.escape(FACTS_BEGIN) + r"\s*```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not found:
        raise HandoffError("handoff file has no AGP_CLAUDE_HANDOFF_FACTS_V1 block")
    return json.loads(found.group(1))


def compare(recorded: dict, current: dict) -> list[str]:
    keys = sorted(set(recorded) | set(current))
    return [f"{key}: Übergabe {recorded.get(key)!r} · jetzt {current.get(key)!r}"
            for key in keys if recorded.get(key) != current.get(key)]


def newest_handoff(root: Path) -> Path:
    files = sorted((root / HANDOFF_DIR).glob("CLAUDE_HANDOFF_*.md"))
    if not files:
        raise HandoffError(f"no CLAUDE_HANDOFF_*.md in {root / HANDOFF_DIR}")
    return files[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("--notes", help="markdown file with tagged bullet notes")
    write.add_argument("--host-root", help="repository path on the owner's computer (default: --root)")
    write.add_argument("--output", help="handoff file (default: .local/agp-cockpit/handoff/CLAUDE_HANDOFF_<UTC time>.md)")
    check = sub.add_parser("check")
    check.add_argument("handoff", nargs="?", help="handoff file (default: newest)")
    args = parser.parse_args(argv)
    root = Path(_git(Path(args.root).resolve(), "rev-parse", "--show-toplevel"))
    try:
        facts = collect_facts(root)
        if args.command == "write":
            notes = validate_notes(Path(args.notes).read_text(encoding="utf-8")) if args.notes else []
            created = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
            output = Path(args.output) if args.output else root / HANDOFF_DIR / f"CLAUDE_HANDOFF_{created}.md"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render(facts, notes, args.host_root or str(root), created), encoding="utf-8")
            print(output)
            return 0
        target = Path(args.handoff) if args.handoff else newest_handoff(root)
        differences = compare(parse_facts(target.read_text(encoding="utf-8")), facts)
        print(f"Übergabe: {target}")
        if not differences:
            print("Fakten unverändert.")
            return 0
        print("Abweichungen (seit der Übergabe geändert oder falsch):")
        for line in differences:
            print(f"- {line}")
        return 1
    except HandoffError as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
