"""AGP_E2E_NO_LIVE_NETWORK_V1: browser tests never depend on a live website.

PR #185 (a documentation-only successor refresh, run #588) had a red browser
job while the identical code was green on main minutes before (run #587):
five test_203 specs failed with "Execution context was destroyed, most likely
because of a navigation". test_203 loaded the live https://chatgpt.com/c/...;
after `setContent` the live page navigated on its own and destroyed the test
context. Without network to chatgpt.com all nine test_203 specs fail
(reproduced). Every spec that navigates must therefore serve the page itself:
a `page.route` stub or a local file URL.
"""

from __future__ import annotations

import re
from pathlib import Path

E2E = Path(__file__).resolve().parent / "e2e"
GOTO = re.compile(r"page\.goto\(")


def _specs() -> list[Path]:
    return sorted(E2E.glob("*.spec.js"))


def test_e2e_specs_exist():
    assert _specs(), "no Playwright specs found"


def test_every_navigating_spec_serves_its_own_page():
    offenders = []
    for spec in _specs():
        text = spec.read_text(encoding="utf-8")
        if GOTO.search(text) and "page.route(" not in text and "pathToFileURL" not in text:
            offenders.append(spec.name)
    assert offenders == [], f"specs that may load a live website: {offenders}"


def test_conversation_contract_spec_stubs_chatgpt():
    text = (E2E / "test_203_phase5_conversation_contract.spec.js").read_text(encoding="utf-8")
    assert "AGP_E2E_NO_LIVE_NETWORK_V1" in text
    assert text.index('page.route("https://chatgpt.com/**"') < text.index("await page.goto(url)")
