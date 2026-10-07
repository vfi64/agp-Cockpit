// AGP_PROBE_TEMPLATE_ESCAPES_V1: the send-readiness probe is a template
// literal handed to Runtime.evaluate. This suite cooks the actual template
// from background.js exactly as Chrome receives it and runs it against the
// live DOM of step 1598 (2026-10-02): enabled "Senden" submit button in the
// composer form, no data-testid, hit test on a foreign DIV.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/background.js", "utf8");
// AGP_SELECTOR_TABLE_V1: agpPageExpression() gives every evaluated template this table.
require("../chrome_extension/chatgpt_selectors.js");
const AGP_SELECTORS = globalThis.AGP_SELECTORS;

function templates(text) {
  const out = [];
  const re = /evaluate\(`((?:[^`\\]|\\.)*)`\)/gs;
  let m;
  while ((m = re.exec(text))) out.push({body:m[1], index:m.index});
  return out;
}

// 1. No single backslash in any evaluated template except before \ ` $ or
//    an interpolation: anything else is cooked away silently.
for (const t of templates(source)) {
  const bad = /(?<!\\)(?:\\\\)*\\([^\\`$])/g;
  let k;
  while ((k = bad.exec(t.body))) {
    const line = source.slice(0, t.index).split("\n").length;
    assert.fail(`single backslash escape "\\${k[1]}" in evaluate template near line ${line}`);
  }
}

// 2. The readiness probe itself, cooked, against the live 1598 DOM.
const probeTemplate = templates(source).find(t => t.body.includes("AGP_SEND_CONTROL_SEMANTIC_V1"));
assert.ok(probeTemplate, "probe template not found");
assert.ok(!probeTemplate.body.includes("${"), "probe template must not interpolate");
const cooked = vm.runInNewContext("`" + probeTemplate.body + "`");
assert.ok(cooked.includes("/^(send|senden)\\b/i"), "cooked regex must keep \\b");

function probe(button) {
  const div = {tagName:"DIV", getAttribute:() => null};
  const document = {
    querySelectorAll:(selector) => {
      if (selector === 'button[data-testid="send-button"]') return button.attrs["data-testid"] === "send-button" ? [button] : [];
      if (selector.startsWith("button[aria-label*=")) {
        const needle = selector.match(/"(.*)"/)[1];
        return (button.attrs["aria-label"] || "").includes(needle) ? [button] : [];
      }
      if (selector === 'form button[type="submit"]') return button.inForm && button.attrs.type === "submit" ? [button] : [];
      return [];
    },
    elementFromPoint:() => div,
  };
  const context = {AGP_SELECTORS, document, getComputedStyle:() => ({visibility:"visible", display:"block", pointerEvents:"auto"})};
  return vm.runInNewContext(cooked, context);
}

function button(attrs, {disabled = false, inForm = true} = {}) {
  return {
    attrs, inForm, disabled, tagName:"BUTTON",
    getAttribute:(name) => (name in attrs ? attrs[name] : null),
    getBoundingClientRect:() => ({left:1000, top:770, width:36, height:36}),
    contains:() => false,
    closest:(sel) => (sel === "form" && inForm ? {} : null),
  };
}

let r = probe(button({"aria-label":"Senden", type:"submit"}));
assert.equal(r.found, true, "live 1598 send control must be ready");
assert.equal(r.target.aria_label, "Senden");
r = probe(button({"aria-label":"Send prompt", type:"submit"}));
assert.equal(r.found, true);
r = probe(button({"aria-label":"Senden", type:"submit"}, {disabled:true}));
assert.equal(r.found, false, "disabled stays not ready");
r = probe(button({"aria-label":"Senden", type:"submit"}, {inForm:false}));
assert.equal(r.found, false, "outside the composer form stays not ready");
r = probe(button({"aria-label":"Sendung stoppen", type:"submit"}));
assert.equal(r.found, false, "label must start with the word Send/Senden");
console.log("send_probe_template: ok");
