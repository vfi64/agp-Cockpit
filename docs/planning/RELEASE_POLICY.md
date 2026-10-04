# Release policy — agp-Cockpit

Status: active · Decided by the owner on 2026-10-02 · Machine-readable form:
`docs/planning/release_policy.json` (marker `AGP_RELEASE_POLICY_V1`).

agp-Cockpit is the owner's private tool. It is not published anywhere.

- A release is private: version bump, changelog entry, annotated git tag and a
  local app build. Pushing the tag to the private repository is allowed
  (owner's decision 2026-10-02, `tag_push` in the JSON); it is a remote effect
  and needs the owner's approval of the release run.
- A GitHub Release entry in the private repository is allowed when the owner
  creates it by hand (owner's decision 2026-10-02, `owner_github_release` in
  the JSON): `gh release create <tag> --verify-tag`, visible only to the owner
  while the repository stays private. Cockpit work orders still never create,
  edit or delete GitHub Releases.
- No PyPI package, no Zenodo record. There is no Zenodo
  record for this repository; none may be created, updated or queried, and a
  release must not attempt a Zenodo or DOI step.
- Enforced in code: the Cockpit rejects work orders that run
  `agentic-kit release-publish`, `agentic-kit post-release-doi-closeout`,
  `gh release create|upload|edit|delete` or contact Zenodo or PyPI upload hosts
  (correctable rejection, the remote side gets the reason).
- The Kit's release lifecycle currently assumes public publication (GitHub
  Release, Zenodo DOI, PyPI); recorded as Greenfield finding KIT-GF-029.

Release 0.1.0 (2026-10-02) was prepared manually because Kit 1.0.13 cannot
prepare a release of an external, private workspace (KIT-GF-032): version files
and `CHANGELOG.md` in the branch, row in `docs/releases/versions.json`, the
annotated tag `v0.1.0` set by the owner on main after the merge.

## Version map (owner's decision 2026-10-04, AGP_VERSION_MAP_V2)

- `agentic-kit release prepare --write` updates the version anchors declared in
  `.agentic/config.yaml` (`release.version_anchors`, Kit 1.0.16, KIT-GF-037):
  `pyproject.toml`, `APP_VERSION` in `src/agp_cockpit/version.py`, the
  `CHANGELOG.md` section and a row **appended** to `docs/releases/versions.json`
  (`app`, `build_id`, `kit`, `date`, `tag`, `published: false`).
- The row's build id is the release build `release-<app>`. The release work
  order sets `BRIDGE_BUILD_ID` (`src/agp_cockpit/version.py`) and
  `chrome_extension/build_identity.js` to that value in the same branch: the
  build id is read literally by the stale-app guard and by the extension, so it
  is not a Kit version anchor. Rebuilds between releases carry `-r<N>`.
- The Chrome extension version lives in `chrome_extension/manifest.json` only.
- `tests/test_release_versions.py` enforces all of this; a release branch whose
  build id was not set fails with a message naming both files.
- Rehearsed 2026-10-04 with Kit 1.0.16 in a sandbox clone: `release prepare
  --version 0.1.1 --write` plus the build-id step → full test suite, `release-check`,
  `check` and `doctor` PASS.
