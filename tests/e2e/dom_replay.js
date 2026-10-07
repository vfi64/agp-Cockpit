// AGP_DOM_SHAPE_REPLAY_V2 (DOM hardening step 2, completed 2026-10-07): replay a sanitized page
// shape (agpDomShape, stored by the bridge in .local/agp-cockpit/browser/dom-snapshots) against
// the real probe code. shapeToHtml rebuilds the captured parts — the composer form and the last
// assistant turn — with the attributes the touchpoints decide on; probeReport runs the real
// resolver, touchpoint self-test and page adapter on it. Used by
// test_dom_snapshot_replay.spec.js (round trip and stored regression snapshots).
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const STACK = ["chatgpt_selectors.js", "native_message_evidence.js", "chatgpt_dom.js"]
  .map(name => fs.readFileSync(path.join(ROOT, "chrome_extension", name), "utf8"));
const VOID = new Set(["input", "img", "br", "hr", "meta", "link", "source", "wbr"]);
const CSS = `body{margin:0;font:14px sans-serif}
button,a,[role=button]{display:inline-block;min-width:12px;min-height:12px}
[contenteditable]{display:block;min-width:200px;min-height:24px}`;

const escape = value => String(value).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

function nodeHtml(item) {
  if (!item || typeof item !== "object") return "";
  const tag = /^[a-z][a-z0-9-]*$/.test(String(item.t || "")) ? item.t : "div";
  const attrs = [];
  const add = (name, value = "") => attrs.push(value === "" ? ` ${name}` : ` ${name}="${escape(value)}"`);
  if (item.r) add("role", item.r);
  if (item.id) add("data-testid", item.id);
  if (item.ty) add("type", item.ty);
  if (item.l) add("aria-label", item.l);
  if (item.ce) add("contenteditable", "true");
  if (item.i) add("id", item.i);
  if (item.di) add("data-id", item.di);
  if (item.a) add("data-message-author-role", item.a);
  if (item.d) add("disabled");
  if (item.hr) add("href", "#replay");
  if (item.dl) add("download", item.f ? item.f.split(" ")[0] : "file");
  if (item.h) add("hidden");
  if (item.ah) add("aria-hidden", "true");
  if (item.in) add("inert");
  const style = [];
  if (item.z) style.push("width:0;height:0;min-width:0;min-height:0;padding:0;border:0;overflow:hidden");
  if (item.v) style.push("display:none");
  if (style.length) add("style", style.join(";"));
  const open = `<${tag}${attrs.join("")}>`;
  if (VOID.has(tag)) return open;
  const children = Array.isArray(item.c) ? item.c.map(nodeHtml).join("") : "";
  const text = !Array.isArray(item.c) && item.f ? escape(item.f) : "";
  return `${open}${text}${children}</${tag}>`;
}

/** A stored snapshot file ({event, shape, …}) or a bare shape → a replay page. */
function shapeToHtml(snapshot) {
  const shape = snapshot && snapshot.shape ? snapshot.shape : snapshot;
  return `<!doctype html><html><head><style>${CSS}</style></head><body><main>` +
    `<section>${nodeHtml(shape.last_assistant)}</section>${nodeHtml(shape.composer_form)}` +
    `</main></body></html>`;
}

async function loadStack(page) {
  for (const source of STACK) await page.addScriptTag({content:source});
}

/** The failure snapshot exactly as content.js failureDomShape() takes it. */
function captureShape(page) {
  return page.evaluate(() => {
    const composer = agpResolveComposer();
    const form = composer && composer.closest ? composer.closest("form") : null;
    const turns = AGP_DOM.assistantTurns();
    return agpDomShape({composer_form:form, last_assistant:turns.length ? turns[turns.length - 1] : null});
  });
}

/** What the real probe code decides on this page. */
function probeReport(page) {
  return page.evaluate(() => {
    const composer = agpResolveComposer();
    const form = composer && composer.closest ? composer.closest("form") : null;
    const send = AGP_DOM.sendButton(composer);
    const turns = AGP_DOM.assistantTurns();
    const last = turns.length ? turns[turns.length - 1] : null;
    const steps = new Set();
    for (const anchor of document.querySelectorAll(AGP_SELECTORS.fileCardCandidate)) {
      const match = String(AGP_DOM.fileCardRow(anchor).name || "").match(/^(\d+)_/);
      if (match) steps.add(Number(match[1]));
    }
    const cards = {};
    for (const step of Array.from(steps).sort((a, b) => a - b)) {
      for (const kind of ["command", "terminal"]) {
        const found = AGP_DOM.stepFileCards(step, kind)
          .filter(item => last && last.contains(item.node))
          .map(item => item.name + (item.downloadNode ? " +download" : ""));
        if (found.length) cards[`${step}:${kind}`] = found;
      }
    }
    const touch = agpMissionTouchpointCheck(agpResolveComposer);
    return {
      composer:composer ? (composer.id || composer.tagName.toLowerCase()) : null,
      composer_in_form:Boolean(form),
      touchpoint:touch.ok ? "ok" : touch.reason,
      send_button:send ? String(send.getAttribute("data-testid") || send.getAttribute("aria-label") || "button") : null,
      generation_active:AGP_DOM.generationActive(),
      last_turn_cards:cards,
    };
  });
}

module.exports = {shapeToHtml, loadStack, captureShape, probeReport};
