importScripts("result_file_attachment.js");
importScripts("native_message_evidence.js");

const ALARM_NAME = "agp-browser-refresh-tabs";
const LAST_HANDLED = "agpLastHandledRefreshGeneration";
const PENDING = "agpPendingRefreshTabs";

async function performRefresh(generation) {
  const state = await chrome.storage.local.get([LAST_HANDLED]);
  const handled = Number(state[LAST_HANDLED] || 0);

  if (!Number.isFinite(generation) || generation <= handled) {
    return {accepted:false, reason:"already-handled"};
  }

  const tabs = await chrome.tabs.query({
    url:[
      "https://chatgpt.com/*",
      "https://www.chatgpt.com/*"
    ]
  });

  const tabIds = tabs
    .map(tab => tab.id)
    .filter(id => Number.isInteger(id));

  await chrome.storage.local.set({
    [LAST_HANDLED]:generation,
    [PENDING]:{generation, tabIds}
  });

  chrome.alarms.create(
    ALARM_NAME,
    {when:Date.now() + 1500}
  );

  setTimeout(() => {
    chrome.runtime.reload();
  }, 100);

  return {
    accepted:true,
    generation,
    tabCount:tabIds.length
  };
}

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (!message || message.type !== "AGP_REFRESH_INTEGRATION") {
      return false;
    }

    performRefresh(Number(message.generation || 0))
      .then(sendResponse)
      .catch(error => {
        sendResponse({
          accepted:false,
          error:String(error)
        });
      });

    return true;
  }
);

chrome.alarms.onAlarm.addListener(async alarm => {
  if (alarm.name !== ALARM_NAME) {
    return;
  }

  const state = await chrome.storage.local.get([PENDING]);
  const pending = state[PENDING];

  if (!pending || !Array.isArray(pending.tabIds)) {
    return;
  }

  for (const tabId of pending.tabIds) {
    try {
      await chrome.tabs.reload(tabId);
    } catch (_) {}
  }

  await chrome.storage.local.remove(PENDING);
});


async function agpK07NativeTrace1165(payload) {
  try { await chrome.runtime.sendMessage({type:"AGP_K07_NATIVE_TRACE_1165", payload}); } catch (_) {}
}

// AGP_BROWSER_NATIVE_TRANSPORT_V1
async function agpNativeTransportV1(message, sender) {
  const requestId = String(message.request_id || "");
  const text = String(message.text || "");
  const operation = String(message.operation || "");
  const tabId = sender && sender.tab ? sender.tab.id : null;

  if (!requestId || !text || operation !== "insert_and_submit") {
    throw new Error("invalid native transport request");
  }
  if (!Number.isInteger(tabId)) {
    throw new Error("native transport requires sender.tab.id");
  }

  const target = {tabId};
  let attached = false;

  const evaluate = async expression => {
    const result = await chrome.debugger.sendCommand(
      target,
      "Runtime.evaluate",
      {
        expression,
        returnByValue:true,
        awaitPromise:true
      }
    );
    if (result && result.exceptionDetails) {
      throw new Error("CDP Runtime.evaluate failed");
    }
    return result && result.result ? result.result.value : null;
  };

  const normalize = value => String(value || "")
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  try {
    await chrome.debugger.attach(target, "1.3");
    attached = true;

    await chrome.debugger.sendCommand(target, "Runtime.enable");

    const observeMessages = () => evaluate(`(${agpNativeMessageSnapshot.toString()})()`);
    const beforeMessages = await observeMessages();

    const before = await evaluate(`(() => {
      const el = document.activeElement;
      return {
        url: location.href,
        tag: el ? el.tagName : "",
        id: el ? el.id : "",
        role: el ? el.getAttribute("role") : "",
        contenteditable: el ? el.getAttribute("contenteditable") : "",
        value: el && "value" in el ? String(el.value || "") : "",
        text: el ? String(el.innerText || el.textContent || "") : ""
      };
    })()`);

    await chrome.debugger.sendCommand(
      target,
      "Input.insertText",
      {text}
    );

    const inserted = await evaluate(`(() => {
      const active = document.activeElement;
      const composer = document.querySelector('#prompt-textarea') ||
        document.querySelector('[contenteditable="true"][role="textbox"]');
      const el = composer || active;
      const value = el && "value" in el
        ? String(el.value || "")
        : String((el && (el.innerText || el.textContent)) || "");
      return {
        url: location.href,
        value,
        tag: el ? el.tagName : "",
        id: el ? el.id : "",
        contenteditable: el ? el.getAttribute("contenteditable") : "",
        source: composer ? "composer" : "activeElement",
        active_tag: active ? active.tagName : "",
        active_id: active ? active.id : ""
      };
    })()`);

    if (normalize(inserted && inserted.value) !== normalize(text)) {
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:"INSERT_NOT_VERIFIED",
        before,
        inserted
      };
    }

    // 825 proved insertion succeeds while the prior submit path did not commit.
    // React may publish/enable the send control shortly after Input.insertText.
    // Wait boundedly for a truly actionable target instead of sampling once.
    let sendTarget = null;
    let sendDiagnostics = null;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const probe = await evaluate(`(() => {
        const selectors = [
          'button[data-testid="send-button"]',
          'button[aria-label*="Send"]',
          'button[aria-label*="Senden"]',
          'form button[type="submit"]'
        ];
        const diagnostics = [];
        for (const selector of selectors) {
          const nodes = Array.from(document.querySelectorAll(selector));
          for (const button of nodes) {
            const r = button.getBoundingClientRect();
            const style = getComputedStyle(button);
            const x = r.left + r.width / 2;
            const y = r.top + r.height / 2;
            const hit = (r.width > 0 && r.height > 0)
              ? document.elementFromPoint(x, y)
              : null;
            const hitMatches = Boolean(hit && (hit === button || button.contains(hit)));
            const record = {
              selector,
              disabled:Boolean(button.disabled),
              aria_disabled:String(button.getAttribute("aria-disabled") || ""),
              visible:Boolean(
                r.width > 0 &&
                r.height > 0 &&
                style.visibility !== "hidden" &&
                style.display !== "none"
              ),
              pointer_events:String(style.pointerEvents || ""),
              hit_matches:hitMatches,
              x, y,
              tag:String(button.tagName || ""),
              type:String(button.getAttribute("type") || ""),
              aria_label:String(button.getAttribute("aria-label") || ""),
              testid:String(button.getAttribute("data-testid") || ""),
              hit_tag:String(hit ? hit.tagName : ""),
              hit_testid:String(hit ? (hit.getAttribute("data-testid") || "") : "")
            };
            diagnostics.push(record);
            if (
              !record.disabled &&
              record.aria_disabled !== "true" &&
              record.visible &&
              record.pointer_events !== "none" &&
              record.hit_matches
            ) {
              return {found:true,target:record,diagnostics};
            }
          }
        }
        return {found:false,diagnostics};
      })()`);

      sendDiagnostics = probe && probe.diagnostics ? probe.diagnostics : [];
      if (probe && probe.found === true && probe.target) {
        sendTarget = probe.target;
        sendTarget.readiness_attempt = attempt + 1;
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    if (!sendTarget) {
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:"SEND_BUTTON_NOT_READY",
        before,
        inserted,
        send_target:null,
        send_diagnostics:sendDiagnostics,
        readiness_wait_ms:3000
      };
    }

    void agpK07NativeTrace1165({event:"PRIMARY_ENTER_BEFORE",request_id:requestId,send_target:sendTarget,inserted:inserted});
    await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
      type:"keyDown",
      key:"Enter",
      code:"Enter",
      text:"\r",
      unmodifiedText:"\r",
      windowsVirtualKeyCode:13,
      nativeVirtualKeyCode:13
    });
    await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
      type:"keyUp",
      key:"Enter",
      code:"Enter",
      windowsVirtualKeyCode:13,
      nativeVirtualKeyCode:13
    });

    let commitEvidence = null;
    let lastObserved = null;
    const previousIds = new Set(beforeMessages.messages.map(message => message.id).filter(Boolean));
    for (let i = 0; i < 40; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));
      const observed = await observeMessages();
      const exactIndex = observed.url === beforeMessages.url
        ? observed.messages.findIndex((message, index) =>
          message.text === normalize(text) &&
          (message.id ? !previousIds.has(message.id) : index >= beforeMessages.messages.length))
        : -1;
      observed.exact_user_message_index = exactIndex;
      observed.exact_user_message_found = exactIndex >= 0;
      lastObserved = observed;
      if (observed.exact_user_message_found) {
        commitEvidence = observed;
        break;
      }
    }

    if (!commitEvidence) {
      // A missing acknowledgement is not proof that a side effect did not occur.
      // AGP_K07_TRUSTED_ENTER_COMMIT_RETRY_928
      // Retry the same trusted CDP Enter primitive once, but only when exact evidence
      // says the first attempt left the exact payload untouched and generation inactive.
      let clearlyUnsent = lastObserved &&
        lastObserved.url === beforeMessages.url &&
        lastObserved.composer_text === normalize(text) &&
        !lastObserved.generation_active;
      if (clearlyUnsent) {
        void agpK07NativeTrace1165({event:"RETRY_ENTER_BEFORE",request_id:requestId,last_observed:lastObserved});
        await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
          type:"keyDown", key:"Enter", code:"Enter", text:"\r", unmodifiedText:"\r",
          windowsVirtualKeyCode:13, nativeVirtualKeyCode:13
        });
        await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
          type:"keyUp", key:"Enter", code:"Enter",
          windowsVirtualKeyCode:13, nativeVirtualKeyCode:13
        });
        for (let i = 0; i < 20; i += 1) {
          await new Promise(resolve => setTimeout(resolve, 250));
          const observed = await observeMessages();
          const exactIndex = observed.url === beforeMessages.url
            ? observed.messages.findIndex((message, index) =>
              message.text === normalize(text) &&
              (message.id ? !previousIds.has(message.id) : index >= beforeMessages.messages.length))
            : -1;
          observed.exact_user_message_index = exactIndex;
          observed.exact_user_message_found = exactIndex >= 0;
          lastObserved = observed;
          if (observed.exact_user_message_found) { commitEvidence = observed; break; }
        }
        if (commitEvidence) {
          return {ok:true,request_id:requestId,tab_id:tabId,stage:"USER_TURN_COMMITTED",
            before,inserted,commit:commitEvidence,commit_retry:"trusted_enter_once"};
        }
      }
      void agpK07NativeTrace1165({event:"COMMIT_FAILURE",request_id:requestId,clearly_unsent:Boolean(clearlyUnsent),before_messages:beforeMessages,send_target:sendTarget,last_observed:lastObserved});
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:clearlyUnsent ? "USER_TURN_NOT_COMMITTED" : "USER_TURN_INDETERMINATE",
        before,
        inserted,
        send_target:sendTarget,
        after:lastObserved
      };
    }

    return {
      ok:true,
      request_id:requestId,
      tab_id:tabId,
      stage:"USER_TURN_COMMITTED",
      before,
      inserted,
      commit:commitEvidence
    };
  } finally {
    if (attached) {
      try {
        await chrome.debugger.detach(target);
      } catch (_) {}
    }
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "AGP_BROWSER_NATIVE_TRANSPORT_V1") {
    return false;
  }

  agpNativeTransportV1(message, sender)
    .then(result => sendResponse(result))
    .catch(error => sendResponse({
      ok:false,
      request_id:String(message.request_id || ""),
      stage:"NATIVE_TRANSPORT_EXCEPTION",
      error:String(error && error.message ? error.message : error)
    }));

  return true;
});


// AGP_K07_COMMAND_FILE_FETCH_989
async function agpFetchAssistantCommandFile(message, sender) {
  const href = String(message.href || "").trim();
  const filename = String(message.filename || "").trim();
  const tabId = sender && sender.tab ? sender.tab.id : null;

  if (!href || !filename || !/\.py$/i.test(filename)) {
    throw new Error("K07 command-file fetch requires one .py attachment");
  }
  if (!Number.isInteger(tabId)) {
    throw new Error("K07 command-file fetch requires sender.tab.id");
  }

  const target = {tabId};
  let attached = false;
  try {
    await chrome.debugger.attach(target, "1.3");
    attached = true;
    await chrome.debugger.sendCommand(target, "Runtime.enable");

    const expression = `(async () => {
      const href = ${JSON.stringify(href)};
      const response = await fetch(href, {credentials:"include"});
      if (!response.ok) throw new Error("attachment fetch HTTP " + response.status);
      const text = await response.text();
      return {
        href,
        text,
        content_type:String(response.headers.get("content-type") || ""),
        chars:text.length
      };
    })()`;

    const evaluated = await chrome.debugger.sendCommand(
      target,
      "Runtime.evaluate",
      {expression, returnByValue:true, awaitPromise:true}
    );
    if (evaluated && evaluated.exceptionDetails) {
      throw new Error("K07 attachment fetch failed in page context");
    }
    const value = evaluated && evaluated.result ? evaluated.result.value : null;
    if (!value || typeof value.text !== "string") {
      throw new Error("K07 attachment fetch returned no text");
    }
    if (value.text.length < 1 || value.text.length > 2000000) {
      throw new Error("K07 command file size outside bounded range");
    }
    return {
      ok:true,
      stage:"COMMAND_FILE_FETCHED",
      filename,
      href,
      content:value.text,
      content_type:String(value.content_type || ""),
      chars:Number(value.chars || value.text.length)
    };
  } finally {
    if (attached) {
      try { await chrome.debugger.detach(target); } catch (_) {}
    }
  }
}

// AGP_K07_RESULT_CONTINUATION_MESSAGE_991
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "AGP_K07_RESULT_CONTINUATION") return false;
  const tabId = sender && sender.tab ? sender.tab.id : null;
  const absolutePath = String(message.result_file || "").trim();
  if (!Number.isInteger(tabId) || !absolutePath.startsWith("/")) {
    sendResponse({ok:false, stage:"RESULT_CONTINUATION_REJECTED"});
    return false;
  }
  agpSubmitFileLoopContinuation(tabId, absolutePath)
    .then(sendResponse)
    .catch(error => sendResponse({ok:false, stage:"RESULT_CONTINUATION_FAILED", error:String(error && error.message ? error.message : error)}));
  return true;
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "AGP_K07_COMMAND_FILE_FETCH") return false;
  agpFetchAssistantCommandFile(message, sender)
    .then(sendResponse)
    .catch(error => sendResponse({
      ok:false,
      stage:"COMMAND_FILE_FETCH_FAILED",
      error:String(error && error.message ? error.message : error)
    }));
  return true;
});

// K07_FILE_LOOP_RESULT_ATTACHMENT_WIRING
async function agpAttachFileLoopResultBundle(tabId, absolutePath) {
  if (!globalThis.AGPResultFileAttachment) throw new Error("K07 result-file attachment seam unavailable");
  const attached = await globalThis.AGPResultFileAttachment.attachResultFile(chrome, {tabId}, absolutePath);
  if (!attached || attached.stage !== "RESULT_FILE_ATTACHED") throw new Error("K07 result-file attachment was not confirmed");
  return attached;
}
async function agpSubmitFileLoopContinuation(tabId, absolutePath) {
  await agpAttachFileLoopResultBundle(tabId, absolutePath);
  const continuation = "Attached is the result file for the command you gave me. Evaluate it and continue the current task. If more local work is required, return the next command file; otherwise finish or request human input.";
  if (typeof sendPromptToChatGPT !== "function") throw new Error("ChatGPT prompt transport unavailable");
  await sendPromptToChatGPT(tabId, continuation);
  return {ok:true, stage:"RESULT_ATTACHED_AND_CONTINUATION_SENT", file_path:absolutePath, cycle_id:message.cycle_id || null, result_sha256:message.result_sha256 || null, trace_events:[{event:"BROWSER_RESULT_ATTACHED",cycle_id:message.cycle_id || null,result_sha256:message.result_sha256 || null},{event:"CONTINUATION_SENT",cycle_id:message.cycle_id || null,result_sha256:message.result_sha256 || null}]};
}
