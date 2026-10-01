const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const start = source.indexOf("  function classifyRemoteServiceLimit(");
const end = source.indexOf("\n  async function tick()", start);
assert.notEqual(start, -1);
assert.notEqual(end, -1);

const context = {
  normalizeObservedMessageText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

assert.equal(
  context.classifyRemoteServiceLimit(
    "Du hast dein Nutzungslimit erreicht. Alternativ kannst du es ab 17:35 erneut versuchen."
  ).reset_at,
  "17:35",
);
assert.equal(
  context.classifyRemoteServiceLimit("Your Work usage is temporarily exhausted.").code,
  "CHATGPT_USAGE_LIMIT",
);
assert.equal(
  context.classifyRemoteServiceLimit("The handoff finished with status PASS."),
  null,
);
