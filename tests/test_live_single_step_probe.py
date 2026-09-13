from pathlib import Path

SOURCE = Path(
    "chrome_extension/content.js"
).read_text(encoding="utf-8")


def test_live_probe_has_exact_fixed_command():
    assert 'title:"061 LIVE READ-ONLY PROBE"' in SOURCE
    assert 'cwd:"/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit"' in SOURCE
    assert 'argv:["/usr/bin/git","status","--short"]' in SOURCE
    assert 'execution_mode:"LIVE"' in SOURCE
    assert 'run_mode:"SINGLE_STEP"' in SOURCE


def test_live_probe_guard_runs_before_local_submit():
    guard = SOURCE.index(
        "assertExactLiveProbeWorkOrder(text);"
    )
    submit = SOURCE.index(
        '"/v1/protocol/execute"',
        guard,
    )
    assert guard < submit
    assert "timeout > 30" in SOURCE
    assert 'data.kind !== "generic"' in SOURCE
    assert "work order differs from exact read-only git status contract" in SOURCE


def test_live_bootstrap_is_mode_aware():
    assert 'mission.execution_mode === "LIVE"' in SOURCE
    assert "This mission is LIVE." in SOURCE


def test_existing_loop_and_completion_guards_remain():
    assert "ASSISTANT_RESPONSE_COMPLETE" in SOURCE
    assert "stablePollsRequired: 3" in SOURCE
    assert "maxTurns: 40" in SOURCE
    assert "maxErrors: 3" in SOURCE
