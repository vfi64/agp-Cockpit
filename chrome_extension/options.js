async function load() {
  const cfg = await chrome.storage.local.get({
    token: "",
    baseUrl: "http://127.0.0.1:9876"
  });

  document.getElementById("token").value =
    cfg.token;
  document.getElementById("baseUrl").value =
    cfg.baseUrl;
}

document
  .getElementById("save")
  .addEventListener("click", async () => {
    await chrome.storage.local.set({
      token:
        document.getElementById("token").value.trim(),
      baseUrl:
        document.getElementById("baseUrl").value.trim()
    });
    document.getElementById("status").textContent =
      "Saved.";
  });

load();
