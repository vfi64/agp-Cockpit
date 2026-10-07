// Shared by the content script and the serialized CDP observation.
// Keep this function self-contained: toString() preserves regex escapes in CDP.
function agpNormalizeUserTurnText(value) {
  return String(value || "")
    .normalize("NFKC")
    .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
    .replace(/\u00a0/g, " ")
    // ChatGPT exposes the rendered user Markdown, not the raw composer text.
    .replace(/```[^\n]*\n?/g, "")
    .replace(/`/g, "")
    .replace(/\\([\\`*_{}\[\]()#+.!>~-])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function agpRenderedUserTurnMatches(observed, expected) {
  const observedText = agpNormalizeUserTurnText(observed);
  const expectedText = agpNormalizeUserTurnText(expected);
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

// AGP_COMPOSER_RESOLVER_V1: one self-contained composer identity for the
// content script and every serialized CDP expression (toString()).
// Live 2026-09-30 on a new chat (https://chatgpt.com/): the focus step took
// the first [contenteditable][role=textbox] in document order, blurred the
// focused visible composer and could not focus its choice
// (COMPOSER_FOCUS_NOT_VERIFIED, active element BODY). Only visible, enabled,
// non-inert candidates count; the focused candidate wins.
function agpResolveComposer() {
  const usable = el => {
    if (!el || el.disabled || el.isConnected === false) return false;
    if (typeof el.closest === "function" && el.closest('[inert], [aria-hidden="true"]')) return false;
    const rect = el.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) return false;
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    // AGP_COMPOSER_VISIBLE_FORM_V1: the ChatGPT start page (live 2026-10-05)
    // renders three composer forms, two of them 0x0. A composer inside an
    // invisible form is never the owner's composer.
    const form = typeof el.closest === "function" ? el.closest("form") : null;
    if (form) {
      const formRect = form.getBoundingClientRect();
      if (!(formRect.width > 0 && formRect.height > 0)) return false;
    }
    return true;
  };
  // AGP_SELECTOR_TABLE_V1: AGP_SELECTORS is the content-script global, or the scope that
  // the service worker puts around every injected expression (agpPageExpression, chatgpt_selectors.js).
  const candidates = Array.from(document.querySelectorAll(AGP_SELECTORS.composer)).filter(usable);
  if (!candidates.length) return null;
  const active = document.activeElement;
  if (active && candidates.includes(active)) return active;
  const byId = candidates.find(el => el.id === AGP_SELECTORS.composerPreferredId);
  if (byId) return byId;
  return candidates.find(el => typeof el.closest === "function" && el.closest("form")) || candidates[0];
}

function agpNativeMessageSnapshot(resolveComposer) {
  // Keep the snapshot self-contained: background.js serializes this function
  // into the page through Runtime.evaluate(...toString()).
  const norm = value => String(value || "")
    .normalize("NFKC")
    .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
    .replace(/\u00a0/g, " ")
    .replace(/```[^\n]*\n?/g, "")
    .replace(/`/g, "")
    .replace(/\\([\\`*_{}\[\]()#+.!>~-])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
  // ChatGPT has used several equivalent user-turn wrappers. Prefer the
  // semantic role selector, then fall back to the turn/test-id wrappers. Do
  // not combine selector results: nested wrappers would double-count a turn.
  const userSelectors = AGP_SELECTORS.userTurn;   // AGP_SELECTOR_TABLE_V1
  const visibleElement = node => {
    if (!node || typeof node.getBoundingClientRect !== "function") return false;
    const r = node.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const cloneMessageText = node => {
    const content = node.querySelector(AGP_SELECTORS.userTurnContent);
    const copy = (content || node).cloneNode(true);
    copy.querySelectorAll('button, [role="button"], [aria-hidden="true"]').forEach(control => control.remove());
    copy.querySelectorAll('br').forEach(br => br.replaceWith(document.createTextNode("\n")));
    copy.querySelectorAll('div, p, pre, li, h1, h2, h3, h4, blockquote, tr').forEach(block => {
      block.prepend(document.createTextNode("\n"));
      block.append(document.createTextNode("\n"));
    });
    return norm(copy.textContent || "");
  };
  let nodes = [];
  for (const selector of userSelectors) {
    const candidates = Array.from(document.querySelectorAll(selector))
      .filter(visibleElement);
    if (candidates.length) {
      nodes = candidates;
      break;
    }
  }
  nodes = nodes.filter(visibleElement);
  let messages = nodes.map(node => ({
    id:node.getAttribute("data-message-id") || "",
    text:cloneMessageText(node)
  }));
  if (!messages.length) {
    const userLabels = new Set(["du hast gesagt", "du hast gesagt:", "you said", "you said:"]);
    const authorLabels = new Set([
      "du hast gesagt", "du hast gesagt:", "you said", "you said:",
      "chatgpt hat gesagt", "chatgpt hat gesagt:", "chatgpt said", "chatgpt said:"
    ]);
    const labelCandidates = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role='heading'],strong,span,div"))
      .filter(visibleElement)
      .filter(node => {
        const value = norm(node.textContent).toLowerCase();
        return value.length <= 40 && userLabels.has(value);
      });
    const textFromLabel = label => {
      for (let base = label; base; base = base.parentElement) {
        const parent = base.parentElement;
        if (!parent || parent === document.body || parent === document.documentElement) break;
        const parts = [];
        for (let sibling = base.nextElementSibling; sibling; sibling = sibling.nextElementSibling) {
          const boundary = norm(sibling.textContent).toLowerCase();
          if (boundary.length <= 40 && authorLabels.has(boundary)) break;
          if (!visibleElement(sibling)) continue;
          const text = cloneMessageText(sibling);
          if (text) parts.push(text);
          if (parts.length) break;
        }
        if (parts.length) return parts.join(" ");
      }
      return "";
    };
    messages = labelCandidates
      .map(label => ({
        id:label.getAttribute("data-message-id") || "",
        text:textFromLabel(label)
      }))
      .filter(message => message.text);
  }
  const composer = typeof resolveComposer === "function"
    ? resolveComposer()
    : document.querySelector(AGP_SELECTORS.composerSnapshotFallback);
  return {
    url:location.href,
    messages,
    user_message_count:messages.length,
    latest_user_message:messages.length ? messages[messages.length - 1].text : "",
    composer_text:norm(composer ? ("value" in composer ? composer.value : composer.innerText || composer.textContent) : ""),
    generation_active:Boolean(document.querySelector(AGP_SELECTORS.generationActiveQuick))
  };
}

// AGP_SUBMIT_FOCUS_AND_FORM_BUTTON_V1 (live 2026-10-05, build r6, new chat):
// after Input.insertText on the ChatGPT start page the focus moved from the
// composer to <main> (inserted.active_tag MAIN; in every earlier successful
// send it was the composer DIV), so the trusted Enter went nowhere; the DOM
// fallback then looked only for button[data-testid="send-button"], which the
// current UI no longer renders. Both helpers are self-contained: background.js
// serializes them into the page with Function.prototype.toString().
function agpRefocusComposerForSubmit(resolveComposer) {
  const composer = typeof resolveComposer === "function" ? resolveComposer() : null;
  if (!composer) return {ok:false, reason:"composer_not_found", active_tag:"", active_id:""};
  const before = document.activeElement;
  const refocused = before !== composer;
  if (refocused) {
    if (typeof window.focus === "function") window.focus();
    if (typeof composer.focus === "function") composer.focus();
    if (!("value" in composer) && typeof window.getSelection === "function") {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(composer);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }
  const active = document.activeElement;
  return {
    ok:active === composer,
    refocused,
    before_tag:before ? before.tagName : "",
    active_tag:active ? active.tagName : "",
    active_id:active ? active.id : ""
  };
}

function agpComposerSendButton(resolveComposer) {
  const composer = typeof resolveComposer === "function" ? resolveComposer() : null;
  const form = composer && typeof composer.closest === "function" ? composer.closest("form") : null;
  if (!form) return null;
  const buttons = Array.from(form.querySelectorAll(AGP_SELECTORS.formSendButton));   // AGP_SELECTOR_TABLE_V1
  return buttons.find(button => {
    const label = String(button.getAttribute("aria-label") || "");
    if (button.getAttribute("data-testid") !== AGP_SELECTORS.sendButtonTestId && !/^(send|senden)\b/i.test(label)) return false;
    if (button.disabled || button.getAttribute("aria-disabled") === "true") return false;
    const rect = button.getBoundingClientRect();
    const style = getComputedStyle(button);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" &&
      style.display !== "none" && style.pointerEvents !== "none";
  }) || null;
}

// AGP_MISSION_TOUCHPOINT_SELFTEST_V1 (Slice C, 2026-10-05): before a mission
// start touches the composer, check every touchpoint the run will need: the
// visible composer (agpResolveComposer), its form, and an enabled file input in
// that form (digest and result evidence are attached there). r6 failed only
// after the digest had gone to an invisible form, and its diagnosis needed DOM
// probes in DevTools by the owner. The snapshot below records the page shape
// (counts and ids only, no text) with every start, so the next UI change is
// diagnosable from the bridge log. The send button is not checked: ChatGPT
// renders it only after text was inserted (submit uses refocus + form button,
// AGP_SUBMIT_FOCUS_AND_FORM_BUTTON_V1). Self-contained like the helpers above.
function agpMissionTouchpointCheck(resolveComposer) {
  const visible = el => {
    if (!el || typeof el.getBoundingClientRect !== "function") return false;
    const rect = el.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) return false;
    const style = getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden";
  };
  const path = String((typeof location !== "undefined" && location.pathname) || "");
  const forms = Array.from(document.querySelectorAll("form"));
  const composer = typeof resolveComposer === "function" ? resolveComposer() : null;
  const form = composer && typeof composer.closest === "function" ? composer.closest("form") : null;
  const fileInputs = form ? Array.from(form.querySelectorAll('input[type="file"]')) : [];
  const enabledFileInputs = fileInputs.filter(input => !input.disabled);
  const snapshot = {
    page: path === "/" ? "start" : (path.startsWith("/c/") ? "chat" : "other"),
    forms: forms.length,
    visible_forms: forms.filter(visible).length,
    composer_found: Boolean(composer),
    composer_tag: composer ? composer.tagName : "",
    composer_id: composer ? String(composer.id || "") : "",
    composer_focused: Boolean(composer) && document.activeElement === composer,
    composer_form_index: form ? forms.indexOf(form) : -1,
    file_inputs_in_form: fileInputs.length,
    enabled_file_inputs_in_form: enabledFileInputs.length,
    send_testid_in_form: Boolean(form && form.querySelector(AGP_SELECTORS.sendButtonByTestId))
  };
  const ui = agpUiFingerprint(composer, form);
  let reason = "";
  if (!composer) reason = "composer_not_found";
  else if (!form) reason = "composer_form_not_found";
  else if (!enabledFileInputs.length) reason = "file_input_not_found";
  return {ok:!reason, reason, snapshot, fingerprint:ui.fingerprint, ui_signature:ui.signature,
    fingerprint_version:ui.version};
}

// AGP_UI_FINGERPRINT_V1 (DOM hardening step 5, owner 2026-10-07): a short fingerprint of the
// composer's structure — its tag, the data-testid values inside its form (digits folded) and
// the file-input count; no text. The bridge records every new value as a new ChatGPT UI
// variant, so a later failure can be related to a UI change. FNV-1a keeps it synchronous.
function agpFnv1a(text) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

// AGP_UI_FINGERPRINT_VERSIONED_V1: the algorithm version travels with every fingerprint, so a
// new algorithm is never mistaken for a new ChatGPT page (live 2026-10-07: V1 → V2 showed "NEU").
// Raise it whenever agpUiFingerprint changes what it collects.
const AGP_UI_FINGERPRINT_VERSION = 2;

function agpUiFingerprint(composer, form) {
  // AGP_UI_FINGERPRINT_V2 (live 2026-10-07, variant a0785191): at the start the composer form
  // carries no data-testid, so V1 saw only "editable div" and "3 file inputs". V2 adds the
  // composer's attribute names, the element chain up to its form and the labels of the
  // form's buttons (UI labels, never chat text).
  const items = new Set();
  const fold = value => String(value || "").replace(/\d+/g, "#");
  if (composer) {
    const editable = composer.getAttribute && composer.getAttribute("contenteditable");
    items.add("composer:" + String(composer.tagName || "").toLowerCase() + (editable ? ":editable" : ""));
    for (const attr of Array.from(composer.attributes || [])) {
      const name = String(attr.name || "");
      if (name && name !== "style" && name !== "class") items.add("attr:" + fold(name).slice(0, 40));
    }
    const chain = [];
    for (let el = composer.parentElement, depth = 0; el && depth < 8; el = el.parentElement, depth += 1) {
      chain.push(String(el.tagName || "").toLowerCase());
      if (el === form) break;
    }
    items.add("chain:" + chain.join(">"));
  }
  if (form) {
    for (const button of form.querySelectorAll("button")) {
      const label = String((button.getAttribute && button.getAttribute("aria-label")) || "").trim();
      if (label && label.length <= 40) items.add("button:" + fold(label));
    }
    for (const el of form.querySelectorAll("[data-testid]")) {
      items.add("testid:" + String(el.getAttribute("data-testid") || "").replace(/\d+/g, "#").slice(0, 60));
    }
    items.add("file_inputs:" + form.querySelectorAll('input[type="file"]').length);
  }
  const signature = Array.from(items).sort().slice(0, 60);
  return {fingerprint:signature.length ? agpFnv1a(signature.join("|")) : "", signature,
    version:AGP_UI_FINGERPRINT_VERSION};
}

// AGP_DOM_SHAPE_SNAPSHOT_V1 (DOM hardening step 2): the sanitized shape of named page parts —
// tag, role, data-testid, type, short aria-label (<= 60 chars), editable/hidden flags and
// children; never text content. Bounded in nodes and depth; sent with failures after the start.
// AGP_DOM_SHAPE_REPLAY_V2 (step 2 completed, owner 2026-10-07): the shape also keeps what the
// touchpoints decide on, so tests/e2e/dom_replay.js can rebuild the page and replay the real
// probe code: element id and data-id (structural), author role, disabled, href/download present
// (never their values), the Cockpit's own step-file names (e.g. 1475_x.py, 1480_agp_terminal.json —
// identifiers the Cockpit itself issued, never chat text), zero size and display/visibility.
const AGP_DOM_SHAPE_VERSION = 2;
const AGP_STEP_FILE_NAME = /\b\d+_[A-Za-z0-9_.-]*\.(?:py|json)\b/g;

function agpDomShape(roots, maxNodes = 300, maxDepth = 10) {
  let nodes = 0;
  const walk = (el, depth) => {
    if (!el || nodes >= maxNodes) return null;
    nodes += 1;
    const attr = name => (el.getAttribute ? el.getAttribute(name) : null);
    const item = {t:String(el.tagName || "").toLowerCase()};
    const role = attr("role");
    if (role) item.r = String(role).slice(0, 40);
    const testid = attr("data-testid");
    if (testid) item.id = String(testid).slice(0, 60);
    const type = attr("type");
    if (type) item.ty = String(type).slice(0, 20);
    const label = attr("aria-label");
    if (label && String(label).length <= 60) item.l = String(label);
    if (attr("contenteditable")) item.ce = 1;
    const elementId = attr("id");
    if (elementId && String(elementId).length <= 40) item.i = String(elementId);
    const dataId = attr("data-id");
    if (dataId && String(dataId).length <= 20) item.di = String(dataId);
    const author = attr(AGP_SELECTORS.authorRoleAttribute);   // AGP_SELECTOR_TABLE_V1
    if (author) item.a = String(author).slice(0, 20);
    if (el.disabled) item.d = 1;
    if (attr("href") !== null) item.hr = 1;
    if (attr("download") !== null) item.dl = 1;
    if (el.hidden) item.h = 1;
    if (attr("aria-hidden") === "true") item.ah = 1;
    if (attr("inert") !== null) item.in = 1;
    if (typeof el.getBoundingClientRect === "function") {
      const rect = el.getBoundingClientRect();
      if (!(rect.width > 0 && rect.height > 0)) item.z = 1;
    }
    if (typeof getComputedStyle === "function" && el.nodeType === 1) {
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") item.v = 1;
    }
    const own = [attr("download"), attr("title"),
      el.children && el.children.length ? "" : (el.textContent || "")].join(" ");
    const names = String(own).match(AGP_STEP_FILE_NAME);
    if (names) item.f = Array.from(new Set(names)).slice(0, 3).join(" ");
    if (depth < maxDepth && el.children && el.children.length) {
      const kids = [];
      for (const child of el.children) {
        const kid = walk(child, depth + 1);
        if (kid) kids.push(kid);
        if (nodes >= maxNodes) break;
      }
      if (kids.length) item.c = kids;
    }
    return item;
  };
  const shape = {v:AGP_DOM_SHAPE_VERSION};
  for (const [name, el] of Object.entries(roots || {})) shape[name] = el ? walk(el, 0) : null;
  shape.nodes = nodes;
  shape.truncated = nodes >= maxNodes;
  return shape;
}

function agpMissionTouchpointMessage(reason) {
  const texts = {
    composer_not_found: "kein sichtbares ChatGPT-Eingabefeld gefunden. Seite fertig laden lassen oder neu laden, angemeldet sein, dann die Aufgabe erneut starten.",
    composer_form_not_found: "das ChatGPT-Eingabefeld liegt in keinem Formular (Oberfläche geändert?). Bitte Claude melden.",
    selftest_unavailable: "der Selbsttest ist nicht geladen; Erweiterung neu laden.",
    file_input_not_found: "im Formular des ChatGPT-Eingabefelds gibt es keinen aktiven Datei-Upload; Anhänge wären unmöglich. Seite neu laden; bleibt es so, Claude melden."
  };
  const code = "AGP_TOUCHPOINT_" + String(reason || "unknown").toUpperCase();
  return `${code}: Selbsttest vor dem Start: ${texts[reason] || "unbekannter Fehler."} Es wurde nichts eingefügt, angehängt oder gesendet.`;
}

// AGP_PANEL_LIVE_STATUS_V1 (live 2026-10-05): the bridge panel showed
// "0 / 40" and "Aktualisiert 10:25:46" for the whole run although the bridge
// counted turn 1 at 10:27:17; a local step that waits for CI (8 min) showed no
// sign of life either. Pure helpers, used by content.js and tested in node.
function agpMergeLiveMission(current, fresh) {
  // Observational only: take the counters of the same mission, nothing else.
  if (!current || !fresh || !current.mission_id || fresh.mission_id !== current.mission_id) return null;
  return Object.assign({}, current, {
    turn_count: Number(fresh.turn_count || 0),
    step_count: Number(fresh.step_count || 0)
  });
}

function agpMissionPhaseText(phase, nowMs) {
  const since = startedAt => {
    const seconds = Math.max(0, Math.floor((Number(nowMs) - Number(startedAt)) / 1000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  };
  if (!phase) return "";
  if (Number(phase.processingStartedAt) > 0) {
    const file = String(phase.processingFile || "").trim();
    return `${file || "Auftrag"} läuft lokal seit ${since(phase.processingStartedAt)}`;
  }
  if (phase.waitingForAssistant && Number(phase.assistantWaitStartedAt) > 0) {
    return `wartet auf ChatGPT seit ${since(phase.assistantWaitStartedAt)}`;
  }
  return "";
}
