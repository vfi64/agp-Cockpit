// AGP_UI_FINGERPRINT_V1 and AGP_DOM_SHAPE_SNAPSHOT_V1: the pure helpers of
// native_message_evidence.js on a minimal fake DOM — structure only, never text.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function el(tag, attrs = {}, children = [], text = "") {
  const node = {
    tagName: tag.toUpperCase(), children, hidden: false, textContent: text, innerText: text,
    getAttribute: name => (name in attrs ? attrs[name] : null),
    attributes: Object.keys(attrs).map(name => ({name, value: attrs[name]})),
    parentElement: null,
  };
  for (const child of children) child.parentElement = node;
  const all = () => children.flatMap(child => [child, ...child._all()]);
  node._all = all;
  node.querySelectorAll = selector => all().filter(child => {
    if (selector === "[data-testid]") return child.getAttribute("data-testid") !== null;
    if (selector === 'input[type="file"]') return child.tagName === "INPUT" && child.getAttribute("type") === "file";
    if (selector === "button") return child.tagName === "BUTTON";
    return false;
  });
  return node;
}

const context = vm.createContext({});
vm.runInContext(fs.readFileSync("chrome_extension/chatgpt_selectors.js", "utf8"), context);   // AGP_SELECTOR_TABLE_V1
vm.runInContext(fs.readFileSync("chrome_extension/native_message_evidence.js", "utf8"), context);
const fingerprint = vm.runInContext("agpUiFingerprint", context);
const shape = vm.runInContext("agpDomShape", context);

const composer = el("div", {contenteditable: "true", class: "x1 y2", "data-virtualkeyboard": "true"}, [],
                   "SECRET PROMPT TEXT");
const form = el("form", {}, [
  el("div", {}, [composer]),
  el("button", {"data-testid": "composer-plus-btn", "aria-label": "Dateien hinzufügen"}),
  el("input", {type: "file"}), el("input", {type: "file"}),
  el("div", {"data-testid": "model-switcher-42"}),
]);

// 1. Stable, text-free, digit-folded fingerprint.
const a = fingerprint(composer, form);
assert.match(a.fingerprint, /^[0-9a-f]{8}$/);
const plain = value => JSON.parse(JSON.stringify(value));   // the vm realm has its own Array
assert.deepEqual(plain(a.signature), [
  "attr:contenteditable", "attr:data-virtualkeyboard", "button:Dateien hinzufügen", "chain:div>form",
  "composer:div:editable", "file_inputs:2", "testid:composer-plus-btn", "testid:model-switcher-#"]);
assert.equal(fingerprint(composer, form).fingerprint, a.fingerprint);
assert.ok(!JSON.stringify(a).includes("SECRET"));
// 2. A new control in the form is a new variant; the class attribute (hashed names) is not part of it.
form.children.push(el("button", {"data-testid": "send-button"}));
assert.notEqual(fingerprint(composer, form).fingerprint, a.fingerprint);
assert.deepEqual(plain(fingerprint(null, null)), {fingerprint: "", signature: [], version: 2});   // AGP_UI_FINGERPRINT_VERSIONED_V1

// 3. The shape keeps structure and short labels, never text, and is bounded.
const turn = el("article", {"data-message-author-role": "assistant", role: "article"}, [
  el("p", {}, [], "assistant answer text"),
  el("button", {"aria-label": "Vorschau von 1862_agp_terminal.json öffnen"}),
  el("button", {"aria-label": "x".repeat(61)}),
]);
const s = shape({composer_form: form, last_assistant: turn, missing: null});
assert.equal(s.composer_form.t, "form");
assert.equal(s.composer_form.c[0].c[0].ce, 1);
assert.equal(s.composer_form.c[1].id, "composer-plus-btn");
assert.equal(s.last_assistant.r, "article");
assert.equal(s.last_assistant.c[1].l, "Vorschau von 1862_agp_terminal.json öffnen");
assert.equal(s.last_assistant.c[2].l, undefined);           // long labels are dropped
assert.equal(s.missing, null);
assert.ok(!JSON.stringify(s).includes("SECRET") && !JSON.stringify(s).includes("answer text"));
assert.equal(s.truncated, false);
const big = el("div", {}, Array.from({length: 50}, () => el("span")));
const bounded = shape({big}, 10);
assert.equal(bounded.nodes, 10);
assert.equal(bounded.truncated, true);
// 4. AGP_DOM_SHAPE_REPLAY_V2: what the touchpoints decide on, still without chat text or URLs.
const card = el("a", {href: "https://files.example/secret-file-id", download: "1475_task.py"}, [], "1475_task.py Code");
const prose = el("p", {}, [], "SECRET prose naming 1474_old.py");
const sendOff = el("button", {"data-testid": "send-button", id: "composer-submit-button"});
sendOff.disabled = true;
const turn2 = el("article", {"data-message-author-role": "assistant"}, [prose, card]);
const form2 = el("form", {}, [el("div", {id: "prompt-textarea", contenteditable: "true", "data-id": "root"}), sendOff]);
const s2 = shape({composer_form: form2, last_assistant: turn2});
assert.equal(s2.v, 2);
assert.equal(s2.last_assistant.a, "assistant");
assert.deepEqual([s2.last_assistant.c[1].hr, s2.last_assistant.c[1].dl, s2.last_assistant.c[1].f], [1, 1, "1475_task.py"]);
assert.equal(s2.last_assistant.c[0].f, "1474_old.py");
assert.deepEqual([s2.composer_form.c[0].i, s2.composer_form.c[0].di, s2.composer_form.c[1].d], ["prompt-textarea", "root", 1]);
const text2 = JSON.stringify(s2);
assert.ok(!text2.includes("SECRET") && !text2.includes("files.example") && !text2.includes("Code"));
console.log("dom_observe_browser: PASS");
