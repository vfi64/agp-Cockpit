# Changelog — AGP Cockpit

Private tool; releases are not published (no PyPI or Zenodo); the private
repository carries a GitHub Release entry per release, made by the owner until the
Kit's signed release run takes it over (`docs/planning/RELEASE_POLICY.md`). Version map: `docs/releases/versions.json`.

## Unreleased

- A task started right after „Neu bauen und neu starten“ waits until the Chrome extension reports the new build and then starts by itself, and a refused start stops the mission it had just created instead of leaving it blocking every new start; build `release-0.2.2-r6`.
- The page adapter also names the attachment preview, its download control and the dialog close controls; `content.js` keeps 10 direct page lookups; build `release-0.2.2-r5`.
- The page adapter also names the composer fallback, the send control and the generation and stop signals; `content.js` keeps 16 direct page lookups (from 27); build `release-0.2.2-r4`.
- The browser extension finds file cards, assistant turns and ChatGPT's alerts through one page adapter (`chatgpt_dom.js`), the first module split off `content.js`, and the UI fingerprint also covers the composer's attributes, its element chain and the form's button labels; build `release-0.2.2-r3`.
- The Cockpit records the ChatGPT UI variant at every start and a sanitized page shape at every failure, the send retry works without a send button, a lost terminal reply is requested again, a task stopped by a lost or late reply is checked against the repository, and the result line no longer recommends „Wiederherstellen“ once the Lage withdrew it; build `release-0.2.2-r2`.
- A running release shows a yellow note instead of locking the tasks, the release pull request needs the exact build id and JSON summary lines, src and tests pass ruff like the Kit's local gate, test windows stay invisible, and Pause, Fortsetzen, Stop and Reset are clickable only when they act; build `release-0.2.2-r1`.

## v0.2.2 - 2026-10-07

- The tick „Nach Erfolg selbst abschließen“ has its own line under the editor with a hint that green CI does not check correctness, instead of breaking the button row; it stays off by default.
- An older build in the checkout (main before its pull during „Abschließen“) no longer raises the stale-app warning, and the warning says whether the source is newer or just different; build `release-0.2.1-r12`.
- „Abschließen“ only publishes (no work order may touch tests/ or src/, no commit on a clean branch), the interruption memory expires on a clean branch ready to finish, and the Kit findings table sorts by a clicked column (opens sorted by ID); build `release-0.2.1-r11`.
- The Cockpit keeps the runtime of a steered repository (bridge log, missions, Kit digest, deliveries, work-order temp files) in its own checkout instead of the steered repository, and „Aufräumen“ offers what earlier builds left there; build `release-0.2.1-r10`.
- Pull requests need one-line Unreleased entries, the build id is checked exactly, and Kit commands that declare a write effect in the manifest need an approval (KIT-GF-057 recorded: five commands are declared without their effect); build `release-0.2.1-r9`.
- „Branch wechseln …“ switches the local branch through the Kit, a ticked „Arbeiten“ task starts „Abschließen“ by itself when it ends DONE, and an approval in the „Arbeiten“ tab names its scope (push and PR, or with merge), which the bridge enforces; build `release-0.2.1-r8`.
- One extension refresh per new build (a second one orphaned the ChatGPT tab after „Neu bauen und neu starten“), orphaned ChatGPT tabs reload themselves, „Wiederherstellen“ and „Weitere anzeigen“ align, Ollama and Hermes share one height; build `release-0.2.1-r7`.
- The „Arbeiten“ tab gets the Ampel, a fixed-height editor and a decision box under the editor whose buttons stay visible, with facts checked by the Cockpit and „Änderungen ansehen“; all tabs wrap to the window width and the repository path has its own line; build `release-0.2.1-r6`.
- One upload per step (the run_next log travels inside the result file), a ChatGPT attachment limit holds the task until the named time and re-sends the kept result instead of stopping it, and the mission start asks for few combined work orders; build `release-0.2.1-r4`.
- The Lage follows tasks of the „Arbeiten“ tab, a finished one switches back to Standard Tasks, results name their task, a fresh work branch is no leftover, effects are listed by start click or approval, Kit findings come from the Cockpit checkout, the stale-app line wraps; KIT-GF-024 verified; build `release-0.2.1-r3`.
- Kit 1.0.19 adopted (CI pins, command manifest fb315aa30770); KIT-GF-024/025/028/047/050 fixed in 1.0.19, KIT-GF-053 to KIT-GF-056 recorded from the Cockpit's first run in the Kit repository and the Kit's 1.0.19 release.
- „Repo wechseln“ restarts the app again (the rebuild button's restart had replaced it); no class may define a name twice; build `release-0.2.1-r2`.
- The Lage shows a running task as „ein Task läuft“ from its start to its end, and after a private release the Cockpit names the owner's GitHub entry command (KIT-GF-052 recorded); build `release-0.2.1-r1`.

## v0.2.1 - 2026-10-06

- Add release hygiene gates and prepare the Kit's GitHub release entry (P11c)
- Sync Kit findings with Kit main after 1.0.18
- Add the Lage traffic light and a short German result line
- Add a rebuild and restart button to the stale-app warning
- Add guided recovery
- Keep rejected work orders and narrow the release resume scope
- Prepare release 0.2.1
- Fix release 0.2.1 build identity

## v0.2.0 - 2026-10-05

App 0.2.0 · build `release-0.2.0` · agentic-project-kit 1.0.18 · made with the
Release button (corrected entry; the tag carries the pull-request titles).

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
