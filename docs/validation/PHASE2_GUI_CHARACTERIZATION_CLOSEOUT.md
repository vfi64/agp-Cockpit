# Phase 2 GUI Characterization Closeout

Status: COMPLETE

## Provenance

The working GUI is invoked through `python -m agp_cockpit`. Git history was used as the
behavioral provenance source rather than inventing a separate legacy fixture. The selected
historical baseline is commit `31497cc4e64dde852554e6833e60661556ea6425`.

## Characterized domains

1. Ollama discovery and read-only runtime observation.
2. Hermes runtime/configuration discovery.
3. Startup decision behavior.
4. Ollama process lifecycle boundaries using injected fakes.
5. Hermes model update/backup/restore using temporary files.
6. Headless MainWindow delegation/status/model-update behavior.

## Safety boundary

Automated characterization does not start or stop the user's live Ollama/Hermes processes,
does not construct/control the user's live Tk GUI, and does not write the real
`~/.hermes/config.yaml`.

## Evidence

- `tests/test_phase2_core_behavior_characterization.py`
- `tests/test_phase2_mutation_safety_characterization.py`
- `tests/test_phase2_mainwindow_delegation_characterization.py`

Step 159 assessed all six required domains as explicitly covered and the Phase-2 boundary
as `SUFFICIENT`. A manual smoke test remains appropriate before release/closeout.

## Decision

Phase 2 characterization is complete. Further work should proceed from these executable
behavior contracts rather than historical symbol-name assumptions.
