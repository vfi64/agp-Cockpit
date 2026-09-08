# Phase 9 — FILE_TRANSFER pass-through acceptance

**Status: PASS**  
**Date: 2026-09-08**

## Product authority

Phase 9 proves that FILE_TRANSFER does not create a second Cockpit workflow engine. The browser LLM supplies the Protocol-v1 work order. Cockpit performs deterministic presentation canonicalization, strict Protocol-v1 validation, opaque local dispatch, bounded result handling, and return to the same browser conversation. FILE_TRANSFER semantics remain Kit-owned.

## Real-browser acceptance

The controlled real-browser acceptance used action `phase9-file-transfer-e2e-460-01` in mode `FILE_TRANSFER`.

The browser LLM reproduced the previously observed serialization defect: nested JSON in `work_order.content` lost the required escaping. The production deterministic canonicalizer repaired only that presentation form. The strict Protocol-v1 parser then accepted the canonical action.

Cockpit dispatched the canonical terminal payload unchanged to the actual local command:

`agentic-kit transfer remote-next --json`

The Kit process ran and returned `RC=2` with `missing_transfer_order`. That semantic/lifecycle result is external to the Phase-9 Cockpit pass-through acceptance. Cockpit returned the bounded result to the same ChatGPT conversation. All eight Step-460 E2E acceptance predicates were true.

## Turn counter adjudication

The overlay remained at `Turns 0 / 40` because Step 460 deliberately invoked the Phase-7 single-round controller directly. Source review found no contract requiring a direct `runOneRound()` call to increment the P8/mission counter. P8 owns multi-round accounting through its completed-round callback/result. Previous P8 browser evidence showed `1 / 40` for one P8 round and `2 / 40` for two P8 rounds.

Classification: **expected separation; no Cockpit defect evidence**.

## Architectural exclusions

No Cockpit GitHub API/client for FILE_TRANSFER was added. No Cockpit transfer-order generator, validator, polling/synchronization/correlation state machine, handcrafted transfer YAML, or Kit lifecycle repair logic was added.

## External Kit findings

GF010, GF019, KIT-GF-011, the generated transfer archive/runtime PR-preflight conflict, and the pre-existing-diff ownership-transition limitation remain recorded as Kit findings. They are not Phase-9 Cockpit features and must be repaired later only in `agentic-project-kit`.

## Final gates

- Phase-9/adjacent targeted tests: PASS
- Full pytest suite using repository `.venv`: PASS
- `agentic-kit check --root .`: PASS
- `git diff --check`: PASS before evidence generation

**Phase 9 product acceptance: COMPLETE.**
