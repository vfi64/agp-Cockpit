# K07 Decomplexified Command-File / Result-File Loop

Status: canonical implementation contract.

The remote model does not emit executable work orders in prose. Each non-terminal turn returns exactly one Python command file. Browser transport downloads that file and passes its local path to the Cockpit. The numeric prefix in the local `Download/` filename is the sole execution step ID; the remote filename is retained only as correlation metadata. A remote retry receives the next local number and cannot overwrite local history. The embedded `STEP` constant and step-scoped output names must match that local number; a mismatch fails closed. `Download/` is intentionally Git-ignored local evidence; the versioned Cockpit executor still validates the resulting artifacts independently.

`run_next.py` remains the execution authority for compile, self-test, and the real run. Exactly one newly created `<step>_*_return_bundle.json` is required. Zero or multiple bundles fail loudly. The result bundle and the run log `Download/__run_next_output.txt` are attached to the same ChatGPT conversation as file evidence; the log is the fallback diagnostic when the command does not produce a usable result bundle. Result JSON and log text are never copied into the composer.

The canonical `Download/run_next.py` is versioned at the authorized root path;
`Download/alt/` (historical material, never an execution source) was removed on
2026-10-02; the five files cited as evidence moved to
`.local/agp-cockpit/archive/cited-evidence/`. Runner
stdout/stderr and the combined runner log are bounded to 256 KiB. A newly
created return bundle is bounded to 2,000,000 bytes, matching the transport
frame limit. An oversized bundle is retained locally for diagnosis but is
rejected and replaced by a small diagnostic bundle; it is never attached as a
successful result. Work orders must not recursively scan or embed historical
`Download/` evidence. They must emit a bounded summary and refer to evidence by
path, digest, and size.

`run_next.py` is owned by one process controller per Bridge instance. The
controller starts it in a dedicated process group and terminates the complete
group on timeout, explicit stop, Bridge shutdown, or forced cleanup. A timeout
or stop never becomes a successful result: it creates one diagnostic artifact
with `status: "unknown"` and `outcome: "OUTCOME_UNKNOWN"`, preserves the
runner log and any candidate bundles, and requires remote reconciliation before
any retry. In the production Bridge, `BridgeRuntime.stop()` is bound to the
same `RunNextProcessController` that owns execution; it requests process-group
termination first and persists mission state second. A standalone runtime
without that binding is state-only and must not be used as the K07 process
authority. `FileLoopLifecycle` only controls generation admission and must not
claim to terminate a process. The authoritative K07 stop contract is therefore
explicit: `OperatorControlStore` blocks new command admission,
`RunNextProcessController` terminates the active process group, and the bound
`BridgeRuntime.stop()` coordinates both actions. Other `stop()`/`cancel()`
methods belong to separate task, terminal, or service scopes and must not be
presented as K07 process termination.

Terminal remote text is limited to `AGP_DONE` or `AGP_NEEDS_HUMAN` plus an optional reason. Arbitrary prose is never executable. Duplicate command files are rejected by SHA-256 fingerprint. Pause, resume, stop, and generation fencing remain owned by the Cockpit lifecycle. Repository/GitHub workflow semantics remain owned by the Agentic Project Kit.

Legacy Protocol-v1/browser code remains present only as compatibility infrastructure until end-to-end replacement acceptance proves the decomplexified path. This slice changes the core file-loop contract; browser download wiring is the next acceptance boundary.

The file loop and browser loop share one mission-scoped `AutomationGuard`.
The guard is reset only when a new mission is created. Every accepted file-loop
turn is checked against the same turn and runtime budgets, assistant-response
repeat detection, prompt-repeat detection, and consecutive-error budget. The
file loop must never maintain a second counter. Exhaustion is persisted as the
terminal mission state `BLOCKED`; it is not converted into another recovery
prompt or an implicit restart.

Command-file preflight failures are a separate bounded class. A syntax,
indentation, or semantic-contract failure is detected before `run_next.py`
starts and therefore proves that no Kit command ran. The first such failure
may produce exactly one recovery prompt with the diagnostic bundle and runner
log. A second preflight failure in the same mission is terminal `BLOCKED`; it
does not create a third remote turn. A successful local run resets this
preflight-failure counter. This prevents truncated remote files from turning
into an open-ended sequence of newly numbered files.

The persisted `file-loop-state.json` is mission-scoped as well: when a new
mission ID arrives, old failure counters, replay history, and terminal state
are discarded for admission purposes. Prior return bundles and logs remain
immutable evidence, but they cannot block the first command of a new mission.

A desktop restart is a fresh authority boundary. The Bridge stops any
non-terminal mission left by the previous process, preserves that mission's
per-mission evidence file, and clears the `current.json` pointer. A browser
reconnect therefore observes `IDLE` with no active mission; it must not revive
or display an old `STOPPED`, `READY`, or `FULL_AUTO` mission as the new start
state. A new standard task creates a new mission explicitly.

## Closed-loop execution contract

The normal non-terminal cycle is a bounded state machine, not a best-effort prompt exchange:

`REMOTE_COMMAND_ATTACHED -> COMMAND_MATERIALIZED -> RUN_NEXT_STARTED -> SELF_TEST_PASSED -> LOCAL_RUN_FINISHED -> RESULT_EVIDENCE_READY -> RESULT_FILES_ATTACHED -> REMOTE_EVALUATED -> next command | AGP_DONE | AGP_NEEDS_HUMAN`

The Cockpit may advance only on evidence for the current transition. A browser acknowledgement, a zero exit code, or a visible success sentence is not completion evidence by itself.

A Python command file must perform the authorized local operation and write its own canonical return bundle. JSON printed to stdout that merely describes `argv`, `cwd`, or a proposed work order is diagnostic text, not execution evidence; the runner reports it as a failed step and returns the stdout log for repair.

### Evidence package

Every attempted local step has these correlated values:

- the numbered command path in `Download/`;
- the command SHA-256 and cycle id;
- the runner return code;
- `Download/__run_next_output.txt`;
- exactly one newly created canonical return bundle when the runner can produce one;
- the SHA-256 of every file sent back to the remote conversation.

The bridge returns both the result-file path and the output-log path together with a continuation prompt derived from the result status. The stable human entry point remains `cd <repository> && python3 Download/run_next.py <STEP>`. Internally, `run_next.py` also creates an immutable `Download/<STEP>_run_next_output.txt` snapshot; an explicit rerun receives a non-overwriting timestamp suffix. The browser attaches both files in one file-input operation before sending that exact prompt. A failed step therefore tells the remote model explicitly that recovery is required, whether the real run was reached, and that a new numbered command file must be returned. A replay returns the preserved paths and is marked `replayed`; it does not execute the command or send a second continuation. A command rejected by the semantic preflight is the exception: because `run_next.py` never started, a later authoritative remote step with the same content may retry under its own numeric filename instead of being stranded behind the old failed record.

### Failure matrix

| Failure | Required local result | Evidence sent to remote model | Allowed next action |
|---|---|---|---|
| missing or unsafe `.py` attachment | fail before execution | authenticated bridge error and diagnostic event | request a new command file |
| compile, syntax, or self-test failure | failed return bundle if possible | return bundle plus `__run_next_output.txt` and recovery prompt | one bounded repair command; second preflight failure is `BLOCKED` |
| runtime non-zero exit | failed return bundle | return bundle plus `__run_next_output.txt` and recovery prompt | repair command only |
| no return bundle with exit 0 | synthesized failed bundle | synthesized bundle plus `__run_next_output.txt` and recovery prompt | repair command only |
| malformed or incomplete JSON bundle | preserve the raw candidate and create one failed diagnostic bundle | diagnostic bundle naming the raw candidate plus `__run_next_output.txt` and recovery prompt | repair command only |
| multiple bundles | fail closed; do not select one | `__run_next_output.txt` and bounded bridge diagnostic | human or repair command after diagnosis |
| result attachment failure | keep local evidence and durable state | no false remote success; retry attachment with same files only | bounded transport retry or human |
| remote returns another `.py` | preserve its numeric filename step and reject stale/colliding IDs; retry a prior non-executed preflight failure under the new authoritative step | previous evidence remains correlated | execute that exact step |
| remote returns `AGP_DONE` | terminal only after current evidence is available | terminal sentinel and durable completion state | finish |
| remote returns `AGP_NEEDS_HUMAN` | stop without mutation | reason plus preserved evidence | human decision |
| runner timeout or operator stop | terminate the complete runner process group and materialize `OUTCOME_UNKNOWN` | diagnostic bundle plus `__run_next_output.txt` | reconcile evidence before retry; never claim success |
| shared guard budget or repeat limit exhausted | persist `BLOCKED` and preserve the triggering state | bounded diagnostic and current loop state | explicit new mission after diagnosis |

The remote model is responsible for semantic evaluation of the attached result, but it cannot convert missing, malformed, or contradictory evidence into `PASS`. Hermes is optional and observational; it may not alter the command, result, authority, or completion state.

### Completion rule

Under the stated availability assumptions, the loop closes when every non-terminal step produces one attached evidence package and the remote model responds either with the next numbered command file or with an explicit terminal sentinel. Any failure in steps 5-7 remains visible through the output log and durable diagnostics. No step is silently treated as complete, and no failed step is blindly replayed.
