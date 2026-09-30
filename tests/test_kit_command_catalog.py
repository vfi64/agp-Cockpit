"""AGP_KIT_COMMAND_CATALOG_V1: the repository manifest is the command authority;
its rules are sent to the remote side and enforced on every work order."""
import json
from pathlib import Path

import pytest

from agp_cockpit.core.command_file_contract import validate_command_content
from agp_cockpit.core.kit_command_catalog import (
    COMMAND_RULES,
    KitCommandCatalog,
    command_catalog_violations,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = KitCommandCatalog.load(ROOT)


def order(argv_literal: str) -> str:
    return (
        "import argparse, subprocess\nfrom pathlib import Path\n"
        f"CMD = {argv_literal}\n"
        'RETURN_BUNDLE = "1_x_return_bundle.json"\n'
        "def main():\n    p = argparse.ArgumentParser()\n"
        '    p.add_argument("--self-test", action="store_true")\n    p.parse_args()\n'
        '    subprocess.run(["agentic-kit", "transfer", "divergence-status", "--json"])\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


def test_manifest_is_present_and_resolves_real_commands():
    assert CATALOG is not None and CATALOG.manifest_sha
    assert CATALOG.resolve(["transfer", "divergence-status"])["surface"] == "diagnostic"
    assert CATALOG.resolve(["transfer", "chat-switch-complete"])["surface"] == "orchestrator"
    assert CATALOG.resolve(["transfer", "does-not-exist"]) is None


@pytest.mark.parametrize(("argv", "message"), [
    ('["git", "push", "origin", "HEAD"]', "git push is not permitted"),
    ('["git", "-C", "/repo", "fetch"]', "git fetch is not permitted"),
    ('"git pull --rebase"', "git pull is not permitted"),
    ('["git", "commit", "-m", "x"]', "use agentic-kit transfer commit"),
    ('["gh", "pr", "create"]', "use agentic-kit transfer pr-create-complete"),
    ('["agentic-kit", "push-everything"]', "unknown agentic-kit command 'agentic-kit push-everything'"),
])
def test_forbidden_or_unknown_commands_are_rejected(argv, message):
    violations = command_catalog_violations(order(argv), CATALOG)
    assert any(message in v for v in violations), violations


def test_manifest_commands_and_read_only_git_pass():
    source = order('["git", "status", "--porcelain"]')
    assert command_catalog_violations(source, CATALOG) == []


def test_network_git_is_rejected_even_without_a_manifest():
    assert command_catalog_violations(order('["git", "push"]'), None) == ["git push is not permitted in work orders"]


def test_validate_command_content_enforces_the_catalog_for_the_repository():
    with pytest.raises(ValueError, match="unknown agentic-kit command"):
        validate_command_content(order('["agentic-kit", "invented", "cmd"]'), repository_root=ROOT)


def test_digest_lists_orchestrators_first_with_rules(tmp_path):
    digest = CATALOG.digest()
    surfaces = [c["surface"] for c in digest["commands"]]
    assert surfaces[0] == "orchestrator" and surfaces == sorted(surfaces, key={"orchestrator": 0, "diagnostic": 1, "primitive": 2}.get)
    assert digest["rules"] == COMMAND_RULES and "Never run git push, git fetch or git pull" in COMMAND_RULES
    target = CATALOG.write_digest(tmp_path / "d.json")
    assert json.loads(target.read_text())["manifest_sha"] == CATALOG.manifest_sha
    assert target.stat().st_size < 120_000
