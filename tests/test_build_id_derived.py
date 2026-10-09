"""AGP_BUILD_ID_DERIVED_V1 (owner 2026-10-09): the build id follows the version.

A release used to need a hand edit of the build id on the release branch (AGP_RELEASE_BUILD_ID_GATE_V1).
The Kit's `release run` commits only what its own release preparation changes, so the hand edit
would block it. Now the Kit's version anchors (APP_VERSION, AGP_APP_VERSION) carry the version and
both build ids are derived from it; a rebuild between releases raises the revision.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from agp_cockpit import version as v

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "src/agp_cockpit/version.py"
JS = ROOT / "chrome_extension/build_identity.js"


def test_the_build_id_is_derived_from_the_version_and_the_revision():
    assert v.build_id("0.2.3", ("0.2.3", 3)) == "release-0.2.3-r3"
    assert v.build_id("0.2.4", ("0.2.3", 3)) == "release-0.2.4"        # the release itself
    assert v.build_id("0.2.4", ("0.2.4", 0)) == "release-0.2.4"
    assert v.BRIDGE_BUILD_ID == v.build_id(v.APP_VERSION, v.BUILD_REVISION)


def test_both_files_define_the_same_build_id_and_older_literal_files_still_read():
    assert v.build_id_from_text(PY.read_text(encoding="utf-8")) == v.BRIDGE_BUILD_ID
    assert v.build_id_from_text(JS.read_text(encoding="utf-8")) == v.BRIDGE_BUILD_ID
    assert v.build_id_from_text('globalThis.AGP_EXTENSION_BUILD_ID = "release-0.2.3-r2";\n') == "release-0.2.3-r2"
    assert v.build_id_from_text('BRIDGE_BUILD_ID = "release-0.2.2"\n') == "release-0.2.2"
    assert v.build_id_from_text("nothing here") == ""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_extension_computes_the_same_build_id():
    script = ('require("vm").runInThisContext(require("fs").readFileSync(process.argv[1], "utf8"));'
              "process.stdout.write(globalThis.AGP_EXTENSION_BUILD_ID)")
    done = subprocess.run(["node", "-e", script, str(JS)], capture_output=True, text=True, check=True)
    assert done.stdout == v.BRIDGE_BUILD_ID


def test_the_kits_release_preparation_alone_yields_the_release_build_id():
    """What `release prepare --write` changes in both files gives release-<version>, no hand edit."""
    sources = pytest.importorskip("agentic_project_kit.release_version_sources")
    updates = sources.additional_version_anchor_updates(ROOT, version="9.9.9", date="2030-01-01")
    texts = {path.relative_to(ROOT).as_posix(): text for path, text in updates.items()}
    for rel in ("src/agp_cockpit/version.py", "chrome_extension/build_identity.js"):
        assert v.build_id_from_text(texts[rel]) == "release-9.9.9", rel
    assert re.search(r'^APP_VERSION = "9\.9\.9"$', texts["src/agp_cockpit/version.py"], re.MULTILINE)
    assert re.search(r'^AGP_APP_VERSION = "9\.9\.9";$', texts["chrome_extension/build_identity.js"], re.MULTILINE)


def test_a_release_work_order_may_not_write_the_build_identity():
    from agp_cockpit.core import release_hygiene as rh
    order = ('from pathlib import Path\n'
             'Path("chrome_extension/build_identity.js").write_text("x", encoding="utf-8")\n')
    assert rh.kit_owned_writes(order) == ["chrome_extension/build_identity.js"]
