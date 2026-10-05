"""AGP_AMPEL_V1, AGP_SHORT_RESULT_LINE_V1, AGP_FRESHNESS_LINE_V1 (owner 2026-10-05)."""

from pathlib import Path

from agp_cockpit.core import ampel as a
from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.standard_task_progress import (
    counters_text,
    describe_standard_task_progress,
    split_verdict,
)

ROOT = Path(__file__).resolve().parents[1]

# Live 2026-10-05 (PR #236, step 1773): the result line as the panel showed it, cut by „…“.
LIVE_1773 = ("Fertig (Remote): CI grün geprüft (PR #236 gemergt, main 0fafe526d1eb) · Step 1773 passed: "
             "agentic-kit transfer pr-create-complete returned PASS and reported the PR create-complete "
             "lifecycle complete. Cockpit-verified facts show PR #236 MERGED, current origin/main 0fafe526")


def state(name, recommended=None, summary="s", branch="main"):
    return rs.RepoState(name, summary, recommended, rs.OFFERED[name], (), rs.RepoFacts(root="", branch=branch))


def test_each_repository_state_has_one_light_with_a_word():
    assert a.ampel(state(rs.BEREIT)).color == a.GRUEN
    assert a.ampel(state(rs.IN_ARBEIT, branch="feat/x")).color == a.GELB
    assert "feat/x" in a.ampel(state(rs.IN_ARBEIT, branch="feat/x")).reason
    assert a.ampel(state(rs.LAEUFT)).color == a.GELB
    assert a.ampel(state(rs.KEIN_KIT)).color == a.GELB
    assert a.ampel(state(rs.UNKLAR, summary="Der Zustand ist nicht vollständig lesbar.")).color == a.ROT
    assert a.ampel(state(rs.STOERUNG, rs.WIEDERHERSTELLEN, "main ist nicht im sauberen Ausgangszustand.")).color == a.ROT
    # AGP_FINISH_OPEN_FOLLOWUP_V1: only the Kit's post-merge follow-up is open.
    assert a.ampel(state(rs.STOERUNG, rs.ABSCHLIESSEN)).color == a.GELB
    assert a.ampel(None).color == a.GRAU
    for light in (a.ampel(state(rs.BEREIT)), a.ampel(None), a.ampel(state(rs.UNKLAR))):
        assert light.text.split(" — ")[0] in ("Grün", "Gelb", "Rot", "Grau") and light.reason


def test_the_most_urgent_signal_wins():
    ready = state(rs.BEREIT)
    assert a.ampel(ready, block_reason="Blockiert — Neuer Build vorhanden (r2). Cockpit neu starten.").color == a.ROT
    assert "Neuer Build vorhanden (r2)" in a.ampel(ready, block_reason="Blockiert — Neuer Build vorhanden (r2). x").reason
    assert a.ampel(ready, lage_error="boom").color == a.ROT
    assert a.ampel(state(rs.IN_ARBEIT), decision_pending=True).reason == "deine Entscheidung ist gefragt"
    assert a.ampel(state(rs.IN_ARBEIT), recover_offered=True).color == a.ROT
    assert a.ampel(state(rs.IN_ARBEIT), task_outcome="HUMAN_REQUIRED").color == a.ROT
    # A repository that is clean again is not red because of an old task.
    assert a.ampel(ready, task_outcome="HUMAN_REQUIRED").color == a.GRUEN


def test_live_1773_result_line_is_short_and_german():
    verdict, remote = split_verdict(LIVE_1773)
    assert verdict == "CI grün geprüft (PR #236 gemergt, main 0fafe526d1eb)"
    assert remote.startswith("Step 1773 passed")
    progress = describe_standard_task_progress(
        mission_id="m", task_status={"state": "VERIFIED_COMPLETE"},
        bridge_status={"mission": {"mission_id": "m", "state": "DONE", "turn_count": 1, "step_count": 1,
                                   "last_summary": LIVE_1773}})
    assert progress.text == "Fertig ✓ — CI grün geprüft (PR #236 gemergt, main 0fafe526d1eb) · 1 Remote-Turn · 1 Schritt."
    assert "passed" not in progress.text and "…" not in progress.text
    assert progress.detail.startswith("Step 1773 passed")


def test_verifier_verdict_stays_and_counters_are_german():
    verdict, remote = split_verdict("CI grün geprüft (PR #9 gemergt, main abc) · done · Lokal geprüft (Tag v1 ok)")
    assert verdict == "CI grün geprüft (PR #9 gemergt, main abc) · Lokal geprüft (Tag v1 ok)" and remote == "done"
    assert counters_text(1, 1) == "1 Remote-Turn · 1 Schritt"
    assert counters_text(2, 3) == "2 Remote-Turns · 3 Schritte"


def test_panel_and_header_wiring():
    panel = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    assert "AGP_AMPEL_V1" in panel and "self.update_ampel()" in panel and "Meldung der Remote-Seite" in panel
    window = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "AGP_FRESHNESS_LINE_V1" in window and "wraplength=900" in window
    assert 'f"{base} · ⚠ {freshness.message}"' not in window
