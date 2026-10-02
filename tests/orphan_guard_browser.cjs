// AGP_ORPHANED_CONTENT_SCRIPT_GUARD_V1: an orphaned content script retires itself.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const start = source.indexOf("  let AGP_ORPHANED = false;");
const end = source.indexOf("    return true;\n  }\n", start) + "    return true;\n  }\n".length;
const code = source.slice(start, end);

function run(runtime) {
  const cleared = [];
  let removed = false;
  const context = {
    STATE:{running:true, timer:11}, AGP_TASK_FIRST_START_REQUEST_TIMER:12,
    chrome:{runtime},
    clearInterval:id => cleared.push(id),
    document:{getElementById:id => (id === "agp-cockpit-bridge" ? {remove:() => { removed = true; }} : null)},
  };
  vm.createContext(context);
  vm.runInContext(code + "\nAGP_HANDSHAKE_TIMER = 13;\nresult = [retireIfOrphaned(), retireIfOrphaned()];", context);
  return {result:Array.from(context.result), cleared, removed, running:context.STATE.running};
}

const alive = run({id:"ext"});
assert.deepEqual(alive.result, [false, false]);
assert.deepEqual(alive.cleared, []);
assert.equal(alive.running, true);

const orphan = run({});
assert.deepEqual(orphan.result, [true, true]);
assert.deepEqual(orphan.cleared, [11, 12, 13]);       // once, not again on the second call
assert.equal(orphan.removed, true);
assert.equal(orphan.running, false);

const throwing = run(Object.defineProperty({}, "id", {get() { throw new Error("Extension context invalidated."); }}));
assert.deepEqual(throwing.result, [true, true]);
console.log("ok");
