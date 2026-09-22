# Runtime Path Authority

This repository uses distinct paths for versioned source, local command-file
evidence, the production desktop bridge, and the built macOS application.
These paths are part of the runtime contract and must not be duplicated as
independent literals in feature code.

| Responsibility | Authoritative location |
|---|---|
| Versioned source, tests, and documentation | repository root |
| Remote Python work orders, `run_next.py`, return bundles, and runner logs | `<repository>/Download/` |
| Production desktop settings | `~/Library/Application Support/AGP Cockpit/settings.json` |
| Production Bridge runtime, token, operator control, task database, file-loop state, and browser handshake | `~/Library/Application Support/AGP Cockpit/bridge/` |
| Built macOS application | `<repository>/.local/agp-cockpit/dist/AGP Cockpit.app` |
| Staged browser extension | `~/Library/Application Support/AGP Cockpit/chrome_extension/` |

## Mandatory Rules

1. Production Bridge state is owned by `bridge_runtime_root()` in
   `src/agp_cockpit/adapters/macos_settings.py`.
2. Every desktop component that reads or writes Bridge control state must use
   that helper. In particular, `TaskOperatorAPI` and `bridge_server` must use
   the same `operator-control.json`.
3. `~/.local/share/agp-cockpit/runtime/` is not a production runtime path.
   It must not be used for Bridge control, task state, or file-loop state.
4. `Download/` is local evidence and is intentionally not the Bridge runtime.
   A command file is executed only through `Download/run_next.py`.
5. Build output is not the source of truth. After a build, launch the exact
   quoted application path shown above and verify startup status before manual
   browser testing.
6. The extension `build_identity.js`, the staged `.agp-stage.json`, and the
   browser handshake `build_id` must match in addition to the extension
   version. A matching version alone is insufficient evidence that Chrome runs
   the current code.
7. `.agp-stage.json` is the runtime identity record. It must identify the
   repository root, source extension, staged extension, `Download/`, and
   `Download/run_next.py`. A missing or contradictory record is a startup
   failure, not a reason to continue with a best-effort run.
8. A browser handshake is valid only when its timestamp is within the
   configured freshness window and its ChatGPT conversation ID matches the
   conversation URL persisted on the current mission. A valid version/build
   pair from another or stale tab is not sufficient evidence.
9. A desktop restart clears the persisted current-mission pointer after
   preserving the prior mission evidence. A reconnect must observe `IDLE` and
   require explicit creation of a new mission; terminal or stopped missions
   are never the implicit startup target.
10. The `EXTENSION_HANDSHAKE` writer and every production handshake reader must
    use the same injected `bridge_runtime_root()`. The repository-local
    `.local/agp-cockpit/bridge/` directory is not a production identity source.

Tests must fail if a production component introduces a second operator-control
path or if the task operator and Bridge no longer resolve to the same runtime
root.
