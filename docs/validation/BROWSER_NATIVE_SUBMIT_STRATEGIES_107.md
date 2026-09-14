# Browser Native Message Evidence 107

Status: active
Decision status: verified transport repair
Review policy: on material change

## Root cause

The September 14 live inspection established that the reported failed K07
message was present in the conversation and had an assistant response.
The negative transport acknowledgement was incorrect.

Two coupled defects caused the mismatch:
- A whitespace regular expression inside a JavaScript template literal lost
  its backslash during serialization. The evaluated expression replaced the
  letter s instead of whitespace, as the captured diagnostics demonstrated.
- Comparing the entire user-message container included the localized
  Show more / Mehr anzeigen control for collapsed messages.

The previously proposed multiple-submit strategy was removed before commit:
the observed failure did not justify extra attempts. Native Enter submission
uses a real carriage return rather than a literal backslash-r string.

## Repair contract

A shared, self-contained DOM observation function is serialized with toString
for CDP and used directly by the content script. This preserves regex syntax
and keeps both readers consistent. Message content is read independently of
toggle controls; block wrappers, line breaks, inline markup and non-breaking
spaces normalize to the same text. Different or truncated content is rejected.

Commit evidence must belong to a new user-message ID (or a new position for
messages without IDs), on the same conversation URL. An older identical
message cannot confirm a new request. Missing acknowledgement with an empty
or changed composer remains INDETERMINATE, never permission for blind replay.

Correlated browser transport observations persist on the existing MissionState
without changing task authority or claiming completion. The desktop surface
shows a transport failure instead of claiming that the task is working.

## Validation

- Regression first: 3 of 4 behavioral native tests failed before the repair.
- After repair: all four pass, including old-message rejection and changed-text
  rejection. Seven additional markup/whitespace variants pass.
- Full Python suite: PASS.
- Final full Playwright suite including all seven added variants: 49 passed.
- Final focused native/content suite: 13 passed.
- Kit check, doctor and protected-diff plan: PASS.
- Browser tests now run in the existing CI gate; source and projection agree.

## Live evidence

Chrome's installed unpacked bridge was verified to load from the Cockpit
checkout and explicitly reloaded along with the conversation.

Existing LIVE read-only probe mission 33651994-2368-44e0-9755-36fbad491def:
- Start prompt committed: 1ecdcc31-8787-453a-8ae6-be2cb64067b0.
- Assistant produced the bounded repository-status work order.
- Local result delivered: action db47e061-11f7-4dc1-9568-b3b5d7498507.
- Result prompt committed: f3347eb3-2cc6-4e97-80ff-bea5e3582696.
- A subsequent assistant response was visible.
- The operator stopped the bounded probe after this round trip.

Both sends recorded NATIVE_USER_TURN_COMMITTED and NATIVE_SEND_ACCEPTED.
The probe proves the repaired transport and its result-return path. It does
not close the broader K07 product acceptance or the historical three-turn
systemic-review exit criterion.

The old READY/zero-step mission projection remains distinct from durable
task progress; transport observations are diagnostic, not completion evidence.

## Desktop restart follow-up

After merging the transport repair, the local desktop restart exposed another
failure in the same delivered path: the optional AppleScript Chrome-navigation
call raised an uncaught subprocess error and terminated startup. Its stderr was
discarded, so this record does not attribute the failure to a specific macOS
permission or Chrome defect.

The existing macOS browser adapter now bounds both startup navigation and
single-tab wakeup to ten seconds, returns a controlled diagnostic, and never
replays an uncertain work order. Startup keeps the desktop and bridge available
when navigation fails. It records `chatgpt_requested: false`; extension readiness
still comes from the existing fresh-handshake check, not from that failed call.
No permissions or security settings are changed.

Five added behavioral cases failed before the repair and pass afterward.
Additional success/no-tab/multiple-tab regressions preserve the conservative
reload contract. The maintainer's next manual acceptance test remains pending;
this follow-up does not claim K07 completion or a further live mission.
