# Changelog — AGP Cockpit

Private tool; releases are not published (no PyPI or Zenodo); the private
repository may carry a GitHub Release entry made by the owner
(`docs/planning/RELEASE_POLICY.md`). Version map: `docs/releases/versions.json`.

## Unreleased

- An unloadable remote file is requested once more under the next step instead of
  stopping the task (AGP_K07_REMOTE_FILE_REGENERATE_V1); build `release-0.1.1-r1`.
- The release work order fills the changelog from the Unreleased section and the
  merged pull requests (corrected entry for 0.1.1 below).
- Mission start from a new ChatGPT chat: digest and result files go into the visible
  composer's form instead of the first file input of the page, and a send retry clears
  its own draft instead of stopping; build `release-0.1.1-r6`. The send refocuses the
  composer before Enter and its fallback uses the composer form's send button (the
  current UI has no `send-button` test id); build `release-0.1.1-r7`.
- The bridge panel refreshes turns, steps and its time every 5 s during a run and shows
  how long the current work order runs or how long it waits for ChatGPT; build
  `release-0.1.1-r8`.
- Kit 1.0.17 adopted (CI pins, command manifest 9fedc20833c1). The Kit findings window
  keeps a finding open when the Cockpit's own retest still shows the defect in the Kit
  version that claims the fix (KIT-GF-042, `workspace ci-update` stays blocked).
- Mission start checks the ChatGPT composer, its form and its file input before it
  touches the page; a failure stops with a clear reason and nothing sent, and every
  start logs the page shape; build `release-0.1.1-r9`.
- Kit 1.0.18 adopted (CI pins, command manifest 5f78167f2644); KIT-GF-042 and KIT-GF-046
  verified fixed, KIT-GF-047 recorded.

## v0.2.0 - 2026-10-05

- Fix remote file regeneration
- P10a: Pflege standard task; sweep execute asks; ci-update guard
- Pflege DONE file within the terminal schema; correct malformed terminal replies
- R5 in every tab: the Arbeiten tab refuses to start while a task runs
- Docs lifecycle headers for the planning documents
- Lagebericht: uncommitted work on a new branch is IN_ARBEIT, not STÖRUNG
- Fix new chat composer attachment
- Claude chat switch from repository facts (AGP_CLAUDE_HANDOFF_FACTS_V1)
- Bridge panel: live counters and phase during a run (AGP_PANEL_LIVE_STATUS_V1)
- Record KIT-GF-044; KIT-GF-043/044 fixed on Kit main (#2387)
- Adopt Kit 1.0.17; KIT-GF-042 retest still fails, record KIT-GF-045/046
- Adopt Kit 1.0.18; KIT-GF-042 and KIT-GF-046 verified fixed, record KIT-GF-047
- Check composer touchpoints before a mission start (AGP_MISSION_TOUCHPOINT_SELFTEST_V1)

## v0.1.1 - 2026-10-04

App 0.1.1 · build `release-0.1.1` · agentic-project-kit 1.0.16 · made with the
Release button (corrected entry; the tag carries the one-line stub).

- Release button (P11): version map V2, release branch through the Kit, signed
  private tag push after the owner's approval, local release verifier; resumes at
  the tag after an interrupted phase 2.
- Standard Tasks: NEEDS_HUMAN answered in the tab, Ablehnen ends the task, effects
  log kept, remote branch facts, full Wiederherstellen on the Kit's work rescue,
  late Abschließen confirmed locally.
- Waiting for the remote answer by activity (German „Stoppen“ button).
- Repo wechseln (P4): one ChatGPT conversation per repository; start in the
  connected chat when another tab is in front.
- Kit 1.0.14–1.0.16 adopted; findings verified and recorded; e2e never loads the
  live chatgpt.com; owner's window size.

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
