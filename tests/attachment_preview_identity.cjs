const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const start = source.indexOf("  function assistantAttachmentKey");
const end = source.indexOf("  async function fetchSingleAssistantPythonAttachment", start);
const code = source.slice(start, end);
// AGP_SELECTOR_TABLE_V1: the selector table loads first, as in the manifest.
const ADAPTER = fs.readFileSync("chrome_extension/chatgpt_selectors.js", "utf8") + "\n" +
  fs.readFileSync("chrome_extension/chatgpt_dom.js", "utf8");

function node({label="", text="", closest=null, buttons=[], parentElement=null, click=null}={}) {
  return {
    innerText:text,
    textContent:text,
    parentElement,
    isConnected:true,
    tagName:"BUTTON",
    getAttribute(name) { return name === "aria-label" ? label : ""; },
    closest() { return closest; },
    querySelectorAll() { return buttons; },
    click() { if (click) click(); },
  };
}

for (const step of [1469, 1470, 1523]) {
  const filename = `${step}_chat_switch_standard_task.py`;
  const composer = node({label:"ChatGPT fragen", text:"unrelated"});
  const preview = node({label:filename, text:"#!/usr/bin/env python3\nprint('ok')"});
  const context = {
    STATE:{mission:{mission_id:"mission-a"}, runGeneration:7},
    document:{querySelectorAll:() => [composer, preview]},
    lastAssistantMessageId:() => `assistant-${step}`,
    lastAssistantText:() => filename,
    normalizeObservedMessageText:value => String(value || "").trim(),
  };
  vm.createContext(context);
  vm.runInContext(ADAPTER, context);   // AGP_DOM_ADAPTER_V1
  vm.runInContext(code, context);

  assert.equal(context.readableAttachmentPreview(filename), preview);
  const key = context.assistantAttachmentKey([{name:filename, href:""}]);
  assert.match(key, /^mission-a\n7\n/);
  assert.ok(key.includes(filename));
}

const close = node({label:"Schließen"});
const download = node({label:"Herunterladen"});
const shell = node({buttons:[close, download]});
const preview = node({parentElement:shell});
const context = {
  STATE:{mission:null, runGeneration:1},
  document:{querySelectorAll:() => []},
  lastAssistantMessageId:() => "",
  lastAssistantText:() => "",
  normalizeObservedMessageText:value => String(value || ""),
};
vm.createContext(context);
vm.runInContext(ADAPTER, context);   // AGP_DOM_ADAPTER_V1
  vm.runInContext(code, context);
assert.equal(context.attachmentPreviewContainer(preview), shell);

(async () => {
  const filename = "1469_chat_switch_standard_task.py";
  const truncated = "def main():\n    BRIEF.write_text('partial')\n";
  const complete = `${truncated}    BUNDLE.write_text('{}')\nif __name__=='__main__': raise SystemExit(main())\n`;
  const events = [];
  const clicks = [];
  const downloadNode = node({label:"Download", click:() => clicks.push("download")});
  const fileButton = node({label:filename});
  const context = {
    STATE:{mission:{mission_id:"mission-b"}, runGeneration:8},
    document:{querySelectorAll:() => [node({label:filename, text:truncated})]},
    window:{focus() {}},
    composer:() => node({label:"ChatGPT fragen", text:""}),
    lastAssistantMessageId:() => "assistant-download",
    lastAssistantText:() => filename,
    normalizeObservedMessageText:value => String(value || "").trim(),
    chrome:{runtime:{sendMessage:async message => {
      if (message.type === "AGP_K07_ARM_COMMAND_FILE_DOWNLOAD") {
        return {ok:true, stage:"COMMAND_FILE_DOWNLOAD_ARMED", filename};
      }
      if (message.type === "AGP_K07_WAIT_COMMAND_FILE_DOWNLOAD") {
        return {
          ok:true,
          stage:"COMMAND_FILE_DOWNLOADED",
          filename,
          download_path:`/Users/hof/Downloads/${filename}`,
          download_id:42,
          download_bytes:complete.length,
        };
      }
      throw new Error(`unexpected message ${message.type}`);
    }}},
    api:async (url, options) => {
      assert.equal(url, "/v1/file-loop/download");
      const body = JSON.parse(options.body);
      assert.equal(body.filename, filename);
      assert.equal(body.download_path, `/Users/hof/Downloads/${filename}`);
      return {ok:true, stage:"COMMAND_FILE_FETCHED", filename, content:complete, content_type:"text/x-python",
        bytes:Buffer.byteLength(complete, "utf8"), sha256:"bridge-sha"};
    },
    clientEvent:async (name, payload) => events.push({name, payload}),
  };
  vm.createContext(context);
  vm.runInContext(ADAPTER, context);   // AGP_DOM_ADAPTER_V1
  vm.runInContext(code, context);
  const result = await context.readAssistantButtonAttachment({
    node:fileButton,
    name:filename,
    href:"",
    downloadNode,
  });
  assert.equal(result.content, complete);
  assert.notEqual(result.content, truncated);
  assert.deepEqual(clicks, ["download"]);
  assert.equal(events.at(-1).name, "K07_ATTACHMENT_DOWNLOAD_USED");
})().catch(error => {
  console.error(error);
  process.exit(1);
});
