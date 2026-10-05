// AGP_MISSION_TOUCHPOINT_SELFTEST_V1 (Slice C, 2026-10-05): the mission start
// checks composer, composer form and an enabled file input in that form before
// it touches the page. Fixtures: the r6 start page (three forms, two 0x0) and
// the three failure shapes.
const { test, expect } = require("@playwright/test");
const path = require("path");

const EVIDENCE = path.resolve(__dirname, "../../chrome_extension/native_message_evidence.js");

function composerForm(index, {hidden = false, fileInputs = 1, disabledInputs = false} = {}) {
  const box = hidden ? 'style="width:0;height:0;overflow:hidden;display:flex"' : 'style="display:flex"';
  const inputs = Array.from({length: fileInputs}, () => `<input type="file"${disabledInputs ? " disabled" : ""}>`).join("");
  return `<form id="form-${index}" ${box}>
    <div contenteditable="true" role="textbox" id="editor-${index}" style="min-height:24px;width:400px;flex-shrink:0"></div>
    ${inputs}
  </form>`;
}

async function check(page, body) {
  await page.setContent(`<!doctype html><html><body><main>${body}</main></body></html>`);
  await page.addScriptTag({path: EVIDENCE});
  return page.evaluate(() => {
    const result = agpMissionTouchpointCheck(agpResolveComposer);
    return Object.assign(result, {message: result.ok ? "" : agpMissionTouchpointMessage(result.reason)});
  });
}

test("r6 start page: the visible third form passes with its own file inputs", async ({page}) => {
  const result = await check(page,
    composerForm(0, {hidden: true, fileInputs: 3}) +
    composerForm(1, {hidden: true, fileInputs: 3, disabledInputs: true}) +
    composerForm(2, {fileInputs: 3}));
  expect(result.ok).toBe(true);
  expect(result.reason).toBe("");
  expect(result.snapshot).toMatchObject({
    forms: 3, visible_forms: 1, composer_found: true, composer_id: "editor-2",
    composer_form_index: 2, file_inputs_in_form: 3, enabled_file_inputs_in_form: 3
  });
});

test("no visible composer fails with composer_not_found", async ({page}) => {
  const result = await check(page, composerForm(0, {hidden: true}));
  expect(result.ok).toBe(false);
  expect(result.reason).toBe("composer_not_found");
  expect(result.message).toContain("AGP_TOUCHPOINT_COMPOSER_NOT_FOUND");
  expect(result.message).toContain("nichts eingefügt, angehängt oder gesendet");
});

test("a composer outside any form fails with composer_form_not_found", async ({page}) => {
  const result = await check(page,
    '<div contenteditable="true" role="textbox" id="loose" style="min-height:24px;width:400px"></div><input type="file">');
  expect(result.reason).toBe("composer_form_not_found");
  expect(result.snapshot.composer_id).toBe("loose");
});

test("a composer form with only disabled file inputs fails with file_input_not_found", async ({page}) => {
  const result = await check(page, composerForm(0, {fileInputs: 2, disabledInputs: true}));
  expect(result.reason).toBe("file_input_not_found");
  expect(result.snapshot).toMatchObject({file_inputs_in_form: 2, enabled_file_inputs_in_form: 0});
  expect(result.message).toContain("AGP_TOUCHPOINT_FILE_INPUT_NOT_FOUND");
});

test("a file input elsewhere in the document does not satisfy the check", async ({page}) => {
  const result = await check(page, composerForm(0, {fileInputs: 0}) + '<form><input type="file"></form>');
  expect(result.reason).toBe("file_input_not_found");
});
