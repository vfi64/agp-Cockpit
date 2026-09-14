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
