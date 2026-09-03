# Systemic Failure Review — Browser Transport (089)

Status: active
Decision status: accepted
Review policy: on material change

Failure domain: `browser transport / ChatGPT send acknowledgement`
Escalation level: `R2`

## 1. Failure history

### 065-066

send acknowledgement false negatives and multi-signal heuristics accumulated around follow-up sends

Classification: `browser transport`

### 074

terminal DONE/NEEDS_HUMAN incorrectly passed through work-order assertions

Classification: `browser transport / response classification`

### 075-079R1

real browser first-turn path proven; assistant pickup reached server; runtime-budget defect then exposed

Classification: `cross-boundary diagnostic`

### 080B-080B_R1

automation runtime budget corrected to mission scope

Classification: `runtime lifecycle, separate from browser transport`

### 081-082R1

single-step LIVE round trip reached DONE; terminal summary/error semantics repaired

Classification: `runtime semantics, separate from browser transport`

### 083-084

continuation prompt generated but remained unsent; failure localized to continuation send/ack path

Classification: `browser transport`

### 085-086

safe retry added; Playwright green, Python suite exposed brittle source-coupled tests; systemic inventory found 15/18 source-coupled tests

Classification: `browser transport + test model`

## 2. Failure-domain clustering

The recurring defect cluster is the browser transport/send-acknowledgement boundary.
Runtime-budget and terminal-summary defects were real but separate and are already repaired.
The same Browser Sender path repeatedly reappears after local fixes, satisfying R2 recurrence.

## 3. Architecture / state-transition map

- **Mission/Runtime** — mission state, turn/step counts, execution result, terminal state — *proven functional for single-step LIVE*
- **Browser Sender** — populate composer, submit prompt, determine send acceptance — *recurring failure domain*
- **Assistant Observer** — detect complete assistant response and structured JSON — *proven functional in real browser*
- **Bridge/Executor** — validate work order, execute bounded command, return result — *proven functional in real LIVE run*
- **Continuation Controller** — turn result into next prompt or terminal state — *prompt generation proven; transport of prompt remains unstable*

Canonical Browser Sender transport states:

```text
IDLE
  -> DRAFT_WRITTEN
  -> SUBMIT_ATTEMPTED
  -> WAITING_FOR_ACCEPTANCE
       -> ACCEPTED
       -> SAFE_RETRY_ELIGIBLE
            -> RETRY_ATTEMPTED
                 -> ACCEPTED
                 -> FAILED_CONFIRMATION
       -> INDETERMINATE
```

## 4. Test-model audit

Relevant tests: **18**
Source-coupled: **15**
Behavior-oriented: **3**

### Source-coupled tests

- `tests/e2e/test_066_actual_contentjs_send_ack.spec.js` — source-string/index assertions
- `tests/e2e/test_066_e6_generation_edge_false_positive.spec.js` — source-string/index assertions
- `tests/e2e/test_066_g4_multisignal_send_acceptance.spec.js` — exact source literals, source-string/index assertions
- `tests/e2e/test_085_safe_retry_unsent_continuation_prompt.spec.js` — source-string/index assertions
- `tests/test_assistant_response_completion_064_r1.py` — source-string/index assertions
- `tests/test_async_browser_readiness.py` — source-string/index assertions
- `tests/test_browser_integration_lifecycle.py` — source-string/index assertions
- `tests/test_followup_send_path_065l_r7.py` — source-string/index assertions
- `tests/test_followup_send_target_and_decisive_ack_066_d4.py` — exact source literals, source-string/index assertions
- `tests/test_generation_edge_ack_066_e7.py` — source-string/index assertions
- `tests/test_multisignal_send_acceptance_066_d3.py` — exact source literals, source-string/index assertions
- `tests/test_startup_handshake_polish.py` — source-string/index assertions
- `tests/test_verified_followup_send_065l_r10.py` — exact source literals
- `tests/test_verified_followup_send_065l_r8.py` — exact source literals, source-string/index assertions
- `tests/test_verified_followup_send_065l_r9.py` — exact source literals

### Behavior-oriented tests

- `tests/browser_fixtures/chatgpt_fixture.js`
- `tests/e2e/test_066_send_ack_false_negative_fixture.spec.js`
- `tests/test_send_ack_false_negative_065l_r11.py`

Conclusion: `TEST_MODEL_REPAIR_REQUIRED`.

The two currently failing Python tests are classified as
`IMPLEMENTATION_COUPLED_TEST_REGRESSION`, not as demonstrated product regressions.

## 5. Patch-history audit

Active historical send-path markers:

- `AGP_FOLLOWUP_SEND_TARGET_DECISIVE_ACK_066_D4`
- `AGP_MULTI_SIGNAL_SEND_ACCEPTANCE_066_D3`
- `AGP_SAFE_RETRY_UNSENT_CONTINUATION_085`
- `AGP_SEND_ACK_FALSE_NEGATIVE_065L_R11`
- `AGP_STRUCTURED_RESPONSE_COMPLETION_064_R1`

The accumulated marker/heuristic history shows that another local repair would continue
the patch spiral rather than reduce system complexity.

## 6. Root-cause hypotheses

- **implicit state machine** — confidence `high` — multiple historical marker layers and heuristics accumulated in sendPrompt/waitForSentUserMessage without one explicit transport state authority
- **test architecture defect** — confidence `high` — 15/18 relevant tests classified source-coupled; known failures depend on exact `const` source spelling
- **fixture/live model mismatch** — confidence `high` — full Playwright suite passes while real ChatGPT continuation send remains unsent
- **local single-line bug** — confidence `low` — repeated symptom changes after local patches indicate systemic rather than isolated failure

## 7. Decision

Primary decision: **`REFACTOR_SUBSYSTEM`**

Required companion action: **`TEST_MODEL_REPAIR`**

The recurring failure is concentrated in Browser Sender state/acknowledgement semantics, while Mission Runtime, Assistant Observer, Bridge/Executor and single-step LIVE execution are already proven. The current sender contains layered heuristics and the regression model is dominated by source-coupled tests. Another local patch is not justified.

Therefore `PATCH_LOCAL` is explicitly rejected for the next step.

## Next-work contract

- Do not make another symptom patch to sendPrompt.
- Replace brittle source-coupled send-path tests with behavioral state-transition contracts.
- Extract/consolidate browser sending into one explicit transport state machine with one bounded retry policy.
- Preserve decisive vs provisional acknowledgement semantics.
- Run unit/fixture behavioral contracts first.
- Run full Playwright suite second.
- Run full Python suite third.
- Only then run one fresh single-step LIVE confirmation.
- After single-step PASS, run one fresh 3-turn LIVE confirmation.

## Exit criteria

The Browser Transport systemic review may be considered closed only when:

1. the sender is represented by one explicit transport state machine,
2. source-coupled legacy assertions have been replaced or justified,
3. the full Python and Playwright suites are green,
4. one fresh real single-step LIVE mission reaches DONE without manual intervention, and
5. one fresh real 3-turn LIVE mission reaches DONE without manual intervention.
