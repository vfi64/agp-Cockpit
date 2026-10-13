// AGP_BUILD_ID_DERIVED_V1 (owner 2026-10-09): the build id follows the version, like
// src/agp_cockpit/version.py. The Kit's release preparation writes the AGP_APP_VERSION line (a
// version anchor in .agentic/config.yaml); a rebuild between releases raises AGP_BUILD_REVISION.
var AGP_APP_VERSION;
AGP_APP_VERSION = "0.2.6";
var AGP_BUILD_REVISION = ["0.2.5", 1];
globalThis.AGP_EXTENSION_BUILD_ID = "release-" + AGP_APP_VERSION
  + (AGP_BUILD_REVISION[0] === AGP_APP_VERSION && AGP_BUILD_REVISION[1] ? "-r" + AGP_BUILD_REVISION[1] : "");
