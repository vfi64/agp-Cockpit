const { test, expect } = require("@playwright/test");
const path = require("path");
const { pathToFileURL } = require("url");

function fixtureUrl(mode) {
  const file = path.resolve(__dirname, "..", "browser_fixtures", "chatgpt_fixture.html");
  return pathToFileURL(file).href + "?mode=" + encodeURIComponent(mode);
}

test("066-A reproduces accepted send with missing user bubble and assistant activity", async ({ page }) => {
  await page.goto(fixtureUrl("missing-user-bubble"));

  const beforeUsers = await page.locator('[data-message-author-role="user"]').count();
  const beforeAssistants = await page.locator('[data-message-author-role="assistant"]').count();

  const prompt = "AGP 066 reproduction prompt";
  await page.locator("#prompt-textarea").fill(prompt);
  await page.locator('button[data-testid="send-button"]').click();

  await expect.poll(async () => {
    return await page.locator('[data-message-author-role="assistant"]').count();
  }).toBe(beforeAssistants + 1);

  const afterUsers = await page.locator('[data-message-author-role="user"]').count();
  const accepted = await page.evaluate(() => window.__AGP_FIXTURE.acceptedPrompts.length);
  const generations = await page.evaluate(() => window.__AGP_FIXTURE.assistantGenerationCount);

  expect(afterUsers).toBe(beforeUsers);
  expect(accepted).toBe(1);
  expect(generations).toBe(1);
});

test("066-A preserves true send failure as no acceptance evidence", async ({ page }) => {
  await page.goto(fixtureUrl("real-send-failure"));

  await page.locator("#prompt-textarea").fill("must not be accepted");
  await page.locator('button[data-testid="send-button"]').click();
  await page.waitForTimeout(400);

  expect(await page.locator('[data-message-author-role="user"]').count()).toBe(0);
  expect(await page.locator('[data-message-author-role="assistant"]').count()).toBe(0);
  expect(await page.evaluate(() => window.__AGP_FIXTURE.acceptedPrompts.length)).toBe(0);
  expect(await page.evaluate(() => window.__AGP_FIXTURE.assistantGenerationCount)).toBe(0);
});
