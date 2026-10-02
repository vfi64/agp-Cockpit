# Release policy — agp-Cockpit

Status: active · Decided by the owner on 2026-10-02 · Machine-readable form:
`docs/planning/release_policy.json` (marker `AGP_RELEASE_POLICY_V1`).

agp-Cockpit is the owner's private tool. It is not published anywhere.

- A release is private: version bump, changelog entry, annotated git tag and a
  local app build. Pushing the tag to the private repository is a remote effect
  and needs the owner's approval like every other remote effect.
- No GitHub Release, no PyPI package, no Zenodo record. There is no Zenodo
  record for this repository; none may be created, updated or queried, and a
  release must not attempt a Zenodo or DOI step.
- Enforced in code: the Cockpit rejects work orders that run
  `agentic-kit release-publish`, `agentic-kit post-release-doi-closeout`,
  `gh release create|upload|edit|delete` or contact Zenodo or PyPI upload hosts
  (correctable rejection, the remote side gets the reason).
- The Kit's release lifecycle currently assumes public publication (GitHub
  Release, Zenodo DOI, PyPI); recorded as Greenfield finding KIT-GF-029.
