const RESEARCH_PROMPT = `Run a deep research briefing focused on:
- AI
- VR/XR
- Technology
- Startups
- The most interesting Kickstarter and crowdfunding projects

Instructions:
1) Prioritize the most important updates from the last 24 hours.
2) Group into 5-8 themes with clear headlines.
3) For each theme: what happened, why it matters, short-term implications.
4) Highlight weak claims that need verification.
5) End with a concise 10-bullet executive summary.`;

const NOTEBOOK_URL = "https://notebooklm.google.com/";
const LOG_KEY = "runLogs";
const LOG_LIMIT = 300;

function errorToObject(err) {
  if (!err) return { message: "Unknown error" };
  return {
    name: err.name || "Error",
    message: err.message || String(err),
    stack: err.stack || null
  };
}

async function appendLog(level, event, details = {}) {
  const entry = {
    ts: new Date().toISOString(),
    source: "background",
    level,
    event,
    details
  };

  const logger = level === "error" ? console.error : level === "warn" ? console.warn : console.log;
  logger("[NotebookLM Launcher]", entry);

  try {
    const { [LOG_KEY]: logs = [] } = await chrome.storage.local.get([LOG_KEY]);
    logs.push(entry);
    const trimmed = logs.slice(-LOG_LIMIT);
    await chrome.storage.local.set({ [LOG_KEY]: trimmed });
  } catch (err) {
    console.error("[NotebookLM Launcher] Failed to persist log", errorToObject(err));
  }
}

function buildPendingRun() {
  return {
    createdAt: Date.now(),
    researchPrompt: RESEARCH_PROMPT,
    autoRun: true,
    triggerAudio: true,
    triggerVideo: true
  };
}

async function tryRunInExistingTab(pendingRun) {
  const tabs = await chrome.tabs.query({ url: "https://notebooklm.google.com/*" });
  if (!tabs.length) {
    await appendLog("info", "no_open_notebook_tab");
    return false;
  }

  const targetTab = tabs[0];
  if (!targetTab.id) {
    await appendLog("warn", "open_tab_without_id");
    return false;
  }

  await appendLog("info", "attempt_start_in_open_tab", { tabId: targetTab.id });
  await chrome.tabs.update(targetTab.id, { active: true });
  await chrome.windows.update(targetTab.windowId, { focused: true }).catch(() => {});

  try {
    const resp = await chrome.tabs.sendMessage(targetTab.id, { type: "runDeepResearchNow", pendingRun });
    const ok = !!resp?.ok;
    await appendLog(ok ? "info" : "warn", "start_in_open_tab_result", { tabId: targetTab.id, ok });
    return ok;
  } catch (err) {
    await appendLog("error", "start_in_open_tab_message_error", { tabId: targetTab.id, error: errorToObject(err) });
    return false;
  }
}

chrome.action.onClicked.addListener(async () => {
  await appendLog("info", "action_click");
  try {
    const pendingRun = buildPendingRun();
    const startedInOpenTab = await tryRunInExistingTab(pendingRun);
    if (startedInOpenTab) return;

    await chrome.storage.local.set({ pendingRun });
    await appendLog("info", "pending_run_saved_for_new_tab");
    await chrome.tabs.create({ url: NOTEBOOK_URL });
    await appendLog("info", "new_notebook_tab_opened");
  } catch (err) {
    await appendLog("error", "action_click_failed", { error: errorToObject(err) });
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "consumePendingRun") return false;

  chrome.storage.local.get(["pendingRun"]).then(async ({ pendingRun }) => {
    if (!pendingRun) {
      await appendLog("warn", "consume_pending_run_empty");
      sendResponse({ ok: true, pendingRun: null });
      return;
    }
    chrome.storage.local.remove(["pendingRun"]).then(async () => {
      await appendLog("info", "consume_pending_run_success");
      sendResponse({ ok: true, pendingRun });
    }).catch(async (err) => {
      await appendLog("error", "consume_pending_run_remove_failed", { error: errorToObject(err) });
      sendResponse({ ok: false, pendingRun: null });
    });
  }).catch(async (err) => {
    await appendLog("error", "consume_pending_run_get_failed", { error: errorToObject(err) });
    sendResponse({ ok: false, pendingRun: null });
  });

  return true;
});

self.addEventListener("error", (event) => {
  appendLog("error", "global_error", {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno
  });
});

self.addEventListener("unhandledrejection", (event) => {
  appendLog("error", "global_unhandled_rejection", {
    reason: event.reason?.message || String(event.reason)
  });
});
