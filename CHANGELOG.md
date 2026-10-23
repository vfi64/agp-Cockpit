# Changelog — AGP Cockpit

The owner's tool in a public repository; no PyPI package and no Zenodo record. Each
release is a tag and a GitHub Release entry made by the Kit's signed release run
(`docs/planning/RELEASE_POLICY.md`). Version map: `docs/releases/versions.json`.

## Unreleased

- A work order that changes the CI configuration (`.github/workflows/`, `.agentic/ci/`) without the task naming the file now stops the mission; a red check or a Kit BLOCKED is reported, not worked around (AGP_CI_CONFIG_GUARD_V1, rule 87).
- „Release“ refuses to start while the installed Kit differs from the Kit the CI pins, because the release preparation writes the command reference with the local Kit (AGP_RELEASE_KIT_MATCHES_CI_V1).
- Pull requests get their release-note category on every Kit route: the option is accepted everywhere, the prompt names it and suggests Docs or Tests / Gates when the changed paths decide it, and a repository without a publication key follows the Kit's default; the mission-start digest lists every option spelling (AGP_PR_CATEGORY_ROUTES_V1, AGP_DIGEST_ALL_OPTIONS_V1).
- „Branch wechseln“ also offers branches that exist only on origin and fetches them through the Kit; a ticked „Nach Erfolg selbst abschließen“ survives a stop for an approval; the Playwright installs of the browser job retry once (AGP_BRANCH_SWITCH_ORIGIN_V1, AGP_AUTO_FINISH_THROUGH_DECISION_V1, AGP_CI_DEPS_RETRY_V1); build `release-0.3.2-r1`.

## v0.3.2 - 2026-10-22

- Kit 1.1.5 adopted through the Kit's own `kit update` (manifest 84540b010909, signature a863cf96c9e7f8353d9bd0db). `greenfield retest --all`: 38 machine contracts PASS, 0 FAIL; 22 findings are now confirmed here (among them KIT-GF-001 to 016 and 083 to 085), every other numbered finding has a released Kit fix, KIT-GF-070 stays open for six contracts; KIT-GF-082 to 085 recorded; evidence docs/validation/evidence/kit-1.1.5-adoption.json.
- An approval for a signed discard no longer loops: the question keeps the literal line of a destructive execute (it showed only the command name, the owner approved that, and no work order could match it: eighteen identical questions live on 2026-10-22), a signature is approved with its line after a preview, and the same approval asked again after an unused grant stops the mission (AGP_DESTRUCTIVE_EXACT_LINE_V1, AGP_SIGNATURE_BOUND_APPROVAL_V1, AGP_APPROVAL_LOOP_BRAKE_V1, rule 86).

## v0.3.1 - 2026-10-21

- Kit 1.1.4 adopted through the Kit's own `kit update` (manifest e2563df60239, signature 6570672ca210b366fb4976a8); it also covers 1.1.3. The update now refreshes the rule-mechanism inventory itself (KIT-GF-072 confirmed). The Kit's CI wait waits for the late required check `agentic-gate` by name (`gates.required_checks`, AGP_CI_REQUIRED_CHECKS_DECLARED_V1, KIT-GF-079), because it starts only after python and browser. Findings: KIT-GF-076 to 078 confirmed, 079 and 080 FIXED, 070 still open (the Kit's retest runner covers eight families), KIT-GF-081 recorded; evidence docs/validation/evidence/kit-1.1.4-adoption.json; no rebuild needed.
- The Kit invocation guard and the exact approval are proven on the owner's Mac (evidence docs/validation/evidence/kit-guard-live-2026-10-20.json): through ChatGPT an exact approval of `agentic-kit transfer fetch-origin --json` ran in step 2112 with the guard's RUN; ChatGPT refuses to write a hidden remote call, so the refusal (exit 126, Kit not started) was proven by a local probe through the Cockpit's own run_next path with the real Kit 1.1.2; no rebuild needed.
- Every real Kit call of a work order is checked against its approval (AGP_KIT_INVOCATION_GUARD_V1): while `run_next` runs a work order, an `agentic-kit` guard stands first on PATH, resolves each call with the installed manifest and starts the Kit only when the approval that admitted the order covers it (for „Nur diese Befehle“ the exact line); a remote or destructive call the source analysis could not see stops with `AGP_KIT_GUARD_REFUSED` (exit 126) before the Kit starts. An approval-required call must name its arguments literally (string literal or a module-level constant bound once, AGP_LITERAL_APPROVAL_ARGUMENTS_V1), and a path to the Kit, `python -m agentic_project_kit` or an import of its package are refused; build `release-0.3.0-r3`.
- The decision box can approve exactly the command lines a question names (AGP_EXACT_COMMAND_APPROVAL_V1): „Nur diese Befehle“ lists the `agentic-kit` lines read from the question with the Kit manifest, and the bridge then runs only a work order whose approval-relevant commands are exactly these lines, argument for argument; a changed, added or computed command asks again. A line with `--allow-unlisted` needs its own warning tick. A FILE_TRANSFER `transfer remote-next <branch>` no longer needs „Push, PR und Merge“. The facts for the remote side name the branches a task or work order mentions, and one not fetched here is „not known locally“, never absent (AGP_MENTIONED_BRANCH_FACTS_V1); the Lage no longer recommends „Abschließen“ on a `transfer/` branch and points back to main (AGP_TRANSFER_BRANCH_LAGE_V1); build `release-0.3.0-r2`.
- Kit 1.1.2 adopted through the Kit's own `kit update` (manifest 390ff4b84aa2, signature 665f6a21a140daebae269848). The browser job is skipped again on the light CI path of refresh pull requests (AGP_CI_LIGHT_SKIP_DECLARED_V1, replaces AGP_CI_LIGHT_NO_SKIP_V1): `.agentic/config.yaml` declares `gates.light_path_skipped_checks: [browser]`, the Kit accepts that skip only when it re-derives the pull request as light, and the gate job accepts it only with the light verdict. FILE_TRANSFER under 1.1.2: `transfer order-create --run-command` writes command orders, and `transfer remote-next` publishes the files an order wrote and ends with a clean checkout. KIT-GF-071 to 076 are FIXED; evidence: docs/validation/evidence/kit-1.1.2-adoption.json; no rebuild needed.

## v0.3.0 - 2026-10-19

- Kit 1.1.1 adopted through the Kit's own `kit update` (manifest 5a8184255246, signature e7f303d99c564d31cf4bb3dd). For FILE_TRANSFER this is stricter: an order that runs BOUNDED Kit commands or commands outside the Kit manifest needs the local `--allow-unlisted` flag, raw git/gh mutations are always refused, and `expected_current_head` must be the full 40-character commit the order was written on, otherwise `transfer remote-next` stops as STALE_ORDER. Orders that start with the required COMMAND_MANIFEST_ACK line now complete instead of crashing. Evidence: docs/validation/evidence/kit-1.1.1-adoption.json.
- Release changelog sections list each change once: `release.changelog_summary: curated` (AGP_CHANGELOG_CURATED_V1) writes the Unreleased entries instead of also every PR title, and release preparation blocks while an Unreleased entry would stay behind.
- The build metadata `src/agp_cockpit.egg-info/` is no longer tracked (AGP_NO_TRACKED_EGG_INFO_V1): every `pip install -e .` rewrote it and blocked the Kit's clean-worktree merge preflight.

## v0.2.6 - 2026-10-13

- On the light CI path the browser job now runs and succeeds without browser tests instead of being skipped: the Kit's CI policy counts a skipped check as not green and blocked the closeout of refresh PR #347 (KIT-GF-073 recorded); no rebuild needed.
- Kit 1.0.25 adopted through the Kit's own `kit update` (manifest d1604f13011e): refresh pull requests now take the Kit's light CI path (Kit check and doctor only, AGP_CI_LIGHT_REFRESH_V1), the findings ledger and evidence files are declared evidence for the legacy-reference audit (KIT-GF-068), the rule-mechanism inventory is bootstrapped; KIT-GF-021, 051, 068 and the rule-registry bootstrap confirmed, KIT-GF-070–072 recorded; no rebuild needed.
- Kit findings KIT-GF-061 and KIT-GF-065 are confirmed fixed by the first live release run (0.2.5); the evidence is a committed file (`docs/validation/evidence/release-run-0.2.5.json`), and a test now requires dated evidence for every confirmed finding and checks each evidence file against the register; no rebuild needed.
- Gate B4 of a release run may list the Kit's own state under `.agentic/state/` besides the release files: the release task's path rule is now code (`release_gate_files`, AGP_RELEASE_GATE_PATHS_V1) instead of a too narrow sentence; KIT-GF-069 recorded (the Kit's release run stops at C1 in external workspaces; 0.2.5 was published with `release-publish`); build `release-0.2.5-r1`.
- Make the release gate's path rule code and record KIT-GF-069
- Confirm KIT-GF-061 and KIT-GF-065 from release 0.2.5 with committed evidence
- chore: update Agentic Project Kit to 1.0.25
- Run the browser job on the light CI path instead of skipping it

## v0.2.5 - 2026-10-13

- The Kit's release readiness check no longer stops on the Cockpit's own findings ledger (one quoted legacy command reference is now marked as legacy, and a test runs the Kit's audit over the ledger); KIT-GF-066, KIT-GF-067 and KIT-GF-068 recorded; no rebuild needed.
- A release is now one run of the Kit's release orchestrator: the click on „Release“ is the consent, the Kit records who approved and stops on any error or any difference in version, tag or target commit; no second question before the tag; release branches stay `release/<version>`; build `release-0.2.4-r2`.
- The System check no longer reports a new ChatGPT page when only the composer's state changed: the send, expand, voice and stop controls left the UI fingerprint (version 3; the first start after the rebuild sets a new baseline without „NEU“); build `release-0.2.4-r1`.
- Keep composer-state controls out of the UI fingerprint
- Release through the Kit's release run under up-front consent (1b)
- Keep the findings ledger clear of the Kit's legacy-reference audit

## v0.2.4 - 2026-10-13

- Kit 1.0.24 adopted (CI pins, command manifest bf05db61066e): KIT-GF-023/035/064/065 fixed in 1.0.22 and KIT-GF-017/021/027/051/062/063 fixed in 1.0.23 are recorded; checks that never ran are re-run through the Kit's `pr rerun-checks` (its plan is free, its signed run asks the owner); no rebuild needed.
- Protocol lesson recorded: a format change must stay readable by the build that is still running (the r2 app offered no rebuild after #324); no rebuild needed.
- KIT-GF-065 recorded: the Kit's release run gives a GitHub-only release the PyPI and DOI steps, so the fully autonomous Release waits for the Kit fix; no rebuild needed.
- The build id follows the version: the Kit's release preparation sets it to `release-<version>` in the app and the browser extension, so a release needs no hand edit and can run entirely through the Kit; rebuilds between releases still carry `-r<N>`; KIT-GF-049 and KIT-GF-060 verified with Kit 1.0.21; build `release-0.2.3-r3`.
- Kit 1.0.21 adopted (CI pins, command manifest 6d76959d314e): KIT-GF-049/052/060/061 fixed in 1.0.21, the `release.publish_checks: none` override is gone because the Kit-repository checks now skip themselves here; KIT-GF-023/035 fixed on Kit main (next Kit release); KIT-GF-064 recorded (the Kit's own changelog keeps released entries under Unreleased); no rebuild needed.
- When every failed check of a pull request ended without running (no log, no start or done within 3 s — GitHub's Actions quota on PR #319), the Lage says „CI nicht gestartet“ and names „Re-run all jobs“ on GitHub instead of a code failure, the recovery offer disappears as soon as the CI is no longer red, and every task prompt stops with NEEDS_HUMAN instead of asking for raw gh authority; the repository is public, release titles drop „(privat)“; KIT-GF-062 (no Kit route to re-run checks) and KIT-GF-063 (CI light mode only for the Kit's own layout) recorded; build `release-0.2.3-r2`.
- Owner rule recorded: a release runs fully autonomously after the owner's go, also for irreversible publication, and stops on FAIL, BLOCKED or any difference from the consented release (COMMUNICATION_PROTOCOL 81, release_policy.json `approval`); KIT-GF-061 recorded (the Kit's release run has no approval policy and no approver record).
- A release no longer edits the changelog by hand: on a release branch only the Kit's release preparation writes CHANGELOG.md, pyproject.toml and docs/releases/versions.json, the release pull request needs exactly one version section, and the former rule „Unreleased empty“ is withdrawn; KIT-GF-060 recorded; the rule „the Kit is the law, the Cockpit steers“ is written into the architecture, the protocol and CLAUDE.md; build `release-0.2.3-r1`.
- Fix release changelog ownership (#318)
- Refresh successor package after PR318 (#319)
- Recognise CI that never ran; public repository; KIT-GF-062/063 (#320)
- Refresh successor package after PR320 (#321)
- chore(kit): adopt agentic-project-kit 1.0.21 (#322)
- Refresh successor package after PR322 (#323)
- Derive the build id from the version; verify KIT-GF-049/060 (#324)
- Refresh successor package after PR324 (#325)
- Record KIT-GF-065: release run ignores the publication policy (#326)
- Refresh successor package after PR326 (#327)
- Record the r3 rebuild lesson in the protocol log (#328)
- Refresh successor package after PR328 (#329)
- chore(kit): adopt agentic-project-kit 1.0.24 (#330)
- Refresh successor package after PR330 (#331)

## v0.2.3 - 2026-10-08

- Releases create the GitHub Release entry of the private repository through the Kit's signed release run (`publication: github`, P11c); the Kit's Kit-repository reference check is switched off for this workspace (`release.publish_checks: none`, KIT-GF-049 reproduced in Kit 1.0.20); no rebuild needed.
- Kit 1.0.20 adopted (CI pins, command manifest 43b81efb137f): the Kit now declares the remote effects the Cockpit had to add itself (KIT-GF-057 verified); `pr-closeout` and `transfer publish-last-report` no longer ask for an approval (local only); KIT-GF-022/048/049/053/054/055/056 fixed in 1.0.20, KIT-GF-058/059 recorded from the 1.0.19 release run and fixed in 1.0.20; build `release-0.2.2-r16`.
- The browser extension no longer carries the disabled DOM send path (click, form submit or Enter instead of the native submit); a failed native send stops the step as before; `cockpit_send.js` shrinks from 761 to 551 lines and `content.js` to 2196; behavior unchanged; build `release-0.2.2-r15`.
- The browser extension no longer carries the operator paths whose buttons left the overlay on 2026-09-15 (DRY mission, LIVE probes 061/065, Phase 5 bind/draft/send, Phase 7 one round, Phase 8 run/pause/resume/stop), nor the six content scripts only they loaded; the options page drops the unused conversation URL; `content.js` shrinks to 2205 lines; behavior unchanged; build `release-0.2.2-r14`.
- „Branch wechseln …“ no longer preselects a branch: „Wechseln“ stays disabled until a branch is clicked, main is labelled „zurück auf main“, and Return or a double click only switch with a selection (two unintended switches back to main on 2026-10-07). The send transport of the browser extension (writing the prompt into ChatGPT's composer, native submit, commit nonce, acceptance evidence, bounded retry) is its own module (`cockpit_send.js`); `content.js` shrinks to 2617 lines; behavior unchanged; build `release-0.2.2-r13`.
- CI: apt gives up per request and falls back to the next Ubuntu mirror, every job and browser install step has a time limit, the runner image is pinned to Ubuntu 24.04 and the actions run on Node 24 (CI only, no rebuild needed).
- Fix: a task no longer stops with „expectedStepAttachmentCandidates is not defined“ after 20 s of waiting for ChatGPT (regression of `release-0.2.2-r11`); build `release-0.2.2-r12`.
- The file ingress of the browser extension (finding the expected file card in ChatGPT's answer, downloading or reading it and handing it to the bridge) is its own module (`cockpit_ingress.js`); `content.js` shrinks to 3312 lines; behavior unchanged; build `release-0.2.2-r11`.
- DOM hardening complete: a new fingerprint algorithm no longer shows as a new ChatGPT page (the false „NEU“ clears on the next start), and failure snapshots keep enough structure to be replayed against the real probe code in the browser tests; build `release-0.2.2-r10`.
- The overlay on the ChatGPT page (buttons, status, drag and minimize) is its own module (`cockpit_panel.js`), the first step of splitting `content.js`, which shrinks from 4246 to 3789 lines; behavior unchanged; build `release-0.2.2-r9`.
- Every ChatGPT selector of the browser extension lives in one table (`chatgpt_selectors.js`), also for the helpers the extension runs inside the ChatGPT page and for the native send path; a test keeps ChatGPT selectors out of every other extension file; build `release-0.2.2-r8`.
- The System tab offers „Systemcheck …“: app build, bridge, Chrome extension, ChatGPT UI variant, Agentic Kit against the CI pin, repository, GitHub CLI login and disk space, each with the step that fixes a problem; build `release-0.2.2-r7`.
- A task started right after „Neu bauen und neu starten“ waits until the Chrome extension reports the new build and then starts by itself, and a refused start stops the mission it had just created instead of leaving it blocking every new start; build `release-0.2.2-r6`.
- The page adapter also names the attachment preview, its download control and the dialog close controls; `content.js` keeps 10 direct page lookups; build `release-0.2.2-r5`.
- The page adapter also names the composer fallback, the send control and the generation and stop signals; `content.js` keeps 16 direct page lookups (from 27); build `release-0.2.2-r4`.
- The browser extension finds file cards, assistant turns and ChatGPT's alerts through one page adapter (`chatgpt_dom.js`), the first module split off `content.js`, and the UI fingerprint also covers the composer's attributes, its element chain and the form's button labels; build `release-0.2.2-r3`.
- The Cockpit records the ChatGPT UI variant at every start and a sanitized page shape at every failure, the send retry works without a send button, a lost terminal reply is requested again, a task stopped by a lost or late reply is checked against the repository, and the result line no longer recommends „Wiederherstellen“ once the Lage withdrew it; build `release-0.2.2-r2`.
- A running release shows a yellow note instead of locking the tasks, the release pull request needs the exact build id and JSON summary lines, src and tests pass ruff like the Kit's local gate, test windows stay invisible, and Pause, Fortsetzen, Stop and Reset are clickable only when they act; build `release-0.2.2-r1`.
- Harden CI runner
- Add a read-only Systemcheck with a fix for every problem
- Fix start after rebuild
- Move the composer, send and generation touchpoints into the page adapter
- Move the file-card and assistant-turn touchpoints into a page adapter
- Observe the ChatGPT page and survive a lost terminal reply
- Keep releases robust: no lock mid-release, exact build id, JSON summary, clean lint

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
