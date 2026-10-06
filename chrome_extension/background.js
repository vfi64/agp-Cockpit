importScripts("result_file_attachment.js");
importScripts("native_message_evidence.js");

const ALARM_NAME = "agp-browser-refresh-tabs";
const LAST_HANDLED = "agpLastHandledRefreshGeneration";
const PENDING = "agpPendingRefreshTabs";
const K07_DOWNLOAD_ARM_STORAGE = "agpK07DownloadArms";
const K07_DOWNLOAD_ARMS = new Map();

// AGP_K07_TERMINAL_REPLY_FILE_V1: besides the Python work order, the only
// accepted remote file is the step-scoped terminal reply.
function k07SafeRemoteFileName(name) {
  const value = String(name || "").trim();
  return /^[^\\/]+\.py$/i.test(value) || /^\d+_agp_terminal\.json$/.test(value);
}

function k07DownloadNameMatches(actual, expected) {
  const actualName = String(actual || "").split(/[\\/]/).pop();
  const expectedName = String(expected || "").trim();
  if (actualName === expectedName) return true;
  const dot = expectedName.lastIndexOf(".");
  if (dot <= 0) return false;
  const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const stem = escape(expectedName.slice(0, dot));
  const suffix = escape(expectedName.slice(dot));
  // Browser duplicate suffixes: "x (1).py" and "x(2).json".
  return new RegExp(`^${stem} ?\\(\\d+\\)${suffix}$`, "i").test(actualName);
}

async function k07RecentDownloads() {
  return chrome.downloads.search({orderBy:["-startTime"], limit:100});
}

async function k07StoredDownloadArms() {
  const data = await chrome.storage.session.get([K07_DOWNLOAD_ARM_STORAGE]);
  const arms = data && data[K07_DOWNLOAD_ARM_STORAGE];
  return arms && typeof arms === "object" ? arms : {};
}

async function k07StoreDownloadArm(key, arm) {
  K07_DOWNLOAD_ARMS.set(key, {
    knownIds:new Set(arm.knownIds || []),
    armedAt:Number(arm.armedAt || Date.now()),
  });
  const stored = await k07StoredDownloadArms();
  stored[key] = {
    knownIds:Array.from(arm.knownIds || []),
    armedAt:Number(arm.armedAt || Date.now()),
  };
  await chrome.storage.session.set({[K07_DOWNLOAD_ARM_STORAGE]:stored});
}

async function k07LoadDownloadArm(key) {
  const memory = K07_DOWNLOAD_ARMS.get(key);
  if (memory) return memory;
  const stored = await k07StoredDownloadArms();
  const arm = stored[key];
  if (!arm) return null;
  return {
    knownIds:new Set(Array.isArray(arm.knownIds) ? arm.knownIds : []),
    armedAt:Number(arm.armedAt || 0),
  };
}

async function k07ForgetDownloadArm(key) {
  K07_DOWNLOAD_ARMS.delete(key);
  const stored = await k07StoredDownloadArms();
  if (Object.prototype.hasOwnProperty.call(stored, key)) {
    delete stored[key];
    await chrome.storage.session.set({[K07_DOWNLOAD_ARM_STORAGE]:stored});
  }
}

function k07DownloadStartedAfterArm(item, arm) {
  const started = Date.parse(String(item && item.startTime || ""));
  if (!Number.isFinite(started) || !Number.isFinite(arm.armedAt)) return false;
  return started + 1000 >= arm.armedAt;
}

async function agpArmCommandFileDownload(message, sender) {
  const filename = String(message && message.filename || "").trim();
  const tabId = sender && sender.tab ? sender.tab.id : null;
  if (!Number.isInteger(tabId) || !k07SafeRemoteFileName(filename)) {
    throw new Error("K07 download arm requires one safe .py or terminal-reply filename");
  }
  const known = await k07RecentDownloads();
  await k07StoreDownloadArm(`${tabId}:${filename}`, {
    knownIds: known.filter(item => k07DownloadNameMatches(item.filename, filename)).map(item => item.id),
    armedAt: Date.now(),
  });
  return {ok:true, stage:"COMMAND_FILE_DOWNLOAD_ARMED", filename};
}

async function agpWaitForCommandFileDownload(message, sender) {
  const filename = String(message && message.filename || "").trim();
  const tabId = sender && sender.tab ? sender.tab.id : null;
  const key = `${tabId}:${filename}`;
  const arm = await k07LoadDownloadArm(key);
  if (!arm) throw new Error("K07 command-file download was not armed");
  const deadline = Date.now() + 45000;
  try {
    while (Date.now() < deadline) {
      const items = await k07RecentDownloads();
      const candidate = items.find(item =>
        !arm.knownIds.has(item.id) &&
        k07DownloadNameMatches(item.filename, filename) &&
        k07DownloadStartedAfterArm(item, arm) &&
        item.state === "complete" &&
        item.filename
      );
      if (candidate) {
        return {
          ok:true,
          stage:"COMMAND_FILE_DOWNLOADED",
          filename,
          download_path:candidate.filename,
          download_id:candidate.id,
          download_bytes:Number(candidate.fileSize || candidate.totalBytes || 0),
        };
      }
      const interrupted = items.find(item =>
        !arm.knownIds.has(item.id) &&
        k07DownloadNameMatches(item.filename, filename) &&
        k07DownloadStartedAfterArm(item, arm) &&
        item.state === "interrupted"
      );
      if (interrupted) throw new Error(`browser download interrupted: ${interrupted.error || "unknown error"}`);
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    throw new Error("K07 command-file browser download timed out");
  } finally {
    await k07ForgetDownloadArm(key);
  }
}

// AGP_DOWNLOAD_HYGIENE_V1: Chrome saves every remote file in ~/Downloads; the
// bridge persists accepted work orders and terminal replies in the repository's
// Download/ (rejected ones beside their rejection record, AGP_REJECTED_ORDER_KEPT_V1).
// After that the browser copy is removed: only the exact download
// item this extension armed and waited for, matched by id and file name.
async function agpForgetCommandFileDownload(message) {
  const id = Number(message && message.download_id);
  const filename = String(message && message.filename || "").trim();
  if (!Number.isInteger(id) || id < 0 || !k07SafeRemoteFileName(filename)) {
    throw new Error("download id and one safe remote filename required");
  }
  const items = await chrome.downloads.search({id});
  const item = items && items[0];
  if (!item) return {ok:true, stage:"DOWNLOAD_ALREADY_GONE", download_id:id};
  if (!k07DownloadNameMatches(item.filename, filename)) {
    throw new Error("download item does not match the accepted file");
  }
  if (item.state === "complete" && item.exists !== false) {
    try { await chrome.downloads.removeFile(id); } catch (_) {}
  }
  await chrome.downloads.erase({id});
  return {ok:true, stage:"DOWNLOAD_REMOVED", download_id:id};
}

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

  // A Manifest-V3 service worker may be suspended as soon as the message
  // event finishes.  A delayed runtime.reload() is therefore not reliable:
  // the worker can disappear before the timer fires.  Persist the tab work
  // first, then reload the extension while this event is still alive.
  chrome.runtime.reload();

  return {
    accepted:true,
    generation,
    tabCount:tabIds.length
  };
}

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message && message.type === "AGP_K07_ARM_COMMAND_FILE_DOWNLOAD") {
      agpArmCommandFileDownload(message, sender)
        .then(sendResponse)
        .catch(error => sendResponse({ok:false, stage:"COMMAND_FILE_DOWNLOAD_ARM_FAILED", error:String(error && error.message ? error.message : error)}));
      return true;
    }
    if (message && message.type === "AGP_K07_FORGET_DOWNLOAD") {
      agpForgetCommandFileDownload(message)
        .then(sendResponse)
        .catch(error => sendResponse({ok:false, stage:"DOWNLOAD_REMOVE_FAILED", error:String(error && error.message ? error.message : error)}));
      return true;
    }
    if (message && message.type === "AGP_K07_WAIT_COMMAND_FILE_DOWNLOAD") {
      agpWaitForCommandFileDownload(message, sender)
        .then(sendResponse)
        .catch(error => sendResponse({ok:false, stage:"COMMAND_FILE_DOWNLOAD_FAILED", error:String(error && error.message ? error.message : error)}));
      return true;
    }
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

// AGP_EXTENSION_AUTO_REFRESH_V2: after runtime.reload() the alarm may not
// survive; the reloaded worker reloads the recorded ChatGPT tabs itself so
// their content scripts belong to the new build.
async function agpReloadPendingTabs() {
  const state = await chrome.storage.local.get([PENDING]);
  const pending = state[PENDING];
  if (!pending || !Array.isArray(pending.tabIds)) return 0;
  await chrome.storage.local.remove(PENDING);
  for (const tabId of pending.tabIds) {
    try { await chrome.tabs.reload(tabId); } catch (_) {}
  }
  return pending.tabIds.length;
}

if (chrome.runtime.onInstalled && typeof chrome.runtime.onInstalled.addListener === "function") {
  chrome.runtime.onInstalled.addListener(() => { void agpReloadPendingTabs(); });
}

chrome.alarms.onAlarm.addListener(async alarm => {
  if (alarm.name !== ALARM_NAME) {
    return;
  }

  await agpReloadPendingTabs();
});


// A service worker cannot reach content scripts through
// chrome.runtime.sendMessage; that API only addresses extension pages. The
// trace must be addressed to the originating tab, whose content script owns
// the authenticated /v1/client-event sink.
async function agpK07NativeTrace1165(tabId, payload) {
  if (!Number.isInteger(tabId)) return;
  try { await chrome.tabs.sendMessage(tabId, {type:"AGP_K07_NATIVE_TRACE_1165", payload}); } catch (_) {}
}

// AGP_COMPOSER_CLEAN_START_V1 (live 2026-10-02): a failed send left the
// Cockpit's bootstrap text and the command digest in the ChatGPT composer; the
// next start appended to it. Before every Cockpit send the composer must be
// empty or hold only Cockpit leftovers, which are removed: text that starts
// with the AGP-SEND nonce line, attachment chips named like Cockpit files
// (agentic-kit-command-digest*, <step>_*). Anything else (the human's own
// text or files) is never deleted; the send stops with a clear reason.
const AGP_COCKPIT_TEXT = /^AGP-SEND-[0-9a-f]{6,}/;

function agpComposerInspect(resolveComposer, removeCockpitFiles) {
  const composer = resolveComposer();
  const form = composer && typeof composer.closest === "function" ? composer.closest("form") : null;
  const text = composer
    ? String("value" in composer ? (composer.value || "") : (composer.innerText || composer.textContent || ""))
    : "";
  const files = [];
  const unrecognised = [];
  const removeLabel = /remove|entfernen|löschen|delete|close|schließen/i;
  const fileLike = /^[A-Za-z0-9][\w.-]*(\.(json|txt|md|py|csv|pdf|png|jpe?g|zip|yaml|yml)|…|\.\.\.)$/;
  if (form && composer) {
    const seen = new Set();
    for (const el of Array.from(form.querySelectorAll("*"))) {
      if (composer.contains(el)) continue;
      const labels = [el.getAttribute("aria-label") || "", el.getAttribute("title") || "",
        el.children.length ? "" : (el.textContent || "")]
        .map(value => value.replace(/\s+/g, " ").trim()).filter(value => fileLike.test(value));
      for (const name of labels) {
        if (seen.has(name)) continue;
        let chip = el;
        let button = null;
        for (let depth = 0; depth < 6 && chip && chip !== form; depth += 1, chip = chip.parentElement) {
          button = Array.from(chip.querySelectorAll("button")).find(candidate =>
            !composer.contains(candidate) &&
            removeLabel.test((candidate.getAttribute("aria-label") || "") + " " + (candidate.getAttribute("title") || "")));
          if (button) break;
        }
        if (!button) {
          // AGP_COMPOSER_CHIP_DIAGNOSTICS_V1 (live 2026-10-02: the digest chip
          // was not recognised): record the shape so the selector can follow
          // ChatGPT's real markup.
          if (unrecognised.length < 5 && /^(agentic-kit-comm|\d+_)/i.test(name)) {
            let host = el;
            for (let depth = 0; depth < 4 && host.parentElement && host.parentElement !== form; depth += 1) host = host.parentElement;
            unrecognised.push({name, buttons:Array.from(host.querySelectorAll("button, [role=button]")).slice(0, 4).map(b => ({
              tag:b.tagName, aria_label:String(b.getAttribute("aria-label") || "").slice(0, 40),
              title:String(b.getAttribute("title") || "").slice(0, 40),
              testid:String(b.getAttribute("data-testid") || "")}))});
          }
          continue;                     // not an attachment chip
        }
        seen.add(name);
        const prefix = name.replace(/(…|\.\.\.)$/, "").trim();
        const cockpit = /^agentic-kit-comm/i.test(prefix) || /^\d+_/.test(prefix);
        files.push({name, cockpit});
        if (removeCockpitFiles && cockpit) button.click();
      }
    }
  }
  return {composer:Boolean(composer), text, files, unrecognised};
}

async function agpComposerCleanup(evaluate, sendCommand, normalize, {files = true} = {}) {
  const inspect = remove => evaluate(`(${agpComposerInspect.toString()})(${agpResolveComposer.toString()}, ${remove ? "true" : "false"})`);
  const before = await inspect(false);
  if (!before || !before.composer) return {ok:true, stage:"COMPOSER_NOT_FOUND_SKIPPED", before};
  const text = normalize(before.text);
  if (text && !AGP_COCKPIT_TEXT.test(text)) {
    return {ok:false, stage:"COMPOSER_HAS_FOREIGN_TEXT", before,
      reason:"Das ChatGPT-Eingabefeld enthält Text, der nicht vom Cockpit stammt; bitte leeren und erneut starten."};
  }
  // files=false: the native transport keeps the evidence just attached for
  // this very send and only clears leftover text.
  const chips = files ? (before.files || []) : [];
  const foreign = chips.filter(file => !file.cockpit);
  if (foreign.length) {
    return {ok:false, stage:"COMPOSER_HAS_FOREIGN_FILES", before,
      reason:"Im ChatGPT-Eingabefeld hängen Dateien, die nicht vom Cockpit stammen: " +
        foreign.map(file => file.name).join(", ") + "; bitte entfernen und erneut starten."};
  }
  let removed = [];
  if (chips.length) {
    await inspect(true);
    removed = chips.map(file => file.name);
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  if (text) {
    await evaluate(`(() => { const c = (${agpResolveComposer.toString()})(); if (c && c.focus) c.focus(); return true; })()`);
    await sendCommand("Input.dispatchKeyEvent", {type:"keyDown", key:"a", code:"KeyA",
      windowsVirtualKeyCode:65, nativeVirtualKeyCode:65, commands:["selectAll"]});
    await sendCommand("Input.dispatchKeyEvent", {type:"keyUp", key:"a", code:"KeyA", windowsVirtualKeyCode:65});
    await sendCommand("Input.dispatchKeyEvent", {type:"keyDown", key:"Backspace", code:"Backspace",
      windowsVirtualKeyCode:8, nativeVirtualKeyCode:8, commands:["deleteBackward"]});
    await sendCommand("Input.dispatchKeyEvent", {type:"keyUp", key:"Backspace", code:"Backspace", windowsVirtualKeyCode:8});
    let after = await inspect(false);
    if (after && normalize(after.text)) {
      await evaluate(`(() => { const c = (${agpResolveComposer.toString()})(); if (!c) return false;
        c.focus(); document.execCommand("selectAll", false); document.execCommand("delete", false); return true; })()`);
      after = await inspect(false);
    }
    if (after && normalize(after.text)) {
      return {ok:false, stage:"COMPOSER_NOT_CLEARED", before, after,
        reason:"Das ChatGPT-Eingabefeld konnte nicht geleert werden; bitte von Hand leeren."};
    }
  }
  const final = await inspect(false);
  const remaining = files ? ((final && final.files) || []).filter(file => file.cockpit).map(file => file.name) : [];
  if (remaining.length) {
    return {ok:false, stage:"COMPOSER_FILES_NOT_REMOVED", before, final,
      reason:"Alte Cockpit-Anhänge im ChatGPT-Eingabefeld ließen sich nicht entfernen: " + remaining.join(", ")};
  }
  return {ok:true, stage:text || removed.length ? "COMPOSER_CLEANED" : "COMPOSER_EMPTY",
    cleared_text:Boolean(text), removed_files:removed, unrecognised:(final && final.unrecognised) || []};
}

async function agpCleanComposer(tabId, options = {}) {
  const target = {tabId};
  let attached = false;
  const sendCommand = (method, params) => chrome.debugger.sendCommand(target, method, params || {});
  const evaluate = async expression => {
    const result = await sendCommand("Runtime.evaluate", {expression, returnByValue:true, awaitPromise:true});
    if (result && result.exceptionDetails) throw new Error("CDP Runtime.evaluate failed");
    return result && result.result ? result.result.value : null;
  };
  const normalize = value => String(value || "").normalize("NFKC")
    .replace(/[​‌‍﻿]/g, "").replace(/ /g, " ").replace(/\s+/g, " ").trim();
  try {
    await chrome.debugger.attach(target, "1.3");
    attached = true;
    return await agpComposerCleanup(evaluate, sendCommand, normalize, {files:options.files !== false});
  } finally {
    if (attached) { try { await chrome.debugger.detach(target); } catch (_) {} }
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "AGP_K07_CLEAN_COMPOSER") return false;
  const tabId = sender && sender.tab ? sender.tab.id : null;
  if (!Number.isInteger(tabId)) { sendResponse({ok:false, reason:"no tab"}); return false; }
  agpCleanComposer(tabId, {files:message.files !== false}).then(sendResponse)
    .catch(error => sendResponse({ok:false, stage:"COMPOSER_CLEAN_FAILED",
      reason:String(error && error.message ? error.message : error)}));
  return true;
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
    .normalize("NFKC")
    .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const normalizeRenderedUserTurn = value => agpNormalizeUserTurnText(value);
  const renderedUserTurnMatches = (observed, expected) => {
    if (typeof agpRenderedUserTurnMatches === "function") {
      return agpRenderedUserTurnMatches(observed, expected);
    }
    return normalizeRenderedUserTurn(observed) === normalizeRenderedUserTurn(expected);
  };

  try {
    await chrome.debugger.attach(target, "1.3");
    attached = true;

    await chrome.debugger.sendCommand(target, "Runtime.enable");

    const observeMessages = () => evaluate(`(${agpNativeMessageSnapshot.toString()})(${agpResolveComposer.toString()})`);

    // AGP_K07_SEND_COMMIT_NONCE_V1
    // The content script prefixes every prompt with a fresh nonce line. Its
    // persistent appearance outside the composer after submit is decisive
    // commit evidence independent of user-turn selectors, ids, rendering,
    // virtualization and URL changes.
    const commitMarker = String(message.commit_marker || "");
    if (commitMarker && (!/^AGP-SEND-[0-9a-f]{16}$/.test(commitMarker) || !text.startsWith(commitMarker + "\n"))) {
      throw new Error("invalid native transport commit marker");
    }
    const observeMarker = async () => {
      if (!commitMarker) return null;
      return evaluate(`(() => {
        const marker = ${JSON.stringify(commitMarker)};
        const count = value => String(value || "").split(marker).length - 1;
        const composer = (${agpResolveComposer.toString()})();
        const inBody = composer && !(composer instanceof HTMLTextAreaElement)
          ? count(composer.innerText || composer.textContent || "")
          : 0;
        const bodyText = document.body ? (document.body.innerText || document.body.textContent || "") : "";
        return {outside_composer:Math.max(0, count(bodyText) - inBody), in_composer:inBody};
      })()`);
    };
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

    // ChatGPT can leave a duplicate-upload alert open after the result
    // evidence was accepted into the composer. The alert may be rendered in
    // an open shadow root and can appear shortly after the file input settles.
    // Dismiss only this exact, visible alert before verifying editor focus;
    // never click arbitrary OK buttons.
    let duplicateUploadDialog = null;
    for (let attempt = 0; attempt < 12; attempt += 1) {
      duplicateUploadDialog = await evaluate(`(() => {
        const duplicatePhrases = [
          "Du hast diese Datei bereits hochgeladen",
          "You have already uploaded this file"
        ];
        const textOf = node => String(
          node && (node.innerText || node.textContent || "")
        );
        const visible = node => {
          if (!node || typeof node.getBoundingClientRect !== "function") return false;
          const rect = node.getBoundingClientRect();
          const style = getComputedStyle(node);
          return rect.width > 0 && rect.height > 0 &&
            style.visibility !== "hidden" && style.display !== "none";
        };
        const roots = [];
        const visit = root => {
          if (!root || roots.includes(root)) return;
          roots.push(root);
          for (const element of root.querySelectorAll
            ? root.querySelectorAll("*") : []) {
            if (element.shadowRoot) visit(element.shadowRoot);
          }
        };
        visit(document);
        const elements = roots.flatMap(root => Array.from(
          root.querySelectorAll ? root.querySelectorAll("*") : []
        ));
        const bodyText = textOf(document.body);
        const duplicateText = duplicatePhrases.some(phrase =>
          bodyText.includes(phrase) || elements.some(element =>
            visible(element) && textOf(element).includes(phrase)
          )
        );
        if (!duplicateText) return {present:false, dismissed:false};

        const controls = elements.filter(element => {
          const tag = String(element.tagName || "").toLowerCase();
          return tag === "button" || element.getAttribute("role") === "button";
        });
        const active = document.activeElement;
        if (active && !controls.includes(active)) controls.unshift(active);
        const ok = controls.find(button => visible(button) &&
          /^(OK|Ok)$/i.test(textOf(button).trim()));
        if (!ok) return {
          present:true,
          dismissed:false,
          reason:"ok_button_not_found",
          active_tag:active ? active.tagName : "",
          active_text:textOf(active).trim()
        };
        ok.click();
        return {
          present:true,
          dismissed:true,
          control_tag:String(ok.tagName || ""),
          control_role:String(ok.getAttribute("role") || "")
        };
      })()`);
      if (!duplicateUploadDialog || !duplicateUploadDialog.present) break;
      if (duplicateUploadDialog.dismissed) {
        await new Promise(resolve => setTimeout(resolve, 150));
        continue;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // Re-focus the canonical editor inside the debugger context. The page
    // may still have focus on a dialog button even when the composer exists.
    // Do not insert text until ownership of focus is observable.
    let focusVerification = null;
    for (let attempt = 0; attempt < 10; attempt += 1) {
      focusVerification = await evaluate(`(() => {
        const composer = (${agpResolveComposer.toString()})();
        const activeBefore = document.activeElement;
        if (activeBefore && activeBefore !== composer && typeof activeBefore.blur === "function") {
          activeBefore.blur();
        }
        if (composer && typeof window.focus === "function") window.focus();
        if (composer && typeof composer.focus === "function") composer.focus();
        const active = document.activeElement;
        const textboxes = Array.from(document.querySelectorAll('[contenteditable="true"][role="textbox"]'));
        return {
          ok:Boolean(composer && active === composer),
          textboxes:textboxes.length,
          visible_textboxes:textboxes.filter(el => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
          }).length,
          active_tag:active ? active.tagName : "",
          active_id:active ? active.id : "",
          composer_tag:composer ? composer.tagName : "",
          composer_id:composer ? composer.id : ""
        };
      })()`);
      if (focusVerification && focusVerification.ok === true) break;
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    if (!focusVerification || focusVerification.ok !== true) {
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:"COMPOSER_FOCUS_NOT_VERIFIED",
        before,
        duplicate_upload_dialog:duplicateUploadDialog,
        focus:focusVerification
      };
    }

    // AGP_COMPOSER_CLEAN_START_V1: leftover Cockpit text of a failed send
    // would be prefixed to this message; the human's own text is kept.
    const composerClean = await agpComposerCleanup(
      evaluate, (method, params) => chrome.debugger.sendCommand(target, method, params || {}),
      normalize, {files:false});
    if (!composerClean || composerClean.ok !== true) {
      return {ok:false, request_id:requestId, tab_id:tabId, stage:composerClean ? composerClean.stage : "COMPOSER_NOT_CLEAN",
        reason:composerClean ? composerClean.reason : "", before};
    }

    await chrome.debugger.sendCommand(
      target,
      "Input.insertText",
      {text}
    );

    const inserted = await evaluate(`(() => {
      const active = document.activeElement;
      const composer = (${agpResolveComposer.toString()})();
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
        focus:focusVerification,
        inserted
      };
    }

    // AGP_COMPOSER_MODEL_VERIFIED_001
    // DOM text alone is insufficient for ProseMirror/React editors. Require
    // the canonical editor to own focus and expose an actionable send control
    // after the input event has settled. This is the observable boundary for
    // the editor model before Enter is dispatched.
    let modelVerification = null;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      modelVerification = await evaluate(`(() => {
        const composer = (${agpResolveComposer.toString()})();
        const active = document.activeElement;
        const value = composer && "value" in composer
          ? String(composer.value || "")
          : String((composer && (composer.innerText || composer.textContent)) || "");
        const buttons = Array.from(document.querySelectorAll(
          'button[data-testid="send-button"], button[aria-label*="Send"], button[aria-label*="Senden"], form button[type="submit"]'
        ));
        const normalize = value => String(value || "")
          .replace(/\\u00a0/g, " ")
          .replace(/\\s+/g, " ")
          .trim();
        const send = buttons.find(button => {
          const rect = button.getBoundingClientRect();
          const style = getComputedStyle(button);
          return !button.disabled && button.getAttribute("aria-disabled") !== "true" &&
            rect.width > 0 && rect.height > 0 && style.display !== "none" &&
            style.visibility !== "hidden" && style.pointerEvents !== "none";
        });
        return {
          // Focus is useful evidence for refocusing, but it is not proof of
          // the editor model. ChatGPT may move focus while React/ProseMirror
          // has already accepted the inserted value. The stable boundary is
          // the canonical composer value plus an actionable send control.
          stage: composer && normalize(value) === ${JSON.stringify(normalize(text))} && Boolean(send)
            ? "COMPOSER_MODEL_VERIFIED"
            : "COMPOSER_MODEL_NOT_VERIFIED",
          value,
          active_tag: active ? active.tagName : "",
          active_id: active ? active.id : "",
          focused: active === composer,
          composer_id: composer ? composer.id : "",
          send_available: Boolean(send)
        };
      })()`);
      if (modelVerification && modelVerification.stage === "COMPOSER_MODEL_VERIFIED") break;
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    if (!modelVerification || modelVerification.stage !== "COMPOSER_MODEL_VERIFIED") {
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:"COMPOSER_MODEL_NOT_VERIFIED",
        before,
        inserted,
        model:modelVerification,
        model_wait_ms:3000
      };
    }

    // 825 proved insertion succeeds while the prior submit path did not commit.
    // React may publish/enable the send control shortly after Input.insertText.
    // Wait boundedly for a truly actionable target instead of sampling once.
    // AGP_SEND_READY_AFTER_UPLOAD_V1 (live 2026-10-02, Arbeit beginnen): an
    // attachment that is still uploading (the re-attached command digest)
    // keeps the send control disabled longer than 3 s; wait up to 30 s.
    let sendTarget = null;
    let sendDiagnostics = null;
    for (let attempt = 0; attempt < 600; attempt += 1) {
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
              hit_testid:String(hit ? (hit.getAttribute("data-testid") || "") : ""),
              in_form:Boolean(button.closest && button.closest("form"))
            };
            diagnostics.push(record);
            if (
              !record.disabled &&
              record.aria_disabled !== "true" &&
              record.visible &&
              record.pointer_events !== "none" &&
              (record.hit_matches || record.testid === "send-button" ||
               // AGP_SEND_CONTROL_SEMANTIC_V1 (live 2026-10-02): a ChatGPT
               // variant renders the send button without data-testid and its
               // icon svg outside the button, so the hit test fails although
               // the control is enabled. Submission is a trusted Enter in the
               // composer, not a click; an enabled submit button labelled
               // Send/Senden inside the composer form is the readiness signal.
               // AGP_PROBE_TEMPLATE_ESCAPES_V1: this code is a template literal,
               // so regex escapes need a double backslash (a single one before
               // b cooks to a backspace that never matched — live stop 2026-10-02, step 1598).
               (record.in_form && record.type === "submit" && /^(send|senden)\\b/i.test(record.aria_label)))
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
      // AGP_SEND_NOT_READY_RETRY_V1: what the composer area offered instead
      // (live 2026-10-02: "Arbeit beginnen" twice NOT_READY for 30 s with the
      // text verified in the composer and no upload pending).
      let formButtons = [];
      try {
        formButtons = await evaluate(`(() => {
          const composer = (${agpResolveComposer.toString()})();
          const form = composer && composer.closest ? composer.closest("form") : null;
          const scope = form || document;
          return Array.from(scope.querySelectorAll("button")).slice(0, 25).map(b => ({
            aria_label:String(b.getAttribute("aria-label") || "").slice(0, 60),
            testid:String(b.getAttribute("data-testid") || ""),
            disabled:Boolean(b.disabled),
            aria_disabled:String(b.getAttribute("aria-disabled") || ""),
            text:String(b.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 40)
          })).concat([{stop_button:Boolean(document.querySelector('[data-testid="stop-button"]')),
            in_form:Boolean(form)}]);
        })()`) || [];
      } catch (_) {}
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:"SEND_BUTTON_NOT_READY",
        form_buttons:formButtons,
        before,
        inserted,
        model:modelVerification,
        send_target:null,
        send_diagnostics:sendDiagnostics,
        readiness_wait_ms:30000
      };
    }

    const markerBaseline = (await observeMarker()) || {outside_composer:0, in_composer:0};
    // AGP_SUBMIT_FOCUS_AND_FORM_BUTTON_V1: the trusted Enter goes to the
    // focused element; make that the resolved composer again.
    const refocusForSubmit = () => evaluate(
      `(${agpRefocusComposerForSubmit.toString()})(${agpResolveComposer.toString()})`);
    const focusBeforeEnter = await refocusForSubmit();
    void agpK07NativeTrace1165(tabId, {event:"PRIMARY_ENTER_BEFORE",request_id:requestId,send_target:sendTarget,inserted:inserted,focus_before_enter:focusBeforeEnter});
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
    let markerStreak = 0;
    const observeCommit = async () => {
      const observed = await observeMessages();
      const exactIndex = observed.url === beforeMessages.url
        ? observed.messages.findIndex((message, index) =>
          renderedUserTurnMatches(message.text, text) &&
          (message.id ? !previousIds.has(message.id) : index >= beforeMessages.messages.length))
        : -1;
      const marker = await observeMarker();
      markerStreak = marker && marker.outside_composer > markerBaseline.outside_composer
        ? markerStreak + 1
        : 0;
      observed.exact_user_message_index = exactIndex;
      observed.commit_marker = marker;
      observed.commit_marker_streak = markerStreak;
      observed.exact_user_message_found = exactIndex >= 0 || markerStreak >= 2;
      observed.commit_via = exactIndex >= 0
        ? "rendered_user_turn"
        : (markerStreak >= 2 ? "commit_marker" : "");
      return observed;
    };
    for (let i = 0; i < 40; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));
      const observed = await observeCommit();
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
        const focusBeforeRetry = await refocusForSubmit();
        void agpK07NativeTrace1165(tabId, {event:"RETRY_ENTER_BEFORE",request_id:requestId,last_observed:lastObserved,focus_before_enter:focusBeforeRetry});
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
          const observed = await observeCommit();
          lastObserved = observed;
          if (observed.exact_user_message_found) { commitEvidence = observed; break; }
        }
        if (commitEvidence) {
          return {ok:true,request_id:requestId,tab_id:tabId,stage:"USER_TURN_COMMITTED",
            before,inserted,commit:commitEvidence,commit_retry:"trusted_enter_once",model:modelVerification};
        }

        // Some ChatGPT composer revisions ignore synthetic Enter while exposing
        // the canonical send control. Use that exact control as a bounded DOM
        // fallback, then require the same persistent-message evidence.
        // AGP_SUBMIT_FOCUS_AND_FORM_BUTTON_V1: the control is the send button of
        // the resolved composer's form (button[data-testid="send-button"] or a
        // submit button labelled Send/Senden), never a page-wide match.
        const clickResult = await evaluate(`(() => {
          const button = (${agpComposerSendButton.toString()})(${agpResolveComposer.toString()});
          if (!button) return {clicked:false, reason:"send_button_unavailable"};
          button.click();
          return {clicked:true, aria_label:String(button.getAttribute("aria-label") || ""),
            testid:String(button.getAttribute("data-testid") || "")};
        })()`);
        void agpK07NativeTrace1165(tabId, {event:"DOM_SEND_FALLBACK",request_id:requestId,click_result:clickResult});
        if (clickResult && clickResult.clicked) {
          for (let i = 0; i < 20; i += 1) {
            await new Promise(resolve => setTimeout(resolve, 250));
            const observed = await observeCommit();
            lastObserved = observed;
            if (observed.exact_user_message_found) {
              commitEvidence = observed;
              break;
            }
          }
          if (commitEvidence) {
            return {ok:true,request_id:requestId,tab_id:tabId,stage:"USER_TURN_COMMITTED",
              before,inserted,commit:commitEvidence,commit_retry:"canonical_dom_button",model:modelVerification};
          }
        }
      }
      void agpK07NativeTrace1165(tabId, {event:"COMMIT_FAILURE",request_id:requestId,clearly_unsent:Boolean(clearlyUnsent),before_messages:beforeMessages,send_target:sendTarget,last_observed:lastObserved});
      return {
        ok:false,
        request_id:requestId,
        tab_id:tabId,
        stage:clearlyUnsent ? "USER_TURN_NOT_COMMITTED" : "USER_TURN_INDETERMINATE",
        before,
        inserted,
        model:modelVerification,
        send_target:sendTarget,
        after:lastObserved,
        diagnostics: {
          before_user_message_count:Number(beforeMessages.user_message_count || 0),
          before_latest_user_message_chars:String(beforeMessages.latest_user_message || "").length,
          after_user_message_count:Number(lastObserved && lastObserved.user_message_count || 0),
          after_latest_user_message_chars:String(lastObserved && lastObserved.latest_user_message || "").length,
          after_exact_user_message_found:Boolean(lastObserved && lastObserved.exact_user_message_found),
          commit_marker_present:Boolean(commitMarker),
          commit_marker_baseline:markerBaseline,
          after_commit_marker:lastObserved ? lastObserved.commit_marker || null : null,
          before_url:String(beforeMessages.url || ""),
          after_composer_chars:String(lastObserved && lastObserved.composer_text || "").length,
          after_generation_active:Boolean(lastObserved && lastObserved.generation_active),
          selector_url:String(lastObserved && lastObserved.url || "")
        }
      };
    }

    return {
      ok:true,
      request_id:requestId,
      tab_id:tabId,
      stage:"USER_TURN_COMMITTED",
      before,
      inserted,
      commit:commitEvidence,
      model:modelVerification
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

  if (!href || !filename || !k07SafeRemoteFileName(filename)) {
    throw new Error("K07 command-file fetch requires one .py or terminal-reply attachment");
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
  const outputPath = String(message.output_file || "").trim();
  const continuationPrompt = String(message.prompt || "").trim();
  if (!Number.isInteger(tabId) || !absolutePath.startsWith("/") || (outputPath && !outputPath.startsWith("/")) || !continuationPrompt || continuationPrompt.length > 2000000) {
    sendResponse({ok:false, stage:"RESULT_CONTINUATION_REJECTED"});
    return false;
  }
  agpSubmitFileLoopContinuation(tabId, absolutePath, outputPath, continuationPrompt, message.cycle_id, message.result_sha256)
    .then(sendResponse)
    .catch(error => sendResponse({ok:false, stage:"RESULT_CONTINUATION_FAILED", error:String(error && error.message ? error.message : error)}));
  return true;
});

// AGP_KIT_COMMAND_CATALOG_V1: attach local files (the Kit command digest)
// to the composer before the mission start is sent.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "AGP_K07_ATTACH_FILES") return false;
  const tabId = sender && sender.tab ? sender.tab.id : null;
  const files = Array.isArray(message.files) ? message.files.map(String) : [];
  if (!Number.isInteger(tabId) || !files.length || files.some(file => !file.startsWith("/"))) {
    sendResponse({ok:false, error:"absolute file paths and a tab are required"});
    return false;
  }
  globalThis.AGPResultFileAttachment.attachResultFiles(chrome, {tabId}, files)
    .then(result => sendResponse({ok:result && result.stage === "RESULT_FILES_ATTACHED", evidence:result && result.evidence}))
    .catch(error => sendResponse({ok:false, error:String(error && error.message ? error.message : error)}));
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
async function agpSubmitFileLoopContinuation(tabId, absolutePath, outputPath, continuationPrompt, cycleId, resultSha256) {
  if (!globalThis.AGPResultFileAttachment || typeof globalThis.AGPResultFileAttachment.attachResultFiles !== "function") throw new Error("K07 result-file attachment seam unavailable");
  // AGP_COMPOSER_CLEAN_START_V1: leftovers of a failed send never travel along.
  const cleaned = await agpCleanComposer(tabId);
  if (!cleaned || cleaned.ok !== true) throw new Error(String(cleaned && cleaned.reason || "ChatGPT composer not clean"));
  const evidence = [absolutePath];
  if (outputPath) evidence.push(outputPath);
  const attached = await globalThis.AGPResultFileAttachment.attachResultFiles(chrome, {tabId}, evidence);
  if (!attached || attached.stage !== "RESULT_FILES_ATTACHED") throw new Error("K07 result evidence attachment was not confirmed");
  const response = await chrome.tabs.sendMessage(tabId, {
    type: "AGP_K07_SEND_PROMPT",
    prompt: continuationPrompt
  });
  if (!response || response.ok !== true) {
    throw new Error(String(response && response.error || "ChatGPT prompt transport unavailable"));
  }
  return {ok:true, stage:"RESULT_ATTACHED_AND_CONTINUATION_SENT", file_path:absolutePath, evidence_files:evidence, cycle_id:cycleId || null, result_sha256:resultSha256 || null, trace_events:[{event:"BROWSER_RESULT_EVIDENCE_ATTACHED",cycle_id:cycleId || null,result_sha256:resultSha256 || null,evidence_files:evidence},{event:"CONTINUATION_SENT",cycle_id:cycleId || null,result_sha256:resultSha256 || null}]};
}
