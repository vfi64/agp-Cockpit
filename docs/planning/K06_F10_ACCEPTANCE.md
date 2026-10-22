# K06 / F10 First-use and Accessibility Acceptance

Status: active
Status-date: 2026-10-04
Decision status: accepted
Review policy: on material change
Note: MANUAL USABILITY / KEYBOARD ACCEPTED 2026-09-12; EXTERNAL INSTALLATION PENDING

The K06 product entry surface is the durable Task Operator, not the legacy Mission runtime.
It accepts an ordinary target repository as repository context while durable runtime state remains outside that repository.
The surface exposes repository identity, task state, suspension reason, human checkpoint, completion state, pause, resume and checkpoint approval.

## Accessibility contract
- native Tk/ttk controls provide platform semantic roles;
- actionable controls participate explicitly in keyboard focus traversal;
- initial focus is deterministic;
- Command-R refreshes status and Command-P pauses the task;
- layout uses geometry managers and does not require a fixed window size.

Static/component tests do not constitute macOS VoiceOver or visual-layout acceptance.
K06/F10 may close only after a live macOS run proves keyboard-only traversal/activation,
VoiceOver names/roles/state, and usable layout at supported minimum/normal sizes.

## Manual acceptance — 2026-09-12

Observed on macOS with the real AGP Cockpit application and Chrome bridge:

- PASS — production repository context resolves to `/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit`; no pytest/tmp repository path is shown.
- PASS — Chrome bridge reaches `CONNECTED` without manual port or token editing.
- PASS — System, Auftrag, and Task Operator are separate usable tabs.
- PASS — Auftrag layout no longer overlaps controls; the browser-refresh control is in normal layout flow.
- PASS — the application remains usable at its enforced minimum window size; no control overlap was observed.
- PASS — keyboard focus traversal is visible in System, Auftrag, and Task Operator.
- PASS — Auftrag focus feedback explicitly names `Mission Operator öffnen` and `Browser-Verbindung neu laden`.
- PASS — Tab leaves the structured JSON input instead of inserting a tab character; Shift-Tab reverses focus traversal.
- PASS — Task Operator keyboard focus cycles through `Status aktualisieren`, `Task pausieren`, `Task fortsetzen`, and `Checkpoint freigeben`.
- KNOWN ACCESSIBILITY LIMITATION — with macOS VoiceOver enabled, keyboard focus moves correctly through the four Task Operator buttons, but VoiceOver does not announce those button names on focus. VoiceOver does read the native dialog content produced after an activated control. No synthetic speech workaround is added.
- ACCEPTANCE DECISION — K06/F10 manual usability and keyboard-accessibility acceptance is satisfied with the VoiceOver announcement gap documented as a known framework/platform accessibility limitation, not as a blocker for normal Cockpit operation.

The known VoiceOver limitation must not be hidden by product-generated speech. If full screen-reader conformance becomes a product requirement, it requires a dedicated macOS/Tk accessibility investigation rather than further ad-hoc GUI mutation in this slice.
