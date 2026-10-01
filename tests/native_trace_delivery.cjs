// Behavioral proof: native-transport traces from the service worker must be
// addressed to the originating tab. chrome.runtime.sendMessage from a service
// worker never reaches content scripts, so it is not an acceptable sink.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("chrome_extension/background.js", "utf8");
const tabMessages = [];
const runtimeMessages = [];
const context = {
  console,
  importScripts() {},
  setTimeout,
  chrome:{
    storage:{session:{async get() { return {}; }, async set() {}}},
    downloads:{async search() { return []; }},
    runtime:{
      onMessage:{addListener() {}},
      async sendMessage(message) { runtimeMessages.push(message); },
      reload() {},
    },
    alarms:{create() {}, onAlarm:{addListener() {}}},
    tabs:{
      async query() { return []; },
      async reload() {},
      async sendMessage(tabId, message) { tabMessages.push({tabId, message}); },
    },
  },
};
vm.createContext(context);
vm.runInContext(source, context);

(async () => {
  await context.agpK07NativeTrace1165(42, {event:"COMMIT_FAILURE", request_id:"r1"});
  assert.equal(tabMessages.length, 1);
  assert.equal(tabMessages[0].tabId, 42);
  assert.equal(tabMessages[0].message.type, "AGP_K07_NATIVE_TRACE_1165");
  assert.equal(tabMessages[0].message.payload.event, "COMMIT_FAILURE");
  assert.equal(runtimeMessages.length, 0, "runtime.sendMessage cannot reach content scripts");
  await context.agpK07NativeTrace1165(null, {event:"COMMIT_FAILURE"});
  assert.equal(tabMessages.length, 1, "a trace without tab identity is dropped, not broadcast");
  console.log("native trace delivery ok");
})().catch(error => {
  console.error(error);
  process.exit(1);
});
