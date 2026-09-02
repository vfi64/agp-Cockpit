from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import platform
import subprocess
from typing import Any


@dataclass(frozen=True)
class KitErrorEvidence:
    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str


@dataclass(frozen=True)
class KitErrorReport:
    schema_version: int
    report_id: str
    created_at: str
    classification: str
    title: str
    summary: str
    repository_root: str
    branch: str
    head: str
    kit_version: str
    python_version: str
    platform: str
    workflow_phase: str
    expected_behavior: str
    observed_behavior: str
    reproduction_steps: list[str]
    workaround_used: bool
    workaround_description: str
    evidence: list[KitErrorEvidence]
    suspected_component: str
    impact: str
    regression_risk: str
    notes: list[str]


def _git(root: Path, *args: str) -> str:
    cp = subprocess.run(
        ["/usr/bin/git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return cp.stdout.strip() if cp.returncode == 0 else ""


def _kit_version(root: Path) -> str:
    binary = root / ".venv/bin/agentic-kit"
    if not binary.exists():
        return "unknown"
    cp = subprocess.run(
        [str(binary), "--version"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    text = (cp.stdout or cp.stderr).strip()
    return text or "unknown"


def build_kit_error_report(
    *,
    repository_root: Path,
    classification: str,
    title: str,
    summary: str,
    workflow_phase: str,
    expected_behavior: str,
    observed_behavior: str,
    reproduction_steps: list[str],
    evidence: list[KitErrorEvidence],
    suspected_component: str = "unknown",
    impact: str = "",
    regression_risk: str = "",
    workaround_used: bool = False,
    workaround_description: str = "",
    notes: list[str] | None = None,
) -> KitErrorReport:
    root = repository_root.resolve()
    now = datetime.now(timezone.utc)
    seed = "|".join([
        now.isoformat(),
        classification,
        title,
        _git(root, "rev-parse", "HEAD"),
    ])
    report_id = "KIT-" + sha256(seed.encode("utf-8")).hexdigest()[:12].upper()

    return KitErrorReport(
        schema_version=1,
        report_id=report_id,
        created_at=now.isoformat(),
        classification=classification,
        title=title,
        summary=summary,
        repository_root=str(root),
        branch=_git(root, "branch", "--show-current"),
        head=_git(root, "rev-parse", "HEAD"),
        kit_version=_kit_version(root),
        python_version=platform.python_version(),
        platform=platform.platform(),
        workflow_phase=workflow_phase,
        expected_behavior=expected_behavior,
        observed_behavior=observed_behavior,
        reproduction_steps=list(reproduction_steps),
        workaround_used=workaround_used,
        workaround_description=workaround_description,
        evidence=list(evidence),
        suspected_component=suspected_component,
        impact=impact,
        regression_risk=regression_risk,
        notes=list(notes or []),
    )


def _markdown(report: KitErrorReport) -> str:
    lines = [
        f"# Kit Error Report {report.report_id}",
        "",
        f"- Created: {report.created_at}",
        f"- Classification: {report.classification}",
        f"- Branch: {report.branch}",
        f"- HEAD: {report.head}",
        f"- Kit version: {report.kit_version}",
        f"- Workflow phase: {report.workflow_phase}",
        f"- Suspected component: {report.suspected_component}",
        "",
        "## Summary",
        report.summary,
        "",
        "## Expected behavior",
        report.expected_behavior,
        "",
        "## Observed behavior",
        report.observed_behavior,
        "",
        "## Impact",
        report.impact or "Not specified.",
        "",
        "## Regression risk",
        report.regression_risk or "Not specified.",
        "",
        "## Reproduction",
    ]
    for index, step in enumerate(report.reproduction_steps, 1):
        lines.append(f"{index}. {step}")

    lines += ["", "## Evidence"]
    for item in report.evidence:
        lines += [
            "",
            "```text",
            "$ " + " ".join(item.command),
            f"RC={item.returncode}",
            "--- stdout ---",
            item.stdout.rstrip() or "<empty>",
            "--- stderr ---",
            item.stderr.rstrip() or "<empty>",
            "```",
        ]

    lines += [
        "",
        "## Workaround",
        (
            report.workaround_description
            if report.workaround_used
            else "No workaround used."
        ),
        "",
        "## Notes",
    ]
    if report.notes:
        lines += [f"- {note}" for note in report.notes]
    else:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def write_kit_error_report(
    report: KitErrorReport,
    *,
    output_root: Path,
) -> tuple[Path, Path]:
    target = output_root / report.report_id
    target.mkdir(parents=True, exist_ok=False)

    json_path = target / "report.json"
    md_path = target / "report.md"

    payload: dict[str, Any] = asdict(report)
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(
        _markdown(report),
        encoding="utf-8",
    )
    return json_path, md_path
