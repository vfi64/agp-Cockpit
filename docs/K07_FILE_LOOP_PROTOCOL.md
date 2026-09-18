# K07 Decomplexified Command-File / Result-File Loop

Status: canonical implementation contract.

The remote model does not emit executable work orders in prose. Each non-terminal turn returns exactly one Python command file. Browser transport downloads that file and passes its local path to the Cockpit. The Cockpit renumbers/copies it into `Download/` and executes it only through `Download/run_next.py`.

`run_next.py` remains the execution authority for compile, self-test, and the real run. Exactly one newly created `<step>_*_return_bundle.json` is required. Zero or multiple bundles fail loudly. The result bundle and the run log `Download/__run_next_output.txt` are attached to the same ChatGPT conversation as file evidence; the log is the fallback diagnostic when the command does not produce a usable result bundle. Result JSON and log text are never copied into the composer.

Terminal remote text is limited to `AGP_DONE` or `AGP_NEEDS_HUMAN` plus an optional reason. Arbitrary prose is never executable. Duplicate command files are rejected by SHA-256 fingerprint. Pause, resume, stop, and generation fencing remain owned by the Cockpit lifecycle. Repository/GitHub workflow semantics remain owned by the Agentic Project Kit.

Legacy Protocol-v1/browser code remains present only as compatibility infrastructure until end-to-end replacement acceptance proves the decomplexified path. This slice changes the core file-loop contract; browser download wiring is the next acceptance boundary.

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

The bridge returns both the result-file path and the output-log path. The browser attaches both files in one file-input operation before sending the fixed continuation sentence. A replay returns the preserved paths and is marked `replayed`; it does not execute the command or send a second continuation.

### Failure matrix

| Failure | Required local result | Evidence sent to remote model | Allowed next action |
|---|---|---|---|
| missing or unsafe `.py` attachment | fail before execution | authenticated bridge error and diagnostic event | request a new command file |
| compile or self-test failure | failed return bundle if possible | return bundle plus `__run_next_output.txt` | repair command only |
| runtime non-zero exit | failed return bundle | return bundle plus `__run_next_output.txt` | repair command only |
| no return bundle with exit 0 | synthesized failed bundle | synthesized bundle plus `__run_next_output.txt` | repair command only |
| malformed or incomplete JSON bundle | preserve it as untrusted evidence | bundle plus `__run_next_output.txt` and validation metadata | repair command only |
| multiple bundles | fail closed; do not select one | `__run_next_output.txt` and bounded bridge diagnostic | human or repair command after diagnosis |
| result attachment failure | keep local evidence and durable state | no false remote success; retry attachment with same files only | bounded transport retry or human |
| remote returns another `.py` | materialize as next numbered step | previous evidence remains correlated | execute next step |
| remote returns `AGP_DONE` | terminal only after current evidence is available | terminal sentinel and durable completion state | finish |
| remote returns `AGP_NEEDS_HUMAN` | stop without mutation | reason plus preserved evidence | human decision |

The remote model is responsible for semantic evaluation of the attached result, but it cannot convert missing, malformed, or contradictory evidence into `PASS`. Hermes is optional and observational; it may not alter the command, result, authority, or completion state.

### Completion rule

Under the stated availability assumptions, the loop closes when every non-terminal step produces one attached evidence package and the remote model responds either with the next numbered command file or with an explicit terminal sentinel. Any failure in steps 5-7 remains visible through the output log and durable diagnostics. No step is silently treated as complete, and no failed step is blindly replayed.
