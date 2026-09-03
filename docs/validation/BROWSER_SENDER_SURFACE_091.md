# Browser Sender Surface Snapshot (091)

Status: active
Decision status: accepted
Review policy: on material change

Purpose: freeze the exact pre-refactor Browser Sender implementation surface after
the 089 systemic review and 090 test-model repair.

## Contract summary

```json
{
  "wait_signals": {
    "user_message": true,
    "composer_cleared": true,
    "composer_changed": true,
    "generation_started": true,
    "assistant_activity": true,
    "timeout": true
  },
  "send_contract": {
    "populates_composer": true,
    "snapshots_composer": true,
    "snapshots_generation": true,
    "waits_for_ack": true,
    "has_unconfirmed_branch": true,
    "has_safe_retry_marker": true,
    "marks_prompt_sent": true,
    "throws_send_unconfirmed": true
  }
}
```

## Historical AGP markers

- line 49: `AGP_OVERLAY_DRAG_MINIMIZE_063S2`
- line 72: `AGP_BROWSER_BUSY_INDICATOR_064_R2`
- line 276: `AGP_REFRESH_INTEGRATION`
- line 333: `AGP_SEND_ACK_FALSE_NEGATIVE_065L_R11`
- line 342: `AGP_FOLLOWUP_SEND_TARGET_DECISIVE_ACK_066_D4`
- line 343: `AGP_MULTI_SIGNAL_SEND_ACCEPTANCE_066_D3`
- line 493: `AGP_SAFE_RETRY_UNSENT_CONTINUATION_085`
- line 550: `AGP_STRUCTURED_RESPONSE_COMPLETION_064_R1`
- line 609: `AGP_LIVE_PROBE_TERMINAL_SIGNAL_074`
- line 651: `AGP_TURN_ACCOUNTING_064_R1`
- line 797: `AGP_MULTITURN_LIVE_PROBE_065`
- line 1102: `AGP_START_AUTO_CLICK_PATH_077`
- line 1144: `AGP_OVERLAY_DRAG_MINIMIZE_063S2`
- line 1145: `AGP_OVERLAY_UI_KEY`
- line 1146: `AGP_OVERLAY_UI`
- line 1147: `AGP_OVERLAY_UI_LOADED`
- line 1148: `AGP_DRAG`
- line 1151: `AGP_OVERLAY_UI_LOADED`
- line 1152: `AGP_OVERLAY_UI_LOADED`
- line 1154: `AGP_OVERLAY_UI_KEY`
- line 1155: `AGP_OVERLAY_UI_KEY`
- line 1157: `AGP_OVERLAY_UI`
- line 1168: `AGP_OVERLAY_UI_KEY`
- line 1168: `AGP_OVERLAY_UI`
- line 1183: `AGP_OVERLAY_UI`
- line 1184: `AGP_OVERLAY_UI`
- line 1184: `AGP_OVERLAY_UI`
- line 1185: `AGP_OVERLAY_UI`
- line 1185: `AGP_OVERLAY_UI`
- line 1197: `AGP_DRAG`
- line 1206: `AGP_DRAG`
- line 1208: `AGP_DRAG`
- line 1209: `AGP_DRAG`
- line 1210: `AGP_DRAG`
- line 1212: `AGP_DRAG`
- line 1213: `AGP_DRAG`
- line 1214: `AGP_DRAG`
- line 1215: `AGP_DRAG`
- line 1216: `AGP_OVERLAY_UI`
- line 1217: `AGP_OVERLAY_UI`
- line 1221: `AGP_DRAG`
- line 1222: `AGP_DRAG`
- line 1231: `AGP_OVERLAY_UI`
- line 1231: `AGP_OVERLAY_UI`
- line 1232: `AGP_OVERLAY_UI`
- line 1232: `AGP_OVERLAY_UI`
- line 1233: `AGP_OVERLAY_UI`
- line 1234: `AGP_OVERLAY_UI`
- line 1308: `AGP_OVERLAY_UI`
- line 1309: `AGP_OVERLAY_UI`
- line 1314: `AGP_OVERLAY_UI`
- line 1314: `AGP_OVERLAY_UI`

## Function call-site lines

- `visibleUserMessages`: [321, 387, 427]
- `normalizeObservedMessageText`: [334, 348, 350, 379, 380, 381, 389, 409, 496]
- `observedComposerText`: [344, 397, 433, 495]
- `chatgptGenerationActive`: [355, 404, 434, 499]
- `waitForSentUserMessage`: [371, 485, 514]
- `sendPrompt`: [422, 664, 1021, 1084]

## Exact function snapshots

### `visibleUserMessages`

```javascript
function visibleUserMessages() {
    return Array.from(
      document.querySelectorAll('[data-message-author-role="user"]')
    )
      .filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      })
      .map(el => (el.innerText || el.textContent || "").trim())
      .filter(Boolean);
  }
```

### `normalizeObservedMessageText`

```javascript
function normalizeObservedMessageText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
```

### `observedComposerText`

```javascript
function observedComposerText() {
    const el = composer();
    if (!el) return "";
    if (el instanceof HTMLTextAreaElement) {
      return normalizeObservedMessageText(el.value || "");
    }
    return normalizeObservedMessageText(
      el.innerText || el.textContent || el.getAttribute("data-lexical-text") || ""
    );
  }
```

### `chatgptGenerationActive`

```javascript
function chatgptGenerationActive() {
    const selectors = [
      'button[data-testid="stop-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop response"]',
      'button[aria-label*="Generierung stoppen"]',
      'button[aria-label*="Antwort stoppen"]',
      '[data-is-streaming="true"]',
      '[data-testid="stop-generating-button"]'
    ];
    return selectors.some(selector => {
      const el = document.querySelector(selector);
      return Boolean(el && !el.disabled);
    });
  }
```

### `waitForSentUserMessage`

```javascript
async function waitForSentUserMessage(
    prompt,
    beforeMessages,
    beforeAssistantText="",
    beforeComposerText="",
    beforeGenerationActive=false
  ) {
    const beforeCount = beforeMessages.length;
    const expected = normalizeObservedMessageText(prompt);
    const assistantBefore = normalizeObservedMessageText(beforeAssistantText);
    const composerBefore = normalizeObservedMessageText(beforeComposerText);
    let provisionalComposerEvidence = "";

    for (let i = 0; i < 60; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));

      const after = visibleUserMessages();
      if (after.length > beforeCount) {
        const newest = normalizeObservedMessageText(after[after.length - 1]);
        if (newest === expected) {
          return {confirmed:true, via:"user_message"};
        }
      }

      // Composer mutation alone is not decisive. React/editor re-renders can clear
      // or replace the draft even when no user message was actually submitted.
      const composerNow = observedComposerText();
      if (composerBefore && composerNow !== composerBefore) {
        provisionalComposerEvidence = !composerNow
          ? "composer_cleared"
          : "composer_changed";
      }

      const generationNow = chatgptGenerationActive();
      if (generationNow && !beforeGenerationActive) {
        return {confirmed:true, via:"generation_started"};
      }

      const assistantNow = normalizeObservedMessageText(lastAssistantText());
      if (assistantNow && assistantNow !== assistantBefore) {
        return {confirmed:true, via:"assistant_activity"};
      }
    }

    return {
      confirmed:false,
      via:"timeout",
      provisional:provisionalComposerEvidence
    };
  }
```

### `sendPrompt`

```javascript
async function sendPrompt(prompt) {
    if (prompt === STATE.lastPrompt) {
      throw new Error("identical prompt loop detected");
    }

    const beforeMessages = visibleUserMessages();
    const beforeAssistantText = lastAssistantText();
    const composerEl = composer();
    if (!composerEl) throw new Error("ChatGPT composer not found");
    STATE.lastPrompt = prompt;
    setComposerText(composerEl, prompt);
    const beforeComposerText = observedComposerText();
    const beforeGenerationActive = chatgptGenerationActive();

    let sentAttempt = false;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const button = sendButton(composerEl);
      if (button && !button.disabled) {
        button.click();
        sentAttempt = true;
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 150));
    }

    if (!sentAttempt) {
      const el = composer();
      const form = el && el.closest ? el.closest("form") : null;
      if (form && typeof form.requestSubmit === "function") {
        form.requestSubmit();
        sentAttempt = true;
      }
    }

    if (!sentAttempt) {
      const el = composer();
      if (!el) throw new Error("ChatGPT composer not found");
      el.focus();
      const down = new KeyboardEvent("keydown", {
          key:"Enter",
          code:"Enter",
          keyCode:13,
          which:13,
          bubbles:true,
          cancelable:true
        });
      const up = new KeyboardEvent("keyup", {
          key:"Enter",
          code:"Enter",
          keyCode:13,
          which:13,
          bubbles:true,
          cancelable:true
        });
      el.dispatchEvent(down);
      el.dispatchEvent(up);
      sentAttempt = true;
    }

    if (!sentAttempt) {
      throw new Error("send path unavailable");
    }

    let acknowledgement = await waitForSentUserMessage(
      prompt,
      beforeMessages,
      beforeAssistantText,
      beforeComposerText,
      beforeGenerationActive
    );

    // AGP_SAFE_RETRY_UNSENT_CONTINUATION_085
    if (!acknowledgement.confirmed) {
      const pendingComposer = observedComposerText();
      const expectedPrompt = normalizeObservedMessageText(prompt);
      const safeToRetry = (
        pendingComposer === expectedPrompt &&
        !chatgptGenerationActive()
      );

      if (safeToRetry) {
        await clientEvent("SEND_RETRY_SAFE_PENDING_COMPOSER", {
          chars:prompt.length,
          first_via:acknowledgement.via || "",
          provisional:acknowledgement.provisional || ""
        });

        const retryComposer = composer();
        const retryButton = sendButton(retryComposer);
        if (retryButton && !retryButton.disabled) {
          retryButton.click();

          acknowledgement = await waitForSentUserMessage(
            prompt,
            beforeMessages,
            beforeAssistantText,
            expectedPrompt,
            false
          );

          await clientEvent(
            acknowledgement.confirmed
              ? "SEND_RETRY_CONFIRMED"
              : "SEND_RETRY_UNCONFIRMED",
            {
              via:acknowledgement.via || "",
              provisional:acknowledgement.provisional || ""
            }
          );
        }
      }
    }

    if (!acknowledgement.confirmed) {
      STATE.lastEvent = "SEND_UNCONFIRMED";
      throw new Error("SEND_UNCONFIRMED: expected user message did not appear");
    }

    STATE.lastEvent = "PROMPT_SENT";
    STATE.note = `Prompt bestätigt via ${acknowledgement.via}`;
  }
```

## Refactor boundary

092 may change Browser Sender implementation only after preserving the behavior
contracts demonstrated by the full Python and Playwright suites at Step 090.

The refactor should reduce implicit/heuristic state to one explicit transport state
machine while retaining fail-closed acknowledgement and at most one bounded safe retry.
