# Changelog — AGP Cockpit

Private tool; releases are not published (no GitHub Release, PyPI or Zenodo —
`docs/planning/RELEASE_POLICY.md`). Version map: `docs/releases/versions.json`.

## Unreleased

- Repo wechseln (P4): read-only check, transport-path provisioning, restart; one
  ChatGPT conversation per repository.
- Kit-gated buttons: Release (KIT-GF-029, KIT-GF-032) and the full
  Wiederherstellen (KIT-GF-033) wait for Kit fixes; the Cockpit runs no
  repository-changing git.
- Send probe escapes fixed; Kit handoff projection is Kit-internal; no
  Chat-wechseln recommendation; owner's window size.

## v0.1.0 - 2026-10-02

First private release. App 0.1.0 · extension 0.4.3 · build `release-0.1.0-r4` ·
validated with agentic-project-kit 1.0.13.

- File loop with ChatGPT: numbered Python work orders, `run_next.py`, return
  bundles and terminal replies; correctable rejection of rule violations;
  download ingress limited to safety checks; work-order contract stated to
  fresh chats.
- Command authority from the installed Kit (digest once per chat, orchestrator
  obligation for standard tasks, unknown remote effects ask, release policy,
  merged-branch guard, no force option).
- Completion verified locally: CI gate (green PR, merged lifecycle, green main),
  local verifiers for standard tasks, Cockpit-verified repository facts in
  every continuation.
- Standard Tasks tab: Lagebericht with repository states, lifecycle verbs with
  one recommendation, start-click approval with a visible effect log —
  Arbeit beginnen, Abschließen, Chat wechseln, Wiederherstellen (basic).
- Browser bridge: automatic extension refresh, download hygiene, clean
  composer before every send, send-readiness wait and one diagnosed retry,
  semantic send-control readiness for ChatGPT variants without test id,
  orphaned content-script guard.
- System tab: Kit findings with sync from the Kit repository, previewed
  cleanup; scrollable window.
- Known limits: Release, Repo übernehmen, Pflege and Repo wechseln are not yet
  buttons; open Kit findings in `docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.md`.
