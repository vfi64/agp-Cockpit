// AGP_DOM_SHAPE_REPLAY_V2 (DOM hardening step 2, completed 2026-10-07).
// 1. Round trip: on ChatGPT-like pages, the real probe code decides the same on the original page
//    and on the page rebuilt from its sanitized failure shape — the shape keeps what matters.
// 2. Stored snapshots (tests/browser_fixtures/dom_snapshots/*.json: {source, snapshot, expect}) are
//    replayed against the current probe code; a live failure becomes a regression fixture.
// 3. AGP_DOM_SNAPSHOT=<file> replays one snapshot from the owner's machine and prints the report.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const {shapeToHtml, loadStack, captureShape, probeReport} = require("./dom_replay");

const FIXTURES = path.resolve(__dirname, "../browser_fixtures/dom_snapshots");

const composerForm = ({send = "", stop = false, inputs = 'disabled-none', id = "prompt-textarea"} = {}) => `
  <form class="composer"><div class="row">
    <div class="chips"></div>
    <div ${id ? `id="${id}" ` : ""}contenteditable="true" role="textbox" aria-label="ChatGPT fragen" data-virtualkeyboard="true">SECRET draft text</div>
    <input type="file" multiple style="display:none"${inputs === "disabled" ? " disabled" : ""}>
    <input type="file" multiple accept="image/*" style="display:none"${inputs === "disabled" ? " disabled" : ""}>
    <button type="button" data-testid="composer-plus-btn" aria-label="Dateien hinzufügen">+</button>
    ${send}
    ${stop ? '<button type="button" data-testid="stop-button" aria-label="Streaming stoppen">■</button>' : ""}
  </div></form>`;
const turn = (body, role = "assistant") =>
  `<article data-testid="conversation-turn-3"><div data-message-author-role="${role}" data-message-id="m-${Math.random()}">${body}</div></article>`;
const card = (name, {anchor = false, download = true} = {}) => `<div class="card">
    ${anchor ? `<a href="https://files.example/secret-id" download="${name}"><span>${name}</span></a>`
             : `<button type="button" class="file"><span>${name}</span><span>Code</span></button>`}
    ${download ? '<button type="button" aria-label="Datei herunterladen">↓</button>' : ""}</div>`;

const PAGES = {
  "command card, send button ready": `<main>
    ${turn("<p>SECRET older answer naming 1471_old.py</p>" + card("1471_old.py"))}
    ${turn("<p>SECRET 46s nachgedacht, use 1475_task.py</p>" + card("1475_task.py"))}
    ${composerForm({send:'<button data-testid="send-button" id="composer-submit-button" aria-label="Prompt senden">↑</button>'})}
  </main>`,
  "terminal reply as a link while ChatGPT still streams": `<main>
    ${turn("<p>SECRET prose</p>" + card("1480_agp_terminal.json", {anchor:true, download:false}))}
    ${composerForm({stop:true})}
  </main>`,
  "new chat: no id, labelled submit, file inputs disabled": `<main>
    ${composerForm({id:"", inputs:"disabled", send:'<button type="submit" aria-label="Senden" disabled>↑</button>'})}
  </main>`,
  "card hidden behind an inert dialog layer": `<main>
    ${turn('<div inert>' + card("1482_task.py") + '</div><div aria-hidden="true">' + card("1482_task.py") + "</div>")}
    ${composerForm({send:'<button data-testid="send-button" aria-label="Prompt senden">↑</button>'})}
  </main>`,
};

async function report(page, html) {
  await page.setContent(html.startsWith("<!doctype") ? html : `<!doctype html><html><body>${html}</body></html>`);
  await loadStack(page);
  return probeReport(page);
}

for (const [name, html] of Object.entries(PAGES)) {
  test(`round trip: ${name}`, async ({page}) => {
    const original = await report(page, html);
    const shape = await captureShape(page);
    const serialized = JSON.stringify(shape);
    expect(serialized).not.toContain("SECRET");              // never chat text
    expect(serialized).not.toContain("files.example");       // never a file URL
    const replayed = await report(page, shapeToHtml(shape));
    expect(replayed).toEqual(original);
  });
}

test("the round-trip pages cover the decisions that failed live", async ({page}) => {
  const results = {};
  for (const [name, html] of Object.entries(PAGES)) results[name] = await report(page, html);
  expect(results["command card, send button ready"]).toMatchObject({
    composer:"prompt-textarea", touchpoint:"ok", send_button:"send-button", generation_active:false,
    last_turn_cards:{"1475:command":["1475_task.py +download"]}});
  expect(results["terminal reply as a link while ChatGPT still streams"]).toMatchObject({
    send_button:null, generation_active:true, last_turn_cards:{"1480:terminal":["1480_agp_terminal.json"]}});
  expect(results["new chat: no id, labelled submit, file inputs disabled"]).toMatchObject({
    composer:"div", touchpoint:"file_input_not_found", send_button:null});
  expect(results["card hidden behind an inert dialog layer"].last_turn_cards).toEqual({});
});

const stored = fs.existsSync(FIXTURES) ? fs.readdirSync(FIXTURES).filter(name => name.endsWith(".json")).sort() : [];
for (const name of stored) {
  test(`stored snapshot ${name} replays to its recorded decisions`, async ({page}) => {
    const fixture = JSON.parse(fs.readFileSync(path.join(FIXTURES, name), "utf8"));
    expect(fixture.source, "every stored snapshot names where it came from").toBeTruthy();
    expect(await report(page, shapeToHtml(fixture.snapshot))).toEqual(fixture.expect);
  });
}

test("one snapshot from the owner's machine (AGP_DOM_SNAPSHOT=<file>)", async ({page}) => {
  test.skip(!process.env.AGP_DOM_SNAPSHOT, "set AGP_DOM_SNAPSHOT to replay one stored failure");
  const snapshot = JSON.parse(fs.readFileSync(process.env.AGP_DOM_SNAPSHOT, "utf8"));
  const result = await report(page, shapeToHtml(snapshot));
  console.log("DOM_SNAPSHOT_REPLAY " + JSON.stringify({event:snapshot.event, message:snapshot.message, report:result}));
  test.info().annotations.push({type:"report", description:JSON.stringify(result)});
});
