"""AGP_KIT_INVOCATION_GUARD_V1 and AGP_LITERAL_APPROVAL_ARGUMENTS_V1 (owner 2026-10-20, options a and b).

The approval was decided on the work order's source only: a call the source analysis cannot
read (``[*BASE, "push-current"]``, a computed argument) ran unchecked, and an exact approval
never covered a line with a computed argument. Now (b) an approval-required call must name its
arguments literally, and (a) every real Kit call meets a guard on PATH that checks it against
the approval before the Kit starts. Paths to the Kit, its package and the guard's names are
refused in the source, because they would pass around the guard.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agp_cockpit.core.file_loop_runner import execute_with_run_next, kit_guard_dir
from agp_cockpit.core.kit_command_catalog import (
    FORBIDDEN_EXECUTE_COMMANDS,
    KitCommandCatalog,
    approval_required_commands,
    command_catalog_violations,
    kit_bypass_violations,
)
from agp_cockpit.core.kit_invocation_guard import (
    LOG_NAME,
    REFUSED_RETURNCODE,
    KitApprovals,
    build_policy,
    decide,
    install,
    read_log,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = KitCommandCatalog.load(ROOT)
PUSH = "agentic-kit transfer push-current"


def _policy(tmp_path, approvals=None, real_kit=None):
    return build_policy(CATALOG, approvals if approvals is not None else KitApprovals(), real_kit=real_kit,
                        log_path=tmp_path / LOG_NAME)


# --- (b) literal arguments ----------------------------------------------------------------------

@pytest.mark.parametrize("source,rejected", [
    ("import subprocess, sys\nsubprocess.run(['agentic-kit', 'transfer', 'remote-next', sys.argv[1], '--json'])\n", True),
    ("import subprocess\nB = 'transfer/a-1'\nsubprocess.run(['agentic-kit', 'transfer', 'remote-next', B, '--json'])\n", False),
    ("import subprocess\nsubprocess.run(['agentic-kit', 'transfer', 'remote-next', 'transfer/a-1', '--json'])\n", False),
    ("import subprocess, sys\nsubprocess.run(['agentic-kit', 'transfer', 'repo-status', '--root', sys.argv[0]])\n", False),
])
def test_an_approval_required_call_must_name_its_arguments_literally(source, rejected):
    violations = command_catalog_violations(source, CATALOG, allow_remote_effects=True)
    assert any("computed argument" in v for v in violations) is rejected, violations


# --- the source refuses paths around the guard ---------------------------------------------------

@pytest.mark.parametrize("source", [
    "import subprocess\nsubprocess.run(['.venv/bin/agentic-kit', 'check'])\n",
    "import subprocess\nsubprocess.run('/usr/local/bin/agentic-kit check', shell=True)\n",
    "import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'agentic_project_kit.cli', 'check'])\n",
    "from agentic_project_kit.cli import app\napp(['check'])\n",
    "import os\nos.environ['AGP_KIT_GUARD_INNER'] = 'x'\n",
])
def test_ways_around_the_guard_are_refused_in_the_source(source):
    assert kit_bypass_violations(source)
    assert command_catalog_violations(source, CATALOG, allow_remote_effects=True)


@pytest.mark.parametrize("source", [
    "import runpy\nrunpy.run_module('agentic_project_kit.cli', run_name='__main__')\n",
    "import importlib\nimportlib.import_module('agentic_project_kit')\n",
    "import subprocess\nsubprocess.run('python3 -m agentic_project_kit check', shell=True)\n",
    "import subprocess\nsubprocess.run('cd x\\n.venv/bin/agentic-kit check\\n', shell=True)\n",
    "import subprocess, sys\nsubprocess.run((sys.executable, '-m', 'agentic_project_kit'))\n",
])
def test_other_module_runs_stay_refused(source):
    """AGP_KIT_GUARD_NOT_FILE_CONTENT_V1: the narrowed rule still sees a module run."""
    assert kit_bypass_violations(source), source


def test_kit_source_paths_and_file_content_are_not_a_module_run():
    """AGP_KIT_GUARD_NOT_FILE_CONTENT_V1 (live 2026-10-25, Kit repository steps 113 and 134)."""
    content = (
        "import subprocess, sys\n"
        "from agentic_project_kit.kit_ci_pin_guard import evaluate\n\n"
        "def test_cli():\n"
        "    done = subprocess.run([sys.executable, '-m', 'agentic_project_kit.cli', 'commands'])\n"
        "    assert Path('.venv/bin/agentic-kit')\n"
    )
    source = (
        "import subprocess\nfrom pathlib import Path\n"
        f"TEST = {content!r}\n"
        "GUARD = 'src/agentic_project_kit/kit_ci_pin_guard.py'\n"
        "Path('tests/test_kit_ci_pin_guard.py').write_text(TEST)\n"
        "subprocess.run(['agentic-kit', 'transfer', 'commit', '--path', GUARD, '-m', 'KIT-GF-086'])\n"
    )
    assert kit_bypass_violations(source) == []


def test_plain_agentic_kit_is_fine():
    assert kit_bypass_violations("import subprocess\nsubprocess.run(['agentic-kit', 'check', '--json'])\n"
                                 "print('run `agentic-kit check` first')\n") == []


# --- the guard's decision -----------------------------------------------------------------------

def test_the_guard_needs_the_same_approvals_as_the_source_analysis(tmp_path):
    """For every manifest command, alone and with --execute: the guard's need equals what the
    source analysis would have asked for the same literal call."""
    policy = _policy(tmp_path)
    for command in CATALOG.commands:
        path = [str(p) for p in command["path"]]
        if " ".join(path) in FORBIDDEN_EXECUTE_COMMANDS:
            continue
        for extra in ([], ["--execute"]):
            args = [*path, *extra, "--json"]
            source = f"import subprocess\nsubprocess.run({json.dumps(['agentic-kit', *args])})\n"
            need, refusal = decide(policy, args)
            assert ({need} if need else set()) == set(approval_required_commands(source, CATALOG)), args
            assert bool(refusal) is bool(need)


def test_names_lines_and_forbidden_executes(tmp_path):
    named = _policy(tmp_path, KitApprovals((PUSH,)))
    assert decide(named, ["transfer", "push-current"]) == (PUSH, "")
    exact = _policy(tmp_path, KitApprovals((PUSH,), (PUSH,)))
    assert decide(exact, ["transfer", "push-current"]) == (PUSH, "")
    need, refusal = decide(exact, ["transfer", "push-current", "--force"])
    assert need == PUSH and "exact approval covers only" in refusal
    assert decide(_policy(tmp_path), ["release-publish", "--version", "1.0", "--dry-run"]) == ("", "")
    assert decide(_policy(tmp_path), ["work", "rescue", "--json"]) == ("", "")
    assert decide(_policy(tmp_path), ["work", "rescue", "--execute"])[0] == "agentic-kit work rescue --execute"
    everything = _policy(tmp_path, KitApprovals(("agentic-kit workspace ci-update --execute",)))
    assert "never runs" in decide(everything, ["workspace", "ci-update", "--execute"])[1]
    assert decide(_policy(tmp_path), ["check", "--json"]) == ("", "")
    assert decide(_policy(tmp_path), ["--version"]) == ("", "")


# --- the guard as a program ---------------------------------------------------------------------

def _fake_kit(tmp_path):
    record = tmp_path / "fake-calls.jsonl"
    fake = tmp_path / "kitbin" / "agentic-kit"
    fake.parent.mkdir()
    fake.write_text(
        f"#!{sys.executable}\nimport json, os, subprocess, sys\n"
        f"open({str(record)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:3] == ['transfer', 'remote-work-start']:\n"
        "    sys.exit(subprocess.run(['agentic-kit', 'transfer', 'push-current']).returncode)\n"
        "sys.exit(7)\n"
    )
    fake.chmod(0o755)
    return fake, record


def _run(directory, *args):
    env = {**os.environ, "PATH": os.pathsep.join([str(directory), os.environ.get("PATH", "")])}
    env.pop("AGP_KIT_GUARD_INNER", None)
    return subprocess.run(["agentic-kit", *args], env=env, capture_output=True, text=True, check=False)


def _calls(record):
    return [json.loads(line) for line in record.read_text().splitlines()] if record.exists() else []


def test_an_unapproved_call_never_starts_the_kit(tmp_path):
    fake, record = _fake_kit(tmp_path)
    directory = install(tmp_path / "guard", _policy(tmp_path, real_kit=fake), interpreter=sys.executable)
    refused = _run(directory, "transfer", "push-current")
    assert refused.returncode == REFUSED_RETURNCODE and "AGP_KIT_GUARD_REFUSED" in refused.stderr
    assert _calls(record) == []
    assert _run(directory, "check", "--json").returncode == 7
    assert _calls(record) == [["check", "--json"]]
    log = read_log(tmp_path / LOG_NAME)
    assert [r["decision"] for r in log] == ["REFUSED", "RUN"] and log[0]["need"] == PUSH


def test_an_approved_call_runs_and_the_kit_may_call_itself(tmp_path):
    fake, record = _fake_kit(tmp_path)
    start = "agentic-kit transfer remote-work-start"
    policy = _policy(tmp_path, KitApprovals((start,), (f"{start} feat/x",)), real_kit=fake)
    directory = install(tmp_path / "guard", policy, interpreter=sys.executable)
    assert _run(directory, "transfer", "remote-work-start", "feat/y").returncode == REFUSED_RETURNCODE
    assert _run(directory, "transfer", "remote-work-start", "feat/x").returncode == 7
    assert _calls(record) == [["transfer", "remote-work-start", "feat/x"], ["transfer", "push-current"]]
    assert [r["inner"] for r in read_log(tmp_path / LOG_NAME)] == [False, False, True]


def test_an_interpreter_path_with_spaces_works(tmp_path):
    spaced = tmp_path / "with space"
    spaced.mkdir()
    (spaced / "python").symlink_to(sys.executable)
    fake, _ = _fake_kit(tmp_path)
    directory = install(tmp_path / "guard dir", _policy(tmp_path, real_kit=fake), interpreter=str(spaced / "python"))
    assert _run(directory, "check").returncode == 7


# --- through run_next ---------------------------------------------------------------------------

def test_run_next_puts_the_guard_first_and_refuses_a_hidden_remote_call(tmp_path, monkeypatch):
    fake, record = _fake_kit(tmp_path)
    monkeypatch.setenv("AGP_COCKPIT_KIT_BINARY", str(fake))
    manifest = tmp_path / "docs/reference/agentic-kit-commands.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"meta": {"manifest_sha": "x"}, "commands": [
        c for c in CATALOG.commands if c["path"] in (["transfer", "push-current"], ["check"])]}))
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text((ROOT / "Download/run_next.py").read_text())
    command = download / "001_hidden.py"
    # The source analysis sees only ["agentic-kit"]; the remote call is assembled at run time.
    command.write_text(
        'import argparse, json, subprocess\nfrom pathlib import Path\n'
        'BASE = ["agentic-kit"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser()\n'
        '    parser.add_argument("--self-test", action="store_true")\n'
        '    if parser.parse_args().self_test:\n'
        '        return\n'
        '    rc = subprocess.run([*BASE, "transfer", "push-current"]).returncode\n'
        '    Path(__file__).with_name("001_hidden_return_bundle.json").write_text(json.dumps({"rc": rc}))\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    result = execute_with_run_next(tmp_path, command)
    assert json.loads(result.return_bundle.read_text())["rc"] == REFUSED_RETURNCODE, result.stdout + result.stderr
    assert _calls(record) == []
    assert read_log(kit_guard_dir(tmp_path, 1) / LOG_NAME)[0]["need"] == PUSH


def test_the_live_evidence_says_what_was_proven_where():
    evidence = json.loads((ROOT / "docs/validation/evidence/kit-guard-live-2026-10-20.json").read_text())
    approved = evidence["approved_call_through_chatgpt"]
    assert approved["step"] == 2112 and approved["result"]["returncode"] == 0
    assert [r["decision"] for r in approved["guard_log"]] == ["RUN"]
    probe = evidence["refused_call_local_probe"]
    assert probe["result"] == "PASS" and probe["hidden"]["returncode"] == REFUSED_RETURNCODE
    assert probe["hidden"]["kit_started"] is False and probe["hidden"]["guard_log"] == ["REFUSED"]
    assert "not observable through ChatGPT" in evidence["refused_call_through_chatgpt"]["result"]
    assert evidence["verifies"] == {}
