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
      const el = document.activeElement;
      const value = el && "value" in el
        ? String(el.value || "")
        : String((el && (el.innerText || el.textContent)) || "");
      return {
        url: location.href,
        value,
        tag: el ? el.tagName : "",
        id: el ? el.id : "",
        contenteditable: el ? el.getAttribute("contenteditable") : ""
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

    // 850 real discriminator A: preserve proven insertion; replace submit only.
    // 850 discriminator A proved the inserted prompt is sendable with a
    // physical Enter key. Preserve insertion and change only the automated submit
    // event shape to a CDP keyDown/keyUp Enter sequence with text metadata.
    await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
      type:"keyDown",
      key:"Enter",
      code:"Enter",
      text:"\\r",
      unmodifiedText:"\\r",
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

    const escapedPrompt = JSON.stringify(text);

    let commitEvidence = null;
    for (let i = 0; i < 40; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));

      const observed = await evaluate(`(() => {
        const norm = value => String(value || "")
          .replace(/\u00a0/g, " ")
          .replace(/\s+/g, " ")
          .trim();

        const expected = norm(${escapedPrompt});
        const selectors = [
          '[data-message-author-role="user"]',
          'article [data-message-author-role="user"]',
          '[data-testid^="conversation-turn-"] [data-message-author-role="user"]'
        ];

        const nodes = [];
        const seen = new Set();
        for (const selector of selectors) {
          for (const node of document.querySelectorAll(selector)) {
            if (seen.has(node)) continue;
            seen.add(node);
            nodes.push(node);
          }
        }

        const messages = nodes.map(node => norm(node.innerText || node.textContent || ""));
        const exactIndex = messages.findIndex(message => message === expected);

        const composer = document.querySelector(
          '#prompt-textarea, textarea[data-id="root"], form [contenteditable="true"]'
        );
        const composerText = composer
          ? norm("value" in composer ? composer.value : (composer.innerText || composer.textContent || ""))
          : "";

        return {
          url: location.href,
          user_message_count: messages.length,
          exact_user_message_index: exactIndex,
          exact_user_message_found: exactIndex >= 0,
          latest_user_message: messages.length ? messages[messages.length - 1] : "",
          composer_text: composerText
        };
      })()`);

      if (observed && observed.exact_user_message_found === true) {
        commitEvidence = observed;
        break;
      }
    }

    if (!commitEvidence) {
      const afterTimeout = await evaluate(`(() => {
        const norm = value => String(value || "")
          .replace(/\u00a0/g, " ")
          .replace(/\s+/g, " ")
          .trim();
        const nodes = Array.from(document.querySelectorAll('[data-message-author-role="user"]'));
        const messages = nodes.map(node => norm(node.innerText || node.textContent || ""));
        const composer = document.querySelector(
          '#prompt-textarea, textarea[data-id="root"], form [contenteditable="true"]'
        );
        return {
          url: location.href,
          user_message_count: messages.length,
          latest_user_message: messages.length ? messages[messages.length - 1] : "",
          composer_text: composer
            ? norm("value" in composer ? composer.value : (composer.innerText || composer.textContent || ""))
            : ""
        };
      })()`);

      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:"USER_TURN_NOT_COMMITTED",
        before,
        inserted,
        send_target:sendTarget,
        post_click:await evaluate(`(() => {
          const composer = document.querySelector("#prompt-textarea");
          const button = document.querySelector('button[data-testid="send-button"]')
            || document.querySelector('form button[type="submit"]');
          const r = button ? button.getBoundingClientRect() : null;
          const x = r ? r.left + r.width / 2 : null;
          const y = r ? r.top + r.height / 2 : null;
          const hit = (x !== null && y !== null) ? document.elementFromPoint(x, y) : null;
          return {
            composer_text:String(composer ? (composer.innerText || composer.textContent || "") : ""),
            button_present:Boolean(button),
            button_disabled:Boolean(button && button.disabled),
            button_aria_disabled:String(button ? (button.getAttribute("aria-disabled") || "") : ""),
            button_testid:String(button ? (button.getAttribute("data-testid") || "") : ""),
            hit_tag:String(hit ? hit.tagName : ""),
            hit_testid:String(hit ? (hit.getAttribute("data-testid") || "") : "")
          };
        })()`),
        after:afterTimeout
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
