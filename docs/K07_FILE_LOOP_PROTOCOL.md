# K07 Command-File / Result-File Protocol

Status: transition foundation.

The remote model has exactly three protocol states:

1. `AGP_COMMAND_FILE_BEGIN` ... `AGP_COMMAND_FILE_END`
2. `AGP_DONE`
3. `AGP_NEEDS_HUMAN`

Execution semantics remain local. A command block is persisted as the next numbered
Python file in the local Download workspace. Existing `run_next.py` remains the
execution authority for compile, self-test and real run. Large result payloads
are to return as files, not as JSON work orders embedded in composer text.

This module deliberately does not yet execute commands or automate file upload.
Those are subsequent acceptance slices.

## Local runner integration

Persisted command files execute only through `Download/run_next.py`. The adapter snapshots matching return bundles before execution and accepts exactly one newly created `<step>_*_return_bundle.json` afterwards. Zero or multiple new bundles fail loudly. Browser automation is not part of this slice.

## Exactly-once loop foundation

Each complete remote reply is fingerprinted. Re-consumption of the same reply fails loudly. `AGP_DONE` and `AGP_NEEDS_HUMAN` are terminal local states. A command reply is persisted and executed through the existing runner, and the resulting bundle path is persisted as loop state. Browser file upload remains the next transport slice.
