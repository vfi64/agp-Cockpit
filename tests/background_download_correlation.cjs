const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("chrome_extension/background.js", "utf8");
const filename = "1469_chat_switch_standard_task.py";

function makeContext(storage, downloads) {
  const context = {
    console,
    importScripts() {},
    setTimeout,
    chrome:{
      storage:{session:{
        async get(keys) {
          const result = {};
          for (const key of keys) result[key] = storage[key];
          return result;
        },
        async set(values) {
          Object.assign(storage, values);
        },
      }},
      downloads:{async search() { return downloads.slice(); }},
      runtime:{
        onMessage:{addListener() {}},
        reload() {},
      },
      alarms:{
        create() {},
        onAlarm:{addListener() {}},
      },
      tabs:{
        async query() { return []; },
        async reload() {},
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return context;
}

(async () => {
  const storage = {};
  const oldDownload = {
    id:1,
    filename:`/Users/owner/Downloads/${filename}`,
    state:"complete",
    startTime:new Date(Date.now() - 120_000).toISOString(),
    fileSize:100,
  };
  await makeContext(storage, [oldDownload]).agpArmCommandFileDownload(
    {filename},
    {tab:{id:7}},
  );
  const key = `7:${filename}`;
  assert.deepEqual(Array.from(storage.agpK07DownloadArms[key].knownIds), [1]);

  const staleUnseen = {
    id:2,
    filename:`/Users/owner/Downloads/${filename}`,
    state:"complete",
    startTime:new Date(Date.now() - 60_000).toISOString(),
    fileSize:200,
  };
  const fresh = {
    id:3,
    filename:`/Users/owner/Downloads/${filename}`,
    state:"complete",
    startTime:new Date(Date.now() + 1_000).toISOString(),
    fileSize:4431,
  };
  const restarted = makeContext(storage, [oldDownload, staleUnseen, fresh]);
  const result = await restarted.agpWaitForCommandFileDownload(
    {filename},
    {tab:{id:7}},
  );

  assert.equal(result.download_id, 3);
  assert.equal(result.download_bytes, 4431);
  assert.equal(storage.agpK07DownloadArms[key], undefined);
})().catch(error => {
  console.error(error);
  process.exit(1);
});
