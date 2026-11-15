"""AGP_RELEASE_RULE_CALLS_V1 (workflow-friction plan C1, V10).

The release rule reads the calls in the syntax tree, not the text: a flag in a docstring or a
pull-request body no longer turns a dry run into a live run, and every rejection names the call and
its line. An execute flag that stands on its own in the code still counts, because it can be
appended at run time.
"""
from pathlib import Path

import pytest

from agp_cockpit.core import kit_command_catalog as kc
from agp_cockpit.core import release_policy as rp

ROOT = Path(__file__).resolve().parents[1]
CATALOG = kc.KitCommandCatalog.load(ROOT)
RUN_POLICY = {"publication": "github", "signed_kit_commands": {"commands": ["agentic-kit release run"]}}

DOCSTRING = '''"""AGP-AUFTRAG 2400 - release 0.4.2

Erst der Probelauf; der Live-Lauf folgt in einem eigenen Auftrag mit
agentic-kit release-publish --version 0.4.2 --execute --allow-execute --expected-signature <sig>
und agentic-kit release run --execute. Nie die Datei ENABLE_LIVE_PUBLISH.
"""
'''
DRY = 'subprocess.run(["agentic-kit", "release-publish", "--version", "0.4.2", "--dry-run", "--json"])'


def order(*lines: str) -> str:
    return DOCSTRING + "import subprocess\n" + "\n".join(lines) + "\n"


def line_of(source: str, text: str) -> int:
    return next(number for number, line in enumerate(source.splitlines(), 1) if text in line)


def test_execute_only_in_the_docstring_is_accepted():
    source = order(DRY)
    assert rp.violations(source, ROOT) == []
    assert rp.violations(source, ROOT, CATALOG) == []
    assert kc.remote_effect_commands(source, CATALOG) == []
    assert kc.approval_required_commands(source, CATALOG) == []


def test_execute_in_a_pull_request_body_is_prose_and_is_accepted():
    body = 'BODY = "Live run later: agentic-kit release-publish --execute --allow-execute"'
    source = order(body, DRY)
    assert rp.violations(source, ROOT, CATALOG) == []
    assert kc.remote_effect_commands(source, CATALOG) == []


def test_a_real_call_without_signature_is_rejected_with_call_and_line():
    unsigned = 'subprocess.run(["agentic-kit", "release-publish", "--version", "0.4.2", "--execute", "--allow-execute"])'
    source = order(DRY, unsigned)
    found = rp.violations(source, ROOT, CATALOG)
    assert len(found) == 1
    line = line_of(source, '"--allow-execute"])')
    assert (f"line {line}: agentic-kit release-publish --version 0.4.2 --execute --allow-execute: "
            "a live release-publish needs --execute --allow-execute --expected-signature") in found[0]
    assert f"line {line_of(source, '--dry-run')}:" not in found[0]          # the dry run is not named
    assert kc.remote_effect_commands(source, CATALOG) == ["agentic-kit release-publish"]


def test_a_signed_call_is_accepted():
    signed = ('subprocess.run(["agentic-kit", "release-publish", "--version", "0.4.2", "--execute", '
              '"--allow-execute", "--expected-signature", "4a080dd2175802a47217b9a3", "--json"])')
    assert rp.violations(order(signed), ROOT, CATALOG) == []


@pytest.mark.parametrize("appended", ['ARGV += ["--execute"]', 'EXTRA = "--execute --allow-execute"'])
def test_a_flag_standing_free_in_the_code_still_counts_and_is_named(appended):
    source = order("ARGV = [\"agentic-kit\", \"release-publish\", \"--version\", \"0.4.2\", \"--dry-run\"]", appended)
    found = rp.violations(source, ROOT, CATALOG)
    assert found and "a live release-publish needs" in found[0]
    assert f"stands outside every call (line {line_of(source, appended)})" in found[0]
    assert kc.remote_effect_commands(source, CATALOG) == ["agentic-kit release-publish"]


def test_a_flag_of_another_call_does_not_make_the_dry_run_live():
    finish = 'subprocess.run(["agentic-kit", "work", "finish", "--branch", "x", "--execute", "--json"])'
    source = order(DRY, finish)
    assert rp.violations(source, ROOT, CATALOG) == []
    assert "agentic-kit release-publish" not in kc.remote_effect_commands(source, CATALOG)


def test_the_release_run_reads_its_own_flags():
    plan = 'run(["agentic-kit", "release", "run", "--version", "0.4.2", "--json"])'
    live = plan.replace('"--json"', '"--execute", "--expected-signature", "s", "--json"')
    signed = live.replace('"--json"', '"--approved-by", "vfi64", "--consent-source", "click", "--json"')
    names = {"agentic-kit release run"}
    assert rp._signed_release_violations(DOCSTRING + plan, ROOT, RUN_POLICY, names, None) == []
    found = rp._signed_release_violations(DOCSTRING + live, ROOT, RUN_POLICY, names, None)
    assert len(found) == 1 and found[0].startswith(f"line {line_of(DOCSTRING + live, 'run([')}: agentic-kit release run")
    assert "--approved-by" in found[0]
    assert rp._signed_release_violations(DOCSTRING + signed, ROOT, RUN_POLICY, names, None) == []


def test_the_marker_file_counts_only_in_code_and_is_named_with_its_line():
    assert rp.violations(order(DRY), ROOT, CATALOG) == []                    # docstring mention
    marker = 'Path(".agentic/release/ENABLE_LIVE_PUBLISH").write_text("x")'
    source = order("from pathlib import Path", marker, DRY)
    found = rp.violations(source, ROOT, CATALOG)
    assert found and f"line {line_of(source, 'ENABLE_LIVE_PUBLISH\").write')}: a live release-publish uses its signed" in found[0]


def test_github_release_and_forbidden_kit_calls_name_their_lines():
    gh = 'subprocess.run(["gh", "release", "create", "v0.4.2"])'
    doi = 'subprocess.run(["agentic-kit", "post-release-doi-closeout"])'
    source = order(gh, doi)
    found = rp.violations(source, ROOT, CATALOG)[0]
    assert f"line {line_of(source, gh)}: gh release create publishes a GitHub Release" in found
    assert f"agentic-kit post-release-doi-closeout is a publication step (line {line_of(source, doi)})" in found


def test_the_release_route_names_its_calls_when_the_workspace_publication_differs(tmp_path):
    (tmp_path / "docs/planning").mkdir(parents=True)
    (tmp_path / "docs/planning/release_policy.json").write_text(
        (ROOT / "docs/planning/release_policy.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / ".agentic").mkdir()
    (tmp_path / ".agentic/config.yaml").write_text("publication: none\n", encoding="utf-8")
    source = order(DRY)
    found = rp.violations(source, tmp_path)[0]
    assert "publication: github" in found
    assert f"line {line_of(source, '--dry-run')}: agentic-kit release-publish --version 0.4.2 --dry-run --json" in found


def test_free_execute_flags_skip_docstrings_prose_and_recognised_calls():
    source = order(DRY, 'subprocess.run(["agentic-kit", "work", "finish", "--execute"])',
                   'NOTE = "run it with --execute later"', 'run(*ARGS, "--execute")')
    import ast
    assert kc.free_execute_flags(ast.parse(source)) == [("--execute", line_of(source, 'run(*ARGS'))]
