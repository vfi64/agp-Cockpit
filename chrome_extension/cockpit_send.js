// AGP_SEND_MODULE_V1 (content.js split, module 3, owner 2026-10-07): the send transport — writing
// the prompt into ChatGPT's composer, the native (CDP) submit through the service worker, the
// commit nonce, the evidence that the user turn was committed, the bounded retry with the owned
// draft cleared, and the (disabled) degraded DOM path. content.js stays the controller: it keeps
// the pending transport that tick, stop and startAuto read and creates this module once
// (AGP_SEND.create) with its state and the services named below. The moved functions keep their
// content.js indentation, so the characterization tests that slice them by function still apply.
(() => {
  function create(host) {
    const STATE = host.state;
    const normalizeObservedMessageText = (...args) => host.normalizeObservedMessageText(...args);
    const composer = (...args) => host.composer(...args);
    const chatgptGenerationActive = (...args) => host.chatgptGenerationActive(...args);
    const clientEvent = (...args) => host.clientEvent(...args);
    const lastAssistantText = (...args) => host.lastAssistantText(...args);
    const sleep = (...args) => host.sleep(...args);
    const waitForComposer = (...args) => host.waitForComposer(...args);
    const reserveRemoteStep = (...args) => host.reserveRemoteStep(...args);
    const failureDomShape = (...args) => host.failureDomShape(...args);
    const sendButton = (...args) => host.sendButton(...args);
    const setPendingSendTransport = (...args) => host.setPendingSendTransport(...args);


  function setComposerText(el, text) {
    if (!el) throw new Error("ChatGPT composer not found");

    if (el instanceof HTMLTextAreaElement) {
      const setter = Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value"
      ).set;
      setter.call(el, text);
      el.dispatchEvent(new Event("input", {bubbles:true}));
      return;
    }

    el.focus();
    el.textContent = text;
    el.dispatchEvent(
      new InputEvent("input", {
        bubbles:true,
        inputType:"insertText",
        data:text
      })
    );
  }

  function visibleUserMessages() {
    return agpNativeMessageSnapshot(typeof agpResolveComposer === "function" ? agpResolveComposer : undefined).messages.map(message => message.text).filter(Boolean);
  }

  function normalizeRenderedUserTurnText(text) {
    return typeof agpNormalizeUserTurnText === "function"
      ? agpNormalizeUserTurnText(text)
      : normalizeObservedMessageText(text);
  }

  function renderedUserTurnMatches(observed, expected) {
    if (typeof agpRenderedUserTurnMatches === "function") {
      return agpRenderedUserTurnMatches(observed, expected);
    }
    const observedText = normalizeRenderedUserTurnText(observed);
    const expectedText = normalizeRenderedUserTurnText(expected);
    if (!observedText || !expectedText) return false;
    if (observedText === expectedText) return true;
    const minimumPrefix = 240;
    const collapsedText = observedText.replace(/\s*(?:…|\.{3})$/, "").trim();
    if (collapsedText.length >= minimumPrefix && expectedText.startsWith(collapsedText)) {
      return true;
    }
    return observedText.length >= minimumPrefix &&
      observedText.slice(0, minimumPrefix) === expectedText.slice(0, minimumPrefix);
  }


  // AGP_FOLLOWUP_SEND_TARGET_DECISIVE_ACK_066_D4
  // AGP_MULTI_SIGNAL_SEND_ACCEPTANCE_066_D3
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

  function isKnownCockpitDraft(text) {
    const value = normalizeObservedMessageText(text);
    return /^AGP-SEND-[0-9a-f]{16}(?:\s|$)/.test(value) ||
      value.includes("AGP COCKPIT MISSION — FIRST SINGLE STEP") ||
      value.includes("Attached is the result file for the command you gave me.") ||
      value.includes("The attached local execution evidence reports a FAILED command-file step.");
  }

  async function waitForSentUserMessage(
    prompt,
    beforeMessages,
    beforeAssistantText="",
    beforeComposerText="",
    beforeGenerationActive=false
  ) {
    const beforeCount = beforeMessages.length;
    const expected = normalizeRenderedUserTurnText(prompt);
    const assistantBefore = normalizeObservedMessageText(beforeAssistantText);
    const composerBefore = normalizeObservedMessageText(beforeComposerText);
    let provisionalComposerEvidence = "";
    let generationStartedObserved = false;

    // The nonce was generated for this send, so its pre-send occurrence count
    // outside the composer is zero by construction. Reconciliation may start
    // after the native commit already rendered, so it must not re-baseline.
    const commitMarker = commitMarkerOf(prompt);
    const markerBaseline = 0;
    let markerStreak = 0;

    for (let i = 0; i < 60; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));

      markerStreak = commitMarker && commitMarkerOutsideComposer(commitMarker) > markerBaseline
        ? markerStreak + 1
        : 0;
      if (markerStreak >= 2) {
        return {confirmed:true, via:"commit_marker"};
      }

      const after = visibleUserMessages();
      if (after.length > beforeCount) {
        const newest = after[after.length - 1];
        if (renderedUserTurnMatches(newest, expected)) {
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
      if (
        generationNow &&
        !beforeGenerationActive &&
        !generationStartedObserved
      ) {
        generationStartedObserved = true;
        await clientEvent("SEND_GENERATION_STARTED_OBSERVED", {
          authoritative_acceptance:false
        });
      }

      const assistantNow = normalizeObservedMessageText(lastAssistantText());
      if (assistantNow && assistantNow !== assistantBefore) {
        await clientEvent("SEND_ASSISTANT_ACTIVITY_OBSERVED", {
          authoritative_acceptance:false
        });
      }
    }

    return {
      confirmed:false,
      via:"timeout",
      provisional:provisionalComposerEvidence,
      generation_started_observed:generationStartedObserved
    };
  }

    // AGP_BROWSER_SENDER_TRANSPORT_STATE_MACHINE_092
  const SEND_TRANSPORT = Object.freeze({
    IDLE:"IDLE",
    DRAFT_WRITTEN:"DRAFT_WRITTEN",
    NATIVE_INPUT_REQUESTED:"NATIVE_INPUT_REQUESTED",
    NATIVE_SUBMIT_DISPATCHED:"NATIVE_SUBMIT_DISPATCHED",
    SUBMIT_ATTEMPTED:"SUBMIT_ATTEMPTED",
    WAITING_FOR_ACCEPTANCE:"WAITING_FOR_ACCEPTANCE",
    ACCEPTED:"ACCEPTED",
    ACCEPTED_LATE:"ACCEPTED_LATE",
    SAFE_RETRY_ELIGIBLE:"SAFE_RETRY_ELIGIBLE",
    RETRY_ATTEMPTED:"RETRY_ATTEMPTED",
    INDETERMINATE:"INDETERMINATE",
    FAILED_CONFIRMATION:"FAILED_CONFIRMATION"
  });
  const AGP_ALLOW_DEGRADED_DOM_FALLBACK = false;

  function createSendTransport(prompt) {
    return {
      state:SEND_TRANSPORT.IDLE,
      prompt,
      beforeAssistantText:"",
      retryCount:0,
      acknowledgement:null,
      transition(next, details={}) {
        this.state = next;
        STATE.lastEvent = `SEND_TRANSPORT_${next}`;
        clientEvent("SEND_TRANSPORT_STATE", {
          state:next,
          retry_count:this.retryCount,
          ...details
        }).catch(() => {});
      }
    };
  }


  // AGP_K07_SEND_COMMIT_NONCE_V1
  // Every native send carries a fresh, unguessable first line. A persistent
  // occurrence of that nonce outside the composer after the send boundary is
  // decisive commit evidence that does not depend on ChatGPT's user-turn
  // wrappers, message ids, rendered Markdown projection, virtualization
  // window, or conversation URL.
  const AGP_COMMIT_MARKER_PATTERN = /^AGP-SEND-[0-9a-f]{16}$/;

  function agpCommitMarker() {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return "AGP-SEND-" + Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function commitMarkerOf(prompt) {
    const firstLine = String(prompt || "").split("\n", 1)[0].trim();
    return AGP_COMMIT_MARKER_PATTERN.test(firstLine) ? firstLine : "";
  }

  function commitMarkerOutsideComposer(marker) {
    if (!marker) return 0;
    const count = value => String(value || "").split(marker).length - 1;
    const el = composer();
    const inBody = el && !(el instanceof HTMLTextAreaElement)
      ? count(el.innerText || el.textContent || "")
      : 0;
    const bodyText = document.body ? (document.body.innerText || document.body.textContent || "") : "";
    return Math.max(0, count(bodyText) - inBody);
  }

  // AGP_NATIVE_RETRY_OWNED_DRAFT_V1
  // Live 2026-10-05: attempt 1 inserted the prompt but the editor model was not
  // verified; attempt 2 then refused because the composer was not empty, so the
  // bounded retry could never succeed and the real cause was masked. Before a
  // retry, clear exactly this send's own draft (fresh AGP-SEND nonce or the
  // exact prompt). Any other content stays protected: fail closed.
  async function clearOwnedDraftBeforeRetry(prompt, commitMarker, attempt) {
    const staged = normalizeObservedMessageText(observedComposerText());
    if (!staged) return;
    const expected = normalizeObservedMessageText(prompt);
    const marker = String(commitMarker || "");
    const owned = staged === expected ||
      (AGP_COMMIT_MARKER_PATTERN.test(marker) &&
        (staged === marker || staged.startsWith(marker + " ")));
    if (!owned) {
      throw new Error(
        "browser-native retry found foreign composer content; refusing to overwrite"
      );
    }
    const el = composer();
    if (!el) throw new Error("browser-native retry composer disappeared");
    setComposerText(el, "");
    const deadline = Date.now() + 2000;
    while (normalizeObservedMessageText(observedComposerText()) && Date.now() < deadline) {
      await sleep(50);
    }
    if (normalizeObservedMessageText(observedComposerText())) {
      throw new Error("browser-native retry could not clear its own draft");
    }
    await clientEvent("NATIVE_RETRY_OWNED_DRAFT_CLEARED", {
      attempt,
      chars:staged.length
    });
  }

  async function sendPromptNative(prompt) {
    const commitMarker = agpCommitMarker();
    prompt = `${commitMarker}\n${String(prompt || "")}`;
    const transport = createSendTransport(prompt);

    const nativeTransport = window.AGPBrowserNativeTransport;
    if (
      !nativeTransport ||
      typeof nativeTransport.available !== "function" ||
      typeof nativeTransport.submit !== "function" ||
      !nativeTransport.available()
    ) {
      throw new Error("browser-native transport unavailable");
    }

    const beforeMessages = visibleUserMessages();
    const beforeAssistantText = lastAssistantText();
    transport.beforeAssistantText = beforeAssistantText;

    await waitForComposer();

    const stagedComposerText = normalizeObservedMessageText(
      observedComposerText()
    );
    const expectedPromptText = normalizeObservedMessageText(prompt);

    if (stagedComposerText) {
      if (stagedComposerText !== expectedPromptText) {
        if (!isKnownCockpitDraft(stagedComposerText)) {
          throw new Error(
            "browser-native transport found non-empty foreign composer content; refusing to overwrite"
          );
        }
        setComposerText(composer(), "");
        await clientEvent("NATIVE_STALE_OWNED_COMPOSER_RECOVERED", {
          chars:stagedComposerText.length,
          ownership:"known_cockpit_prompt_after_reload"
        });
      }

      const staleOwnedComposer = composer();
      if (!staleOwnedComposer) {
        throw new Error(
          "browser-native transport stale-owned composer disappeared during recovery"
        );
      }

      setComposerText(staleOwnedComposer, "");

      const cleanupDeadline = Date.now() + 2000;
      while (
        normalizeObservedMessageText(observedComposerText()) &&
        Date.now() < cleanupDeadline
      ) {
        await sleep(50);
      }

      if (normalizeObservedMessageText(observedComposerText())) {
        throw new Error(
          "browser-native transport could not clear exact stale Cockpit-owned draft"
        );
      }

      await clientEvent("NATIVE_STALE_OWNED_COMPOSER_RECOVERED", {
        chars:prompt.length,
        ownership:"exact_current_prompt"
      });
    }

    const beforeGenerationActive = chatgptGenerationActive();
    STATE.lastPrompt = prompt;
    setPendingSendTransport(transport);

    transport.transition(SEND_TRANSPORT.NATIVE_INPUT_REQUESTED, {
      chars:prompt.length
    });
    await clientEvent("NATIVE_TRANSPORT_REQUESTED", {
      chars:prompt.length
    });

    let nativeAck = null;
    for (let attempt = 1; attempt <= 2; attempt += 1) {
      if (attempt > 1) await clearOwnedDraftBeforeRetry(prompt, commitMarker, attempt);
      nativeAck = await nativeTransport.submit(prompt, {attempt, commitMarker});
      if (String(nativeAck.stage || "") !== "COMPOSER_MODEL_NOT_VERIFIED") break;
      await clientEvent("COMPOSER_MODEL_NOT_VERIFIED", {
        attempt,
        model: nativeAck.model || null
      });
      if (attempt < 2) await sleep(250);
    }

    transport.transition(SEND_TRANSPORT.NATIVE_SUBMIT_DISPATCHED, {
      request_id:String(nativeAck.request_id || ""),
      tab_id:Number(nativeAck.tab_id || 0),
      native_stage:String(nativeAck.stage || "")
    });
    await clientEvent("NATIVE_TRANSPORT_SUBMIT_DISPATCHED", {
      request_id:String(nativeAck.request_id || ""),
      tab_id:Number(nativeAck.tab_id || 0),
      native_stage:String(nativeAck.stage || "")
    });

    if (String(nativeAck.stage || "") === "COMPOSER_MODEL_NOT_VERIFIED") {
      const error = new Error("COMPOSER_MODEL_NOT_VERIFIED after bounded refocus retry");
      error.code = "COMPOSER_MODEL_NOT_VERIFIED";
      await clientEvent("COMPOSER_MODEL_RECOVERY_EXHAUSTED", {
        attempts:2,
        model:nativeAck.model || null
      });
      throw error;
    }

    if (String(nativeAck.stage || "") === "USER_TURN_INDETERMINATE") {
      transport.acknowledgement = {
        confirmed:false,
        via:"native_indeterminate"
      };
      transport.transition(SEND_TRANSPORT.INDETERMINATE, {
        request_id:String(nativeAck.request_id || ""),
        native_stage:"USER_TURN_INDETERMINATE",
        via:"native_transport",
        attempts:Array.isArray(nativeAck.submit_attempts)
          ? nativeAck.submit_attempts.length
          : 0
      });
      const reconciliation = await waitForSentUserMessage(
        prompt,
        beforeMessages,
        beforeAssistantText,
        observedComposerText(),
        beforeGenerationActive
      );
      if (reconciliation.confirmed) {
        setPendingSendTransport(null);
        transport.acknowledgement = reconciliation;
        transport.transition(SEND_TRANSPORT.ACCEPTED_LATE, {
          via:"reconciliation",
          native_stage:"USER_TURN_INDETERMINATE"
        });
        await clientEvent("ACCEPTED_LATE", {via:"reconciliation", evidence:reconciliation.via || ""});
        return;
      }
      // An empty composer is composer mutation, not send acceptance
      // (COMMUNICATION_PROTOCOL.md). Without decisive commit evidence the
      // send stays indeterminate and fails closed.
      const reservedStep = Number(STATE.nextLocalStep || 0);
      if (reservedStep > 0) {
        try {
          await reserveRemoteStep("native-send-indeterminate", reservedStep);
        } catch (reserveError) {
          await clientEvent("K07_REMOTE_STEP_RESERVE_FAILED", {
            step:reservedStep,
            error:String(reserveError && reserveError.message ? reserveError.message : reserveError)
          });
        }
      }
      await clientEvent("SEND_INDETERMINATE", {
        dom_shape:typeof failureDomShape === "function" ? failureDomShape() : null,   // AGP_DOM_SHAPE_SNAPSHOT_V1
        reconciliation:"not_confirmed",
        commit_marker_outside_composer:commitMarkerOutsideComposer(commitMarker),
        native_diagnostics:nativeAck.diagnostics || null,
        provisional:reconciliation.provisional || "",
        generation_started_observed:Boolean(reconciliation.generation_started_observed),
        native_after_summary:nativeAck.after && {
          user_message_count:Number(nativeAck.after.user_message_count || 0),
          exact_user_message_found:Boolean(nativeAck.after.exact_user_message_found),
          composer_chars:String(nativeAck.after.composer_text || "").length,
          generation_active:Boolean(nativeAck.after.generation_active)
        }
      });
      STATE.lastEvent = "SEND_INDETERMINATE";
      STATE.note = "Prompt nicht reconcilierbar bestätigt; kein weiterer Turn";
      throw new Error("SEND_INDETERMINATE: user turn not reconciled");
    }

    if (String(nativeAck.stage || "") !== "USER_TURN_COMMITTED") {
      throw new Error(
        `native transport returned non-committed stage: ${String(nativeAck.stage || "")}`
      );
    }

    const acknowledgement = {
      confirmed:true,
      via:"user_message",
      native_stage:"USER_TURN_COMMITTED"
    };

    transport.acknowledgement = acknowledgement;
    transport.transition(SEND_TRANSPORT.ACCEPTED, {
      via:"user_message",
      request_id:String(nativeAck.request_id || ""),
      native_stage:"USER_TURN_COMMITTED"
    });
    setPendingSendTransport(null);
    STATE.lastEvent = "PROMPT_SENT";
    STATE.note = "Prompt bestätigt via persistentem User-Turn";
    await clientEvent("NATIVE_USER_TURN_COMMITTED", {
      request_id:String(nativeAck.request_id || ""),
      via:"user_message",
      native_stage:"USER_TURN_COMMITTED"
    });
    await clientEvent("NATIVE_SEND_ACCEPTED", {
      request_id:String(nativeAck.request_id || ""),
      via:"user_message"
    });
  }

  async function sendPrompt(prompt) {
    let failure = null;
    try {
      return await sendPromptNative(prompt);
    } catch (error) {
      failure = error;
    }
    // AGP_SEND_NOT_READY_RETRY_V1 (live 2026-10-02, twice at "Arbeit
    // beginnen"): nothing was sent; log what the composer offered, clear our
    // own text (attachments of this send stay) and try once more after 15 s.
    const rejected = failure && failure.response;
    if (rejected && rejected.stage === "SEND_BUTTON_NOT_READY") {
      await clientEvent("SEND_BUTTON_NOT_READY_DIAGNOSED", {
        form_buttons:Array.isArray(rejected.form_buttons) ? rejected.form_buttons : [],
        send_diagnostics:Array.isArray(rejected.send_diagnostics) ? rejected.send_diagnostics.slice(0, 8) : [],
        readiness_wait_ms:Number(rejected.readiness_wait_ms || 0)
      });
      let cleaned = null;
      try {
        cleaned = await chrome.runtime.sendMessage({type:"AGP_K07_CLEAN_COMPOSER", files:false});
      } catch (_) {
        cleaned = null;
      }
      if (cleaned && cleaned.ok === true) {
        await sleep(15000);
        await clientEvent("SEND_RETRY_AFTER_NOT_READY", {clean_stage:String(cleaned.stage || "")});
        try {
          return await sendPromptNative(prompt);
        } catch (error) {
          failure = error;
        }
      }
    }
    return await sendPromptFailed(failure, prompt);
  }

  async function sendPromptFailed(error, prompt) {
    {
      if (error && error.code === "COMPOSER_MODEL_NOT_VERIFIED") {
        STATE.lastTransportFailureClass = "COMPOSER_MODEL_NOT_VERIFIED";
        await clientEvent("COMPOSER_MODEL_RECOVERY_EXHAUSTED", {
          message:String(error.message || error)
        });
      }
      await clientEvent("NATIVE_TRANSPORT_FAILED", {
        message:String(error && error.message ? error.message : error),
        failure_class:STATE.lastTransportFailureClass || ""
      });

      if (!AGP_ALLOW_DEGRADED_DOM_FALLBACK) {
        throw error;
      }

      await clientEvent("DOM_TRANSPORT_DEGRADED_FALLBACK", {
        explicit_degraded_mode:true
      });
      return await sendPromptDomDegraded(prompt);
    }
  }

  // AGP_SEND_OUTCOME_FIRST_V1: the submit paths without a usable send button.
  function submitComposerWithoutButton(composerEl) {
    const el = composerEl || composer();
    if (!el) return "";
    const form = el.closest ? el.closest("form") : null;
    if (form && typeof form.requestSubmit === "function") {
      form.requestSubmit();
      return "form";
    }
    el.focus();
    for (const type of ["keydown", "keyup"]) {
      el.dispatchEvent(new KeyboardEvent(type, {
        key:"Enter", code:"Enter", keyCode:13, which:13, bubbles:true, cancelable:true
      }));
    }
    return "enter";
  }

  async function sendPromptDomDegraded(prompt) {
    const transport = createSendTransport(prompt);

    const beforeMessages = visibleUserMessages();
    const beforeAssistantText = lastAssistantText();
    transport.beforeAssistantText = beforeAssistantText;
    const composerEl = await waitForComposer();
    STATE.lastPrompt = prompt;
    setComposerText(composerEl, prompt);
    transport.transition(SEND_TRANSPORT.DRAFT_WRITTEN, {chars:prompt.length});
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

    setPendingSendTransport(transport);
    transport.transition(SEND_TRANSPORT.SUBMIT_ATTEMPTED, {attempt:1});
    transport.transition(SEND_TRANSPORT.WAITING_FOR_ACCEPTANCE, {attempt:1});
    let acknowledgement = await waitForSentUserMessage(
      prompt,
      beforeMessages,
      beforeAssistantText,
      beforeComposerText,
      beforeGenerationActive
    );

    // AGP_LATE_ACCEPTANCE_BOUNDARY_097
    // Timeout is epistemic uncertainty, not proof that ChatGPT rejected the send.
    // Retry remains bounded and requires positive evidence that the exact prompt
    // is still present and no generation has begun.
    if (!acknowledgement.confirmed) {
      const pendingComposer = observedComposerText();
      const expectedPrompt = normalizeObservedMessageText(prompt);
      const safeToRetry = (
        pendingComposer === expectedPrompt &&
        !chatgptGenerationActive()
      );

      if (safeToRetry) {
        transport.transition(SEND_TRANSPORT.SAFE_RETRY_ELIGIBLE, {
          via:acknowledgement.via || "unknown"
        });
        await clientEvent("SEND_RETRY_SAFE_PENDING_COMPOSER", {
          chars:prompt.length,
          first_via:acknowledgement.via || "",
          provisional:acknowledgement.provisional || ""
        });

        const retryComposer = composer();
        const retryButton = sendButton(retryComposer);
        // AGP_SEND_OUTCOME_FIRST_V1 (DOM hardening step 1): the retry no longer needs the
        // send button either; like the first attempt it falls back to the form submit or
        // Enter. Only the committed user turn (waitForSentUserMessage) counts as sent.
        let retryVia = "";
        if (retryButton && !retryButton.disabled) {
          retryButton.click();
          retryVia = "button";
        } else {
          retryVia = submitComposerWithoutButton(retryComposer);
        }
        if (retryVia) {
          await clientEvent("SEND_RETRY_SUBMITTED", {via:retryVia});
          transport.retryCount += 1;
          transport.transition(SEND_TRANSPORT.RETRY_ATTEMPTED, {attempt:2});
          transport.transition(SEND_TRANSPORT.WAITING_FOR_ACCEPTANCE, {attempt:2});
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
      const expectedPrompt = normalizeObservedMessageText(prompt);
      const positiveUnsentEvidence = (
        observedComposerText() === expectedPrompt &&
        !chatgptGenerationActive()
      );

      if (positiveUnsentEvidence && transport.retryCount > 0) {
        transport.transition(SEND_TRANSPORT.FAILED_CONFIRMATION, {
          via:acknowledgement.via || "timeout",
          positive_unsent_evidence:true
        });
        setPendingSendTransport(null);
        STATE.lastEvent = "SEND_UNCONFIRMED";
        throw new Error(
          "SEND_UNCONFIRMED: positive evidence shows the prompt is still unsent"
        );
      }

      transport.acknowledgement = acknowledgement;
      transport.transition(SEND_TRANSPORT.INDETERMINATE, {
        via:acknowledgement.via || "timeout",
        attempts:transport.retryCount + 1,
        generation_started_observed:Boolean(
          acknowledgement.generation_started_observed
        )
      });
      STATE.lastEvent = "SEND_INDETERMINATE";
      STATE.note = "Prompt gesendet; Bestätigung noch unbestimmt";
      return;
    }

    transport.acknowledgement = acknowledgement;
    transport.transition(SEND_TRANSPORT.ACCEPTED, {
      via:acknowledgement.via || "unknown",
      attempts:transport.retryCount + 1
    });
    setPendingSendTransport(null);
    STATE.lastEvent = "PROMPT_SENT";
    STATE.note = `Prompt bestätigt via ${acknowledgement.via}`;
  }

    return Object.freeze({
      SEND_TRANSPORT,
      AGP_ALLOW_DEGRADED_DOM_FALLBACK,
      AGP_COMMIT_MARKER_PATTERN,
      setComposerText,
      visibleUserMessages,
      normalizeRenderedUserTurnText,
      renderedUserTurnMatches,
      observedComposerText,
      isKnownCockpitDraft,
      waitForSentUserMessage,
      createSendTransport,
      agpCommitMarker,
      commitMarkerOf,
      commitMarkerOutsideComposer,
      clearOwnedDraftBeforeRetry,
      sendPromptNative,
      sendPrompt,
      sendPromptFailed,
      submitComposerWithoutButton,
      sendPromptDomDegraded,
    });
  }

  globalThis.AGP_SEND = Object.freeze({create});
})();
