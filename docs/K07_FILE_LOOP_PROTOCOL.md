# K07 Decomplexified Command-File / Result-File Loop

Status: implementation slice.

The remote model does not emit executable work orders in prose. Each non-terminal turn returns exactly one Python command file. Browser transport downloads that file and passes its local path to the Cockpit. The Cockpit renumbers/copies it into `Download/` and executes it only through `Download/run_next.py`.

`run_next.py` remains the execution authority for compile, self-test, and the real run. Exactly one newly created `<step>_*_return_bundle.json` is required. Zero or multiple bundles fail loudly. The result bundle is attached to the same ChatGPT conversation; only a fixed bounded continuation sentence is sent as text. Result JSON is never copied into the composer.

Terminal remote text is limited to `AGP_DONE` or `AGP_NEEDS_HUMAN` plus an optional reason. Arbitrary prose is never executable. Duplicate command files are rejected by SHA-256 fingerprint. Pause, resume, stop, and generation fencing remain owned by the Cockpit lifecycle. Repository/GitHub workflow semantics remain owned by the Agentic Project Kit.

Legacy Protocol-v1/browser code remains present only as compatibility infrastructure until end-to-end replacement acceptance proves the decomplexified path. This slice changes the core file-loop contract; browser download wiring is the next acceptance boundary.
