# Browser Transport Stabilization 086

Status: inventory/contract only; no runtime repair performed.

## Current send-path functions

- `chatgptGenerationActive`
- `missionBootstrapPrompt`
- `normalizeObservedMessageText`
- `observedComposerText`
- `parsePureJsonObject`
- `refreshStatus`
- `resetCandidate`
- `sendPrompt`
- `stop`
- `visibleUserMessages`
- `waitForSentUserMessage`

## Historical markers in active send section

- `AGP_FOLLOWUP_SEND_TARGET_DECISIVE_ACK_066_D4`
- `AGP_MULTI_SIGNAL_SEND_ACCEPTANCE_066_D3`
- `AGP_SAFE_RETRY_UNSENT_CONTINUATION_085`
- `AGP_SEND_ACK_FALSE_NEGATIVE_065L_R11`
- `AGP_STRUCTURED_RESPONSE_COMPLETION_064_R1`

## Relevant tests

- `tests/browser_fixtures/chatgpt_fixture.js` — BEHAVIOR-ORIENTED
- `tests/e2e/test_066_actual_contentjs_send_ack.spec.js` — SOURCE-COUPLED
  - source-coupling signals: `toContain(`
- `tests/e2e/test_066_e6_generation_edge_false_positive.spec.js` — SOURCE-COUPLED
  - source-coupling signals: `toContain(`
- `tests/e2e/test_066_g4_multisignal_send_acceptance.spec.js` — SOURCE-COUPLED
  - exact literals: `STATE.lastEvent = "PROMPT_SENT"`, `button.click()`
  - source-coupling signals: `toContain(`
- `tests/e2e/test_066_send_ack_false_negative_fixture.spec.js` — BEHAVIOR-ORIENTED
- `tests/e2e/test_085_safe_retry_unsent_continuation_prompt.spec.js` — SOURCE-COUPLED
  - source-coupling signals: `toContain(`
- `tests/test_assistant_response_completion_064_r1.py` — SOURCE-COUPLED
  - source-coupling signals: `.index(`
- `tests/test_async_browser_readiness.py` — SOURCE-COUPLED
  - source-coupling signals: `.index(`, `in source`
- `tests/test_browser_integration_lifecycle.py` — SOURCE-COUPLED
  - source-coupling signals: `in source`
- `tests/test_followup_send_path_065l_r7.py` — SOURCE-COUPLED
  - source-coupling signals: `.find(`
- `tests/test_followup_send_target_and_decisive_ack_066_d4.py` — SOURCE-COUPLED
  - exact literals: `STATE.lastEvent = "SEND_UNCONFIRMED"`
  - source-coupling signals: `in SRC`
- `tests/test_generation_edge_ack_066_e7.py` — SOURCE-COUPLED
  - source-coupling signals: `.find(`
- `tests/test_multisignal_send_acceptance_066_d3.py` — SOURCE-COUPLED
  - exact literals: `const acknowledgement = await waitForSentUserMessage(`, `STATE.lastEvent = "PROMPT_SENT"`, `STATE.lastEvent = "SEND_UNCONFIRMED"`
  - source-coupling signals: `.index(`, `in SRC`
- `tests/test_send_ack_false_negative_065l_r11.py` — BEHAVIOR-ORIENTED
- `tests/test_startup_handshake_polish.py` — SOURCE-COUPLED
  - source-coupling signals: `in source`
- `tests/test_verified_followup_send_065l_r10.py` — SOURCE-COUPLED
  - exact literals: `STATE.lastEvent = "PROMPT_SENT"`, `STATE.lastEvent = "SEND_UNCONFIRMED"`
- `tests/test_verified_followup_send_065l_r8.py` — SOURCE-COUPLED
  - exact literals: `const acknowledgement = await waitForSentUserMessage(`, `STATE.lastEvent = "PROMPT_SENT"`, `STATE.lastEvent = "SEND_UNCONFIRMED"`
  - source-coupling signals: `.index(`
- `tests/test_verified_followup_send_065l_r9.py` — SOURCE-COUPLED
  - exact literals: `STATE.lastEvent = "PROMPT_SENT"`, `STATE.lastEvent = "SEND_UNCONFIRMED"`

## Canonical send contract proposed for consolidation

States:
- `IDLE`
- `DRAFT_WRITTEN`
- `SUBMIT_ATTEMPTED`
- `WAITING_FOR_ACCEPTANCE`
- `ACCEPTED`
- `SAFE_RETRY_ELIGIBLE`
- `RETRY_ATTEMPTED`
- `INDETERMINATE`
- `FAILED_CONFIRMATION`

Decisive acceptance signals:
- new exact visible user message
- new ChatGPT generation edge
- new assistant activity after submit

Non-decisive evidence:
- composer cleared
- composer changed
- button click attempted

Safe retry contract:
- `max_retries`: `1`
- `requires_exact_prompt_still_in_composer`: `True`
- `requires_generation_inactive`: `True`
- `must_not_retry_on_missing_user_bubble_alone`: `True`
- `must_not_retry_on_composer_mutation_alone`: `True`

## Process conclusion

The next repair should replace historically layered send heuristics with one explicit transport state machine and migrate implementation-coupled tests to behavior contracts before another LIVE attempt.
