"""Version and identity constants for the desktop/bridge runtime."""

import re

APP_VERSION = "0.3.1"
BRIDGE_PROTOCOL_VERSION = 1

# AGP_BUILD_ID_DERIVED_V1 (owner 2026-10-09): the build id follows the version, so a release needs
# no hand edit and the Kit's `release run` can carry it alone. A rebuild between releases raises
# BUILD_REVISION to (APP_VERSION, n + 1) here and AGP_BUILD_REVISION in
# chrome_extension/build_identity.js. The Kit's release preparation raises APP_VERSION here and
# AGP_APP_VERSION there (version anchors in .agentic/config.yaml); the revision then names an
# older version and the build id is plain release-<version>.
BUILD_REVISION = ("0.3.0", 3)


def build_id(app_version: str, revision: tuple[str, int]) -> str:
    """release-<version>, plus -r<n> while the revision belongs to that version."""
    base, number = revision
    return f"release-{app_version}" + (f"-r{number}" if base == app_version and number else "")


BRIDGE_BUILD_ID = build_id(APP_VERSION, BUILD_REVISION)

_VERSION = re.compile(r"""^(?:AGP_)?APP_VERSION\s*=\s*["']([^"']+)["']""", re.MULTILINE)
_REVISION = re.compile(r"""(?:AGP_)?BUILD_REVISION\s*=\s*[(\[]\s*["']([^"']+)["']\s*,\s*(\d+)\s*[)\]]""")
_LITERAL = re.compile(r"""(?:BRIDGE_BUILD_ID|AGP_EXTENSION_BUILD_ID)\s*=\s*["']([^"']+)["']\s*;?\s*$""",
                      re.MULTILINE)


def build_id_from_text(text: str) -> str:
    """The build id that src/agp_cockpit/version.py or chrome_extension/build_identity.js defines,
    read without importing or running it (another checkout, the app bundle). Older files carry the
    id as a literal; "" when neither form is present."""
    version, revision = _VERSION.search(text or ""), _REVISION.search(text or "")
    if version and revision:
        return build_id(version.group(1), (revision.group(1), int(revision.group(2))))
    literal = _LITERAL.search(text or "")
    return literal.group(1) if literal else ""
