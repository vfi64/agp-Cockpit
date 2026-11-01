"""AGP_SELF_TEST_ARGV_SLICE_V1 — live 2026-11-01, task „Kit übernehmen“ 1.1.11: work orders 2209,
2210 and 2213 were correct but rejected with "missing --self-test contract" because they wrote
`'--self-test' in sys.argv[1:]`, a form the rule ("sys.argv or argparse") allows. Two of three
attempts of one round were lost. The shapes below are reduced from those orders (machine paths
left out)."""

import pytest

from agp_cockpit.core.command_file_contract import (
    SELF_TEST_VIOLATION,
    command_content_contract_violations,
)

BODY = '''import json
import subprocess
import sys
from pathlib import Path

STEP = 2209
OUTPUT = Path("Download") / f"{STEP}_agp_kit_adopt_return_bundle.json"


def self_test():
    assert OUTPUT.name == "2209_agp_kit_adopt_return_bundle.json"
    return 0


def run_kit(argv):
    return subprocess.run(argv, capture_output=True, text=True)


def main():
%(main_guard)s    run_kit(["agentic-kit", "kit", "update", "--version", "1.1.11", "--json"])
    OUTPUT.write_text(json.dumps({"step": STEP}) + "\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
%(module_guard)s    sys.exit(main())
'''

GUARD_IN_MODULE = "    if '--self-test' in sys.argv[1:]:\n        sys.exit(self_test())\n"
GUARD_IN_MAIN = "    if '--self-test' in sys.argv[1:]:\n        return self_test()\n"


def _order(*, main_guard: str = "", module_guard: str = "") -> str:
    return BODY % {"main_guard": main_guard, "module_guard": module_guard}


@pytest.mark.parametrize(
    "source",
    [
        _order(module_guard=GUARD_IN_MODULE),  # shape of 2209
        _order(main_guard=GUARD_IN_MAIN),  # shape of 2210 and 2213
        _order(module_guard=GUARD_IN_MODULE.replace("sys.argv[1:]", "sys.argv")),
    ],
    ids=["2209-module-slice", "2210-2213-main-slice", "plain-sys-argv"],
)
def test_live_self_test_forms_are_accepted(source):
    assert command_content_contract_violations(source, expected_step=2209) == []


def test_an_order_without_self_test_mode_is_still_rejected():
    assert command_content_contract_violations(_order(), expected_step=2209) == [SELF_TEST_VIOLATION]


def test_the_string_alone_on_another_list_is_not_a_self_test_mode():
    source = _order(module_guard="    flags = []\n    if '--self-test' in flags:\n        sys.exit(0)\n")
    assert command_content_contract_violations(source, expected_step=2209) == [SELF_TEST_VIOLATION]


def test_the_rejection_names_every_accepted_form():
    for form in ("in sys.argv:", "in sys.argv[1:]:", "add_argument('--self-test'"):
        assert form in SELF_TEST_VIOLATION
    assert SELF_TEST_VIOLATION.startswith("missing --self-test contract")
