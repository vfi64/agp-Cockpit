"""AGP_RELEASE_RUN_AUTONOMY_V1 (owner 2026-10-08 „vollautonom“, 2026-10-13 „1b“).

With release.approval: upfront a release is one Kit orchestrator run: the start click is the consent the
Kit records at gate B4 (KIT-GF-061); release branches keep release/<version> (KIT-GF-065, Kit 1.0.22).
"""
import subprocess
from pathlib import Path

import yaml

from agp_cockpit.core import release_policy as rp
from agp_cockpit.core import standard_tasks as st

ROOT = Path(__file__).resolve().parents[1]
TASK = st.BY_KEY["release"]


def _repo(tmp_path, release: dict) -> Path:
    root = tmp_path / "repo"
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic/config.yaml").write_text(yaml.safe_dump({"publication": "github", "release": release}),
                                              encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nversion = "0.2.4"\n', encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "vfi64"], check=True)
    return root


def test_the_cockpit_declares_up_front_consent_and_its_branch_names():
    config = yaml.safe_load((ROOT / ".agentic/config.yaml").read_text(encoding="utf-8"))
    assert config["release"]["approval"] == "upfront"
    assert config["release"]["branch_prefix"] == "release/"
    assert st.release_run_route(ROOT)


def test_up_front_consent_runs_the_release_through_the_kit_alone(tmp_path):
    root = _repo(tmp_path, {"approval": "upfront", "branch_prefix": "release/"})
    assert TASK.scope(root, {"version": "0.2.5"}) == st.RELEASE_RUN_SCOPE
    assert TASK.scope(root, {"version": "0.2.4"}) == st.RELEASE_RUN_SCOPE     # a stopped run resumes
    prompt = TASK.prompt(root, {"version": "0.2.5"})
    assert "end-to-end release orchestrator" in prompt and "branch release/0.2.5" in prompt
    assert '--approved-by\n   "vfi64"' in prompt and "AGP Cockpit start click: Release 0.2.5" in prompt
    assert "Do not ask NEEDS_HUMAN for this consent" in prompt and "Phase 2" not in prompt
    assert "summary-line option" in prompt and "agentic-kit release" not in prompt   # the remote side chooses
    contract = TASK.contract(root, {"version": "0.2.5"})
    assert "up-front consent" in contract["goal"] and "records it" in contract["constraints"][1]


def test_without_the_declaration_the_two_phase_release_stays(tmp_path):
    root = _repo(tmp_path, {})
    assert TASK.scope(root, {"version": "0.2.5"}) == st._release_scope()
    assert TASK.scope(root, {"version": "0.2.4"}) == st.RELEASE_RESUME_SCOPE
    prompt = TASK.prompt(root, {"version": "0.2.5"})
    assert "Phase 2 — tag publication (always asks)" in prompt and "release run" not in prompt


def test_a_live_release_run_must_name_signature_approver_and_consent_source():
    policy = {"publication": "github", "signed_kit_commands": {"commands": ["agentic-kit release run"]}}
    names = {"agentic-kit release run"}
    plan = 'run(["agentic-kit", "release", "run", "--version", "0.2.5", "--json"])'
    live = plan.replace('"--json"', '"--execute", "--expected-signature", "s", "--json"')
    signed = live.replace('"--json"', '"--approved-by", "vfi64", "--consent-source", "click", "--json"')
    root = ROOT
    assert rp._signed_release_violations(plan, root, policy, names, None) == []
    assert "--approved-by" in rp._signed_release_violations(live, root, policy, names, None)[0]
    assert rp._signed_release_violations(signed, root, policy, names, None) == []


def test_the_policy_names_the_release_run_as_a_signed_route():
    import json
    policy = json.loads((ROOT / "docs/planning/release_policy.json").read_text(encoding="utf-8"))
    assert "agentic-kit release run" in policy["signed_kit_commands"]["commands"]
    assert policy["approval"]["status"].startswith("active since 2026-10-13")


def test_gate_b4_paths_are_the_release_files_and_the_kits_own_state():
    """AGP_RELEASE_GATE_PATHS_V1: release 0.2.5 stopped at B4 because the prompt allowed only the release files,
    while the Kit's branch completion also refreshes its handoff state under .agentic/state/."""
    files = st.release_gate_files(ROOT)
    assert {"CHANGELOG.md", "pyproject.toml", "src/agp_cockpit/version.py",
            "chrome_extension/build_identity.js", "docs/releases/versions.json"} == set(files)
    gate_025 = [".agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md",
                ".agentic/state/handoff/packages/latest/execution_contract.json",
                ".agentic/state/handoff/reports/", *files]
    assert st.release_gate_differences(ROOT, gate_025) == []
    assert st.release_gate_differences(ROOT, [*gate_025, "src/agp_cockpit/app.py"]) == ["src/agp_cockpit/app.py"]
    assert st.release_gate_differences(ROOT, [".agentic/config.yaml"]) == [".agentic/config.yaml"]
    prompt = TASK.prompt(ROOT, {"version": "0.2.6"})
    assert "AGP_RELEASE_GATE_PATHS_V1" in prompt and ".agentic/state/" in prompt
    assert all(f in prompt for f in files)


def test_gate_b4_files_follow_the_declared_version_anchors(tmp_path):
    root = _repo(tmp_path, {"approval": "upfront", "version_anchors": [{"path": "app/VERSION"}, {"kind": "x"}]})
    assert st.release_gate_files(root) == ("CHANGELOG.md", "pyproject.toml", "app/VERSION")
    assert st.release_gate_files(_repo(tmp_path / "b", {"approval": "upfront"})) == ("CHANGELOG.md", "pyproject.toml")
