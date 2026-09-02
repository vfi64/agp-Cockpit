const ALARM_NAME = "agp-browser-refresh-tabs";
const LAST_HANDLED = "agpLastHandledRefreshGeneration";
const PENDING = "agpPendingRefreshTabs";

async function performRefresh(generation) {
  const state = await chrome.storage.local.get([LAST_HANDLED]);
  const handled = Number(state[LAST_HANDLED] || 0);

  if (!Number.isFinite(generation) || generation <= handled) {
    return {accepted:false, reason:"already-handled"};
  }

  const tabs = await chrome.tabs.query({
    url:[
      "https://chatgpt.com/*",
      "https://www.chatgpt.com/*"
    ]
  });

  const tabIds = tabs
    .map(tab => tab.id)
    .filter(id => Number.isInteger(id));

  await chrome.storage.local.set({
    [LAST_HANDLED]:generation,
    [PENDING]:{generation, tabIds}
  });

  chrome.alarms.create(
    ALARM_NAME,
    {when:Date.now() + 1500}
  );

  setTimeout(() => {
    chrome.runtime.reload();
  }, 100);

  return {
    accepted:true,
    generation,
    tabCount:tabIds.length
  };
}

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (!message || message.type !== "AGP_REFRESH_INTEGRATION") {
      return false;
    }

    performRefresh(Number(message.generation || 0))
      .then(sendResponse)
      .catch(error => {
        sendResponse({
          accepted:false,
          error:String(error)
        });
      });

    return true;
  }
);

chrome.alarms.onAlarm.addListener(async alarm => {
  if (alarm.name !== ALARM_NAME) {
    return;
  }

  const state = await chrome.storage.local.get([PENDING]);
  const pending = state[PENDING];

  if (!pending || !Array.isArray(pending.tabIds)) {
    return;
  }

  for (const tabId of pending.tabIds) {
    try {
      await chrome.tabs.reload(tabId);
    } catch (_) {}
  }

  await chrome.storage.local.remove(PENDING);
});
