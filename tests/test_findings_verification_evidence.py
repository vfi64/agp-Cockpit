"""AGP_FINDINGS_VERIFIED_EVIDENCE_V1 (2026-10-13): VERIFIED_FIXED needs dated evidence; from release 0.2.5 on,
retest evidence is a committed file under docs/validation/evidence/ that names the families it verifies."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = json.loads((ROOT / "docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json").read_text(encoding="utf-8"))
FAMILIES = {f["id"]: f for f in LEDGER["families"]}
EVIDENCE = sorted((ROOT / "docs/validation/evidence").glob("*.json"))
CITED = re.compile(r"docs/validation/evidence/[\w.\-]+\.json")


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def test_every_verified_family_carries_dated_evidence():
    for fid, family in FAMILIES.items():
        if family["status"] == "VERIFIED_FIXED":
            assert family.get("fixed_in"), fid
            assert re.match(r"20\d\d-\d\d-\d\d ", str(family.get("verified_by") or "")), fid


def test_cited_evidence_files_exist_and_name_the_family():
    for fid, family in FAMILIES.items():
        for cited in CITED.findall(str(family.get("verified_by") or "")):
            evidence = json.loads((ROOT / cited).read_text(encoding="utf-8"))
            assert fid in evidence["verifies"], (fid, cited)
            assert _version(evidence["kit_version"]) >= _version(family["fixed_in"]), (fid, cited)


def test_every_evidence_file_is_used_and_consistent():
    assert EVIDENCE, "no evidence file"
    for path in EVIDENCE:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        assert evidence["schema_version"] == 1 and evidence["kind"] == "agp_kit_retest_evidence", path.name
        rel = path.relative_to(ROOT).as_posix()
        for fid in evidence["verifies"]:
            family = FAMILIES[fid]
            assert family["status"] == "VERIFIED_FIXED", fid
            assert rel in family["verified_by"], fid
        for key in evidence.get("not_verified", {}):
            for fid in _ids(key):
                # a later evidence file may verify it (Kit 1.1.5 verified KIT-GF-063 and others)
                assert FAMILIES[fid]["status"] != "VERIFIED_FIXED" or rel not in FAMILIES[fid]["verified_by"], fid


def test_release_025_evidence_matches_what_it_claims():
    evidence = json.loads((ROOT / "docs/validation/evidence/release-run-0.2.5.json").read_text(encoding="utf-8"))
    run = evidence["release_run"]
    approval = run["approvals"][0]
    assert (approval["step_id"], approval["approved_by"], approval["approval_mode"]) == ("B4", "vfi64", "upfront")
    assert approval["consent_source"].startswith("AGP Cockpit start click: Release 0.2.5")
    assert run["publication_policy"] == "github" and run["release_branch"] == "release/0.2.5"
    assert run["planned_steps"] == ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "C1", "C2", "C4"]
    assert run["c1"]["release_publish_status"] == "PASS" and "SKIP" in run["c1"]["checks"].values()   # KIT-GF-069
    assert evidence["release_publish"]["status"] == "PASS" and evidence["release_publish"]["tag"] == "v0.2.5"


def _ids(key: str) -> list[str]:
    """``KIT-GF-003, 009`` names KIT-GF-003 and KIT-GF-009."""
    first, *rest = [part.strip() for part in key.split(",")]
    prefix = first.rsplit("-", 1)[0]
    return [first, *(f"{prefix}-{part}" for part in rest)]

