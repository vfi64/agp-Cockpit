"""AGP_GUIDED_RECOVERY_V1, AGP_FOLLOWUP_PR_CI_V1, AGP_FULL_HEAD_SHA_V1, AGP_COMPACT_LAGE_V1
(owner 2026-10-06: „Bei solchen Problemen sollte der Nutzer besser auf dem Lösungsweg geführt
werden“; „der Bildschirmplatz ist endlich“)."""

import json
import subprocess
from pathlib import Path

from agp_cockpit.core import guidance
from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.kit_command_catalog import short_head_sha_violations

ROOT = Path(__file__).resolve().parents[1]

# Live 2026-10-05, PR #243 run #705: browser never got a runner, the aggregate job failed.
LIVE_705 = [{"__typename": "CheckRun", "name": "python", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"__typename": "CheckRun", "name": "browser", "status": "COMPLETED", "conclusion": "CANCELLED"},
            {"__typename": "CheckRun", "name": "agentic-gate", "status": "COMPLETED", "conclusion": "FAILURE"}]


def state(name, recommended=None, reasons=(), **facts):
    return rs.RepoState(name, "s", recommended, rs.OFFERED[name], tuple(reasons),
                        rs.RepoFacts(root="", is_git=True, **facts))


def test_followup_ci_is_classified_like_the_live_cases():
    assert rs.classify_checks(LIVE_705) == rs.FOLLOWUP_RUNNER
    assert rs.classify_checks([{"conclusion": "FAILURE"}, {"conclusion": "SUCCESS"}]) == rs.FOLLOWUP_FAILED
    assert rs.classify_checks([{"status": "QUEUED", "conclusion": ""}]) == rs.FOLLOWUP_PENDING
    assert rs.classify_checks([]) == rs.FOLLOWUP_PENDING
    assert rs.classify_checks([{"status": "COMPLETED", "conclusion": "SUCCESS"}]) == rs.FOLLOWUP_GREEN


def test_followup_pull_request_reads_only_the_kits_branch(monkeypatch, tmp_path):
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "gh")
    prs = [{"number": 9, "headRefName": "feat/x", "url": "u9", "statusCheckRollup": []},
           {"number": 243, "headRefName": "docs/post-pr242-successor-package-refresh",
            "url": "https://github.com/o/r/pull/243", "statusCheckRollup": LIVE_705}]
    seen = []

    def runner(argv, **_kw):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(prs), "")
    assert rs.followup_pull_request(tmp_path, runner=runner) == (243, rs.FOLLOWUP_RUNNER,
                                                                 "https://github.com/o/r/pull/243")
    assert seen[0][:4] == ["gh", "pr", "list", "--state"]       # read-only
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "none")
    assert rs.followup_pull_request(tmp_path, runner=runner) == (None, "", "")


def test_lage_names_the_followup_and_fits_one_line():
    s = state(rs.STOERUNG, rs.ABSCHLIESSEN, branch="main", head="73691f3a86e4", origin_main="73691f3a86e4",
              kit_version="1.0.18", post_merge="NOT_PASS", followup_pr=243, followup_ci="RUNNER")
    assert "Folge-PR #243: CI von GitHub abgebrochen" in rs.describe(s)
    line = rs.summary_line(s)
    assert "\n" not in line and "Folge-PR #243" in line and "main @ 73691f3a · synchron" in line


def test_the_way_out_of_the_live_2026_10_05_case_step_by_step():
    followup = {"branch": "main", "head": "a", "origin_main": "a", "post_merge": "NOT_PASS", "followup_pr": 243,
                "followup_url": "https://github.com/o/r/pull/243"}
    runner = guidance.steps(state(rs.STOERUNG, rs.ABSCHLIESSEN, followup_ci="RUNNER", **followup))
    assert "Re-run failed jobs" in runner[0] and "PR #243" in runner[0] and runner[-1].startswith("Dann „Abschließen“")
    assert guidance.steps(state(rs.STOERUNG, rs.ABSCHLIESSEN, followup_ci="PENDING", **followup))[0].startswith("Warten")
    assert "Wiederherstellen" in guidance.steps(state(rs.STOERUNG, rs.ABSCHLIESSEN, followup_ci="FAILED", **followup))[1]
    assert guidance.steps(state(rs.STOERUNG, rs.ABSCHLIESSEN, followup_ci="GREEN", **followup))[0].startswith("„Abschließen“")
    # The crashed fallback left changes: recovery first.
    assert guidance.steps(state(rs.IN_ARBEIT, rs.ABSCHLIESSEN, branch="docs/x", changes=("a",)),
                          recover_offered=True)[0].startswith("„Wiederherstellen“")
    # The decision: what to check before approving.
    assert "Freigeben" in guidance.steps(None, decision_pending=True)[1]
    # The empty leftover branch afterwards: the owner's own way back to main.
    left = guidance.steps(state(rs.IN_ARBEIT, rs.ARBEITEN, branch="docs/post-pr242-handoff-refresh", head="a",
                                origin_main="a", own_commits=0), repository="/r")
    assert "keine Arbeit" in left[0] and "cd /r && git switch main" in left[1]
    # AGP_FRESH_BRANCH_V1 (live 2026-10-06): right after „Arbeit beginnen“ the empty branch is expected.
    fresh = guidance.steps(state(rs.IN_ARBEIT, rs.ARBEITEN, branch="fix/gf050b-x", head="a", origin_main="a",
                                 own_commits=0), repository="/r")
    assert fresh == ["Branch fix/gf050b-x ist bereit — „Arbeiten“ für den Auftrag, danach „Abschließen“."]
    assert not any("git switch main" in line for line in fresh)
    assert guidance.steps(state(rs.BEREIT, rs.ARBEIT_BEGINNEN, branch="main")) == []


def test_guidance_for_blocks_and_unclear_states():
    assert "Neu bauen" in guidance.steps(None, block_reason="Blockiert — Neuer Build vorhanden (r4), App …")[0]
    unclear = guidance.steps(state(rs.UNKLAR, rs.LAGEBERICHT, reasons=("gh ist nicht angemeldet (gh auth login).",)))
    assert "gh auth login" in unclear[0] and "Aktualisieren" in unclear[1]
    assert len(guidance.text(["a", "b", "c", "d"]).splitlines()) == guidance.MAX_STEPS


def test_short_head_sha_is_rejected_before_the_run():
    short = 'argv = ["agentic-kit", "transfer", "pr-complete", "242", "--expected-head-sha", "c4fcb0199735"]\n'
    assert "AGP_FULL_HEAD_SHA_V1" in short_head_sha_violations(short)[0]
    full = short.replace("c4fcb0199735", "c4fcb0199735130f5e8a6b6c7676e54c1bbf9726")
    assert short_head_sha_violations(full) == []
    assert short_head_sha_violations('argv = ["agentic-kit", "x", "--expected-head-sha=abc"]\n')
    assert short_head_sha_violations('argv = ["agentic-kit", "x", "--expected-head-sha", head]\n') == []


def test_panel_layout_is_compact():
    panel = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    assert "Wiederkehrende, geprüfte Arbeitsaufträge" not in panel
    assert 'font=("TkDefaultFont", 18, "bold")' not in panel
    assert "self.decision_frame.grid(row=1, column=0" in panel     # right under the Lage
    assert "wraplength=760" not in panel and "wraplength=700" not in panel
