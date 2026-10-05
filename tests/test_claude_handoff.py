"""AGP_CLAUDE_HANDOFF_FACTS_V1: the Claude handoff facts come from the repository."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("claude_handoff", ROOT / "scripts" / "claude_handoff.py")
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    files = {
        "src/agp_cockpit/version.py": 'APP_VERSION = "0.1.1"\nBRIDGE_BUILD_ID = "release-0.1.1-r7"\n',
        "chrome_extension/build_identity.js": 'globalThis.AGP_EXTENSION_BUILD_ID = "release-0.1.1-r7";\n',
        ".github/workflows/agentic-gate.yaml": '      - run: python -m pip install "agentic-project-kit==1.0.16"\n',
        ".agentic/state/handoff/packages/latest/execution_contract.json":
            json.dumps({"command_reference": {"manifest_sha": "9529749193c5"}}),
        "docs/planning/COMMUNICATION_PROTOCOL.md":
            "66. One task (`AGP_ONE_TASK_ALL_TABS_V1`, R5): x\n67. Attachments (`AGP_RESULT_ATTACHMENT_COMPOSER_BOUND_V1`,\n",
        "docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md": "# Log\n\n## 2026-10-05 — r6\n",
        "docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json": json.dumps({"families": [
            {"id": "KIT-GF-042", "status": "OPEN"}, {"id": "KIT-GF-043", "status": "OPEN"},
            {"id": "KIT-GF-RULE-REGISTRY-BOOTSTRAP", "status": "CONFIRMED"}]}),
        ".gitignore": ".local/\n",
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    _git(tmp_path, "tag", "-a", "v0.1.1", "-m", "v0.1.1")
    return tmp_path


def test_facts_are_derived_from_the_repository(repo):
    facts = handoff.collect_facts(repo)
    assert facts["branch"] == "main"
    assert facts["worktree_clean"] is True
    assert facts["latest_tag"] == "v0.1.1"
    assert facts["bridge_build_id"] == facts["extension_build_id"] == "release-0.1.1-r7"
    assert facts["kit_ci_pin"] == "1.0.16"
    assert facts["command_manifest_sha"] == "9529749193c5"
    assert facts["last_protocol_rule"] == "67 AGP_RESULT_ATTACHMENT_COMPOSER_BOUND_V1"
    assert facts["last_log_entry"] == "2026-10-05 — r6"
    assert facts["kit_findings_status"] == {"CONFIRMED": 1, "OPEN": 2}
    assert facts["kit_findings_latest"] == "KIT-GF-043"


def test_write_then_check_is_clean_and_carries_the_start_rules(repo, capsys):
    assert handoff.main(["--root", str(repo), "write", "--host-root", "/Users/x/GitHub/agp-Cockpit"]) == 0
    written = Path(capsys.readouterr().out.strip())
    text = written.read_text(encoding="utf-8")
    assert "/Users/x/GitHub/agentic-project-kit" in text
    assert "Session-ID für Commit-Trailer kommt aus der eigenen Umgebung" in text
    assert handoff.main(["--root", str(repo), "check"]) == 0
    assert "Fakten unverändert." in capsys.readouterr().out


def test_check_reports_every_drift(repo, capsys):
    out = repo / "h.md"
    assert handoff.main(["--root", str(repo), "write", "--output", str(out)]) == 0
    (repo / "src/agp_cockpit/version.py").write_text(
        'APP_VERSION = "0.1.1"\nBRIDGE_BUILD_ID = "release-0.1.1-r8"\n', encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "r8")
    capsys.readouterr()
    assert handoff.main(["--root", str(repo), "check", str(out)]) == 1
    report = capsys.readouterr().out
    assert "bridge_build_id: Übergabe 'release-0.1.1-r7' · jetzt 'release-0.1.1-r8'" in report
    assert "head:" in report


def test_untagged_notes_are_rejected(repo, tmp_path, capsys):
    notes = tmp_path / "notes.md"
    notes.write_text("- [belegt: bridge.log 08:25] ok\n- der Text stand noch im Feld\n", encoding="utf-8")
    assert handoff.main(["--root", str(repo), "write", "--notes", str(notes)]) == 2
    assert "untagged note lines" in capsys.readouterr().err


def test_tagged_notes_are_kept(repo, tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text("- [Vermutung] Fokusverlust durch Layoutwechsel\n- [Nächster Schritt] Slice B\n",
                     encoding="utf-8")
    out = repo / "h.md"
    assert handoff.main(["--root", str(repo), "write", "--notes", str(notes), "--output", str(out)]) == 0
    assert "- [Vermutung] Fokusverlust durch Layoutwechsel" in out.read_text(encoding="utf-8")


def test_a_file_without_facts_block_is_an_error():
    with pytest.raises(handoff.HandoffError):
        handoff.parse_facts("# hand-written handoff\n")
