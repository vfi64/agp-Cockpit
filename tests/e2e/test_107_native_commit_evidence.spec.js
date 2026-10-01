const {test, expect} = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const extension = path.resolve(__dirname, '../../chrome_extension');

async function runNative(page, {prompt, existing = false, submit = true, altered = false, roleless = false, collapseChars = null, renderedText = null}) {
  await page.setContent('<main><textarea id="prompt-textarea"></textarea><button data-testid="send-button">Send</button></main>');
  const addMessage = async (id) => page.evaluate(({prompt, id, altered, roleless, collapseChars, renderedText}) => {
    let bodyText = renderedText === null
      ? (altered ? prompt.replace(/s/g, '') : prompt.replace(/ /g, '\u00a0'))
      : renderedText;
    if (Number.isInteger(collapseChars)) bodyText = bodyText.slice(0, collapseChars);
    const node = document.createElement('section');
    node.dataset.messageId = id;
    if (roleless) {
      const heading = document.createElement('h5');
      heading.textContent = 'Du hast gesagt:';
      const body = document.createElement('div');
      body.textContent = bodyText;
      const assistant = document.createElement('h5');
      assistant.textContent = 'ChatGPT hat gesagt:';
      node.append(heading, body, assistant);
    } else {
      node.dataset.messageAuthorRole = 'user';
      const body = document.createElement('div');
      body.dataset.testid = 'collapsible-user-message-content';
      body.textContent = bodyText;
      const toggle = document.createElement('button');
      toggle.textContent = 'Mehr anzeigen';
      node.append(body, toggle);
    }
    document.querySelector('main').append(node);
  }, {prompt, id, altered, roleless, collapseChars, renderedText});
  if (existing) await addMessage('old-turn');
  await page.locator('#prompt-textarea').focus();
  const events = [];
  let submitted = false;
  let detached = false;
  const context = vm.createContext({
    setTimeout: fn => setTimeout(fn, 0),
    chrome: {
      runtime: {onMessage: {addListener() {}}},
      alarms: {onAlarm: {addListener() {}}},
      debugger: {
        attach: async () => {},
        detach: async () => { detached = true; },
        sendCommand: async (_target, method, params = {}) => {
          if (method === 'Runtime.evaluate') return {result: {value: await page.evaluate(params.expression)}};
          if (method === 'Input.insertText') await page.locator('#prompt-textarea').fill(params.text);
          if (method === 'Input.dispatchKeyEvent' || method === 'Input.dispatchMouseEvent') {
            events.push(params);
            if (!submitted && submit) {
              submitted = true;
              await addMessage('new-turn');
              await page.locator('#prompt-textarea').fill('');
            }
          }
          return {};
        }
      }
    }
  });
  context.importScripts = name => vm.runInContext(fs.readFileSync(path.join(extension, name), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(extension, 'background.js'), 'utf8'), context);
  const result = await context.agpNativeTransportV1({request_id:'regression-107', text:prompt, operation:'insert_and_submit'}, {tab:{id:17}});
  return {result, events, detached};
}

test('native commit keeps s characters and normalizes real whitespace without toggle labels', async ({page}) => {
  const {result, detached, events} = await runNative(page, {prompt:'mission status\n\nSteps: tests passed'});
  expect(result.stage).toBe('USER_TURN_COMMITTED');
  expect(result.commit.latest_user_message).toBe('mission status Steps: tests passed');
  expect(detached).toBe(true);
  expect(events.filter(event => event.type === 'keyDown')).toHaveLength(1);
  expect(events[0].text).toBe('\r');
});

test('old identical user message cannot confirm a new unsent request', async ({page}) => {
  const {result} = await runNative(page, {prompt:'mission status', existing:true, submit:false});
  expect(result.stage).toBe('USER_TURN_NOT_COMMITTED');
});

test('a new different message cannot confirm the requested text', async ({page}) => {
  const {result} = await runNative(page, {prompt:'mission status', altered:true});
  expect(result.stage).toBe('USER_TURN_INDETERMINATE');
});

test('a new identical message is distinct from the old turn', async ({page}) => {
  const {result} = await runNative(page, {prompt:'mission status', existing:true});
  expect(result.stage).toBe('USER_TURN_COMMITTED');
  expect(result.commit.exact_user_message_index).toBe(1);
});

test('native commit accepts visible heading-labelled user turns without role attributes', async ({page}) => {
  const {result} = await runNative(page, {prompt:'mission status', roleless:true});
  expect(result.stage).toBe('USER_TURN_COMMITTED');
  expect(result.commit.latest_user_message).toBe('mission status');
});

test('native commit accepts a new long collapsed-prefix user turn', async ({page}) => {
  const prompt = 'AGP mission bootstrap '.repeat(24) + 'FINAL HASH c385efa5346c04ec8a917a2a8f978c5226c55d3a23f42192c957eb111ea0db5b';
  const {result} = await runNative(page, {prompt, collapseChars:320});
  expect(result.stage).toBe('USER_TURN_COMMITTED');
  expect(result.commit.latest_user_message.length).toBeGreaterThanOrEqual(240);
  expect(result.commit.latest_user_message).toBe(prompt.slice(0, 320).trim());
});

test('native commit accepts a new long rendered projection with the same start', async ({page}) => {
  const prompt = 'AGP mission bootstrap '.repeat(24) +
    'source_manifest.json successor_prompt.md ' +
    'agentic-kit transfer chat-switch-complete --json '.repeat(8) +
    'FINAL HASH c385efa5346c04ec8a917a2a8f978c5226c55d3a23f42192c957eb111ea0db5b';
  const renderedText = prompt.slice(0, 320) + ' renderer skipped a middle segment';
  const {result} = await runNative(page, {prompt, renderedText});
  expect(result.stage).toBe('USER_TURN_COMMITTED');
  expect(result.commit.latest_user_message).toBe(renderedText.replace(/\s+/g, ' ').trim());
});

test('native commit rejects an old long rendered projection without a new turn', async ({page}) => {
  const prompt = 'AGP mission bootstrap '.repeat(24) +
    'source_manifest.json successor_prompt.md ' +
    'agentic-kit transfer chat-switch-complete --json '.repeat(8) +
    'FINAL HASH c385efa5346c04ec8a917a2a8f978c5226c55d3a23f42192c957eb111ea0db5b';
  const renderedText = prompt.slice(0, 320) + ' renderer skipped a middle segment';
  const {result} = await runNative(page, {prompt, existing:true, submit:false, renderedText});
  expect(result.stage).toBe('USER_TURN_NOT_COMMITTED');
});

test('native commit rejects a too-short collapsed-prefix user turn', async ({page}) => {
  const prompt = 'AGP mission bootstrap '.repeat(24) + 'FINAL HASH c385efa5346c04ec8a917a2a8f978c5226c55d3a23f42192c957eb111ea0db5b';
  const {result} = await runNative(page, {prompt, collapseChars:120});
  expect(result.stage).toBe('USER_TURN_INDETERMINATE');
});

for (const html of [
  'mission status<br>Steps: tests passed',
  '<p>mission status</p><p>Steps: tests passed</p>',
  '<div><span>mission </span><strong>status</strong></div><div>Steps: <em>tests passed</em></div>',
  '<pre>mission\tstatus\nSteps: tests passed</pre>',
  '<div data-testid="collapsible-user-message-content"><p>mission status</p><p>Steps: tests passed</p></div><button>Show more</button>',
  '<div data-testid="collapsible-user-message-content">mission&nbsp;status\nSteps: tests passed</div><button>Mehr anzeigen</button>',
  '<div>mission status<br>Steps: tests passed</div><span role="button">Copy</span>'
]) {
  test('message formatting variant: ' + html.slice(0,55), async ({page}) => {
    await page.setContent('<div data-message-author-role="user">' + html + '</div>');
    await page.addScriptTag({path:path.join(extension, 'native_message_evidence.js')});
    const result = await page.evaluate(() => agpNativeMessageSnapshot());
    expect(result.messages[0].text).toBe('mission status Steps: tests passed');
  });
}

test('user-turn evidence accepts current conversation-turn test-id wrappers', async ({page}) => {
  await page.setContent(
    '<article data-testid="conversation-turn-user-42">' +
    '<div><p>mission&nbsp;status</p><p>Steps: tests passed</p></div>' +
    '<button>Mehr anzeigen</button></article>'
  );
  await page.addScriptTag({path:path.join(extension, 'native_message_evidence.js')});
  const result = await page.evaluate(() => agpNativeMessageSnapshot());
  expect(result.user_message_count).toBe(1);
  expect(result.messages[0].text).toBe('mission status Steps: tests passed');
});

test('user-turn evidence accepts visible localized author-heading layout', async ({page}) => {
  await page.setContent(
    '<main>' +
    '<section><h5>Du hast gesagt:</h5>' +
    '<div><p>mission&nbsp;status</p><p>Steps: tests passed</p><button>Nachricht kopieren</button></div>' +
    '<h5>ChatGPT hat gesagt:</h5><div>assistant reply</div></section>' +
    '<section><h5>You said:</h5>' +
    '<div><p>next mission</p><p>Step 1472</p><button>Copy message</button></div>' +
    '<h5>ChatGPT said:</h5><div>next assistant</div></section>' +
    '</main>'
  );
  await page.addScriptTag({path:path.join(extension, 'native_message_evidence.js')});
  const result = await page.evaluate(() => agpNativeMessageSnapshot());
  expect(result.user_message_count).toBe(2);
  expect(result.messages.map(message => message.text)).toEqual([
    'mission status Steps: tests passed',
    'next mission Step 1472'
  ]);
});

test('user-turn evidence matches rendered Markdown to the raw prompt', async ({page}) => {
  await page.setContent(
    '<article data-message-author-role="user">' +
    '<div data-testid="collapsible-user-message-content">' +
    'Use <code>agentic-kit transfer chat-switch-complete --json</code>.' +
    '<p>- execution_contract.json</p>' +
    '</div></article>'
  );
  await page.addScriptTag({path:path.join(extension, 'native_message_evidence.js')});
  const result = await page.evaluate(() => agpNativeMessageSnapshot());
  const rawPrompt = 'Use `agentic-kit transfer chat-switch-complete --json`.\n\n- execution_contract.json';
  const expected = await page.evaluate(raw => agpNormalizeUserTurnText(raw), rawPrompt);
  expect(result.messages[0].text).toBe(expected);
});
