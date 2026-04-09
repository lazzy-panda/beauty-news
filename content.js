function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function xFirst(xpath, context = document) {
  const doc = context?.ownerDocument || document;
  return doc.evaluate(xpath, context, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}

function xAll(xpath, context = document) {
  const doc = context?.ownerDocument || document;
  const result = doc.evaluate(xpath, context, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
  const nodes = [];
  for (let i = 0; i < result.snapshotLength; i += 1) {
    nodes.push(result.snapshotItem(i));
  }
  return nodes;
}

function xClosest(node, xpathCondition) {
  if (!node) return null;
  return xFirst(`ancestor-or-self::*[${xpathCondition}][1]`, node);
}

const LOG_KEY = "runLogs";
const LOG_LIMIT = 300;
const LOG_SOURCE = "content";

const DEFAULT_RUN_CFG = {
  researchPrompt: "",
  autoRun: true,
  triggerAudio: true,
  triggerVideo: true
};

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
    source: LOG_SOURCE,
    level,
    event,
    details: { url: location.href, ...details }
  };

  const logger = level === "error" ? console.error : level === "warn" ? console.warn : console.log;
  logger("[NotebookLM Launcher]", entry);

  try {
    const { [LOG_KEY]: logs = [] } = await chrome.storage.local.get([LOG_KEY]);
    logs.push(entry);
    await chrome.storage.local.set({ [LOG_KEY]: logs.slice(-LOG_LIMIT) });
  } catch (err) {
    console.error("[NotebookLM Launcher] Failed to persist log", errorToObject(err));
  }
}

function textOf(el) {
  return (el?.innerText || el?.textContent || "").trim().toLowerCase();
}

function visible(el) {
  if (!el) return false;
  if (xClosest(el, "@aria-hidden='true' or @inert")) return false;
  const r = el.getBoundingClientRect();
  const s = window.getComputedStyle(el);
  return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
}

function getActiveInteractionRoot() {
  const overlays = xAll(
    "//*[(" +
      "@role='dialog' or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' cdk-overlay-pane ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-dialog-container ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-menu-panel ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-autocomplete-panel ')" +
    ") and not(@aria-hidden='true') and not(@inert)]"
  ).filter((el) => visible(el));

  if (!overlays.length) return document;
  return overlays[overlays.length - 1];
}

function findClickableByText(candidates, phrases) {
  const lowerPhrases = phrases.map((p) => p.toLowerCase());
  for (const el of candidates) {
    if (!visible(el)) continue;
    const t = textOf(el);
    if (!t) continue;
    if (lowerPhrases.some((p) => t.includes(p))) {
      const clickable = xClosest(
        el,
        "self::button or @role='button' or @role='option' or @role='menuitem' or @tabindex or self::a or self::li"
      );
      return clickable || el;
    }
  }
  return null;
}

async function clickByText(phrases, timeoutOrOptions = 15000) {
  let timeoutMs = 15000;
  let logOnTimeout = true;
  if (typeof timeoutOrOptions === "number") {
    timeoutMs = timeoutOrOptions;
  } else if (timeoutOrOptions && typeof timeoutOrOptions === "object") {
    timeoutMs = typeof timeoutOrOptions.timeoutMs === "number" ? timeoutOrOptions.timeoutMs : 15000;
    logOnTimeout = timeoutOrOptions.logOnTimeout !== false;
  }

  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const candidates = xAll(
      "//*[self::button or @role or self::a or @tabindex or self::li or self::span or self::div]"
    );
    const el = findClickableByText(candidates, phrases);
    if (el) {
      el.click();
      return true;
    }
    await sleep(350);
  }
  if (logOnTimeout) {
    await appendLog("warn", "click_by_text_timeout", { phrases, timeoutMs });
  }
  return false;
}

function pageHasText(phrases) {
  const all = textOf(document.body);
  return phrases.some((p) => all.includes(p.toLowerCase()));
}

function findCorpusOptionLabel(targetPhrases) {
  const labels = xAll("//*[contains(concat(' ', normalize-space(@class), ' '), ' corpus-option-label ')]");
  return findClickableByText(labels, targetPhrases);
}

function isOptionSelected(labelEl) {
  if (!labelEl) return false;
  const sel = xClosest(
    labelEl,
    "@aria-selected='true' or @aria-checked='true' or @data-selected='true' or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' selected ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' active ')"
  );
  return !!sel;
}

function clickCorpusOptionLabel(targetPhrases) {
  const label = findCorpusOptionLabel(targetPhrases);
  if (!label) return false;
  const clickable = xClosest(label, "self::button or @role='button' or @tabindex or self::a") || label;
  clickable.click();
  return true;
}

function getResearchTriggerButton() {
  return xFirst(
    "//div[contains(concat(' ', normalize-space(@class), ' '), ' action-options-right ')]//button[" +
      "contains(concat(' ', normalize-space(@class), ' '), ' corpus-select ') and " +
      "contains(concat(' ', normalize-space(@class), ' '), ' researcher-menu-trigger ')" +
    "] | //div[contains(concat(' ', normalize-space(@class), ' '), ' action-options-right ')]//button[" +
      "contains(concat(' ', normalize-space(@class), ' '), ' corpus-select ')" +
    "]"
  );
}

function getCurrentResearchModeLabel() {
  const trigger = getResearchTriggerButton();
  if (!trigger) return "";
  const labelEl = xFirst(".//*[contains(concat(' ', normalize-space(@class), ' '), ' corpus-select-label ')]", trigger);
  return (textOf(labelEl || trigger) || "").replace(/\s+/g, " ").trim();
}

function isDeepLabel(label) {
  return /deep research|глубокое исследование/i.test(label || "");
}

function isFastLabel(label) {
  return /fast research|быстрое исследование/i.test(label || "");
}

function getVisibleResearchMenuPanel(trigger = null) {
  if (trigger) {
    const controlsId = trigger.getAttribute("aria-controls");
    if (controlsId) {
      const byId = xFirst(
        `//*[@id="${controlsId}" and contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-menu-panel ')]`
      );
      if (byId && visible(byId)) return byId;
    }
  }

  const panels = xAll(
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-menu-panel ') and " +
      "(ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' cdk-overlay-pane ')] " +
      "or ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' cdk-overlay-container ')])]"
  );
  for (const panel of panels) {
    if (visible(panel)) return panel;
  }
  return null;
}

function getMenuItemCandidates(panel) {
  if (!panel) return [];
  return xAll(
    ".//*[@role='menuitem' or self::button[contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-menu-item ')] or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' mat-mdc-menu-item ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' corpus-option-label ')]",
    panel
  );
}

function collectMenuItemsText(panel) {
  return getMenuItemCandidates(panel)
    .map((el) => textOf(el).replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .slice(0, 20);
}

function findMenuItemByText(panel, phrases) {
  const candidates = getMenuItemCandidates(panel);
  return findClickableByText(candidates, phrases);
}

function findDeepMenuItemFlexible(panel) {
  const items = getMenuItemCandidates(panel);
  for (const item of items) {
    if (!visible(item)) continue;
    const t = textOf(item).replace(/\s+/g, " ").trim();
    if (!t) continue;
    if (/deep/i.test(t) && /research|исслед/i.test(t)) return item;
    if (/глуб/i.test(t) && /исслед/i.test(t)) return item;
  }
  return null;
}

function findBestAlternativeMenuItem(panel, currentModeLabel) {
  const items = getMenuItemCandidates(panel).filter((el) => visible(el));
  if (!items.length) return null;
  if (items.length === 1) return items[0];

  const current = (currentModeLabel || "").toLowerCase();
  const notCurrent = items.find((el) => {
    const t = textOf(el).replace(/\s+/g, " ").trim();
    return t && current && !t.includes(current);
  });
  if (notCurrent) return notCurrent;

  // Typical case: menu has two options Fast/Deep, Deep is second.
  return items[1] || items[0];
}

async function openResearchMenu() {
  const trigger = getResearchTriggerButton();
  if (!trigger || !visible(trigger)) return false;

  const started = Date.now();
  while (Date.now() - started < 4000) {
    const expanded = (trigger.getAttribute("aria-expanded") || "").toLowerCase() === "true";
    if (expanded && getVisibleResearchMenuPanel(trigger)) return true;
    trigger.click();
    await sleep(250);
    if (getVisibleResearchMenuPanel(trigger)) return true;
  }
  return false;
}

function dispatchKey(el, key) {
  if (!el) return;
  el.dispatchEvent(new KeyboardEvent("keydown", { key, code: key, bubbles: true }));
  el.dispatchEvent(new KeyboardEvent("keyup", { key, code: key, bubbles: true }));
}

async function selectByKeyboardFallback(trigger, currentModeLabel) {
  if (!trigger) return false;
  trigger.focus();
  // Typical menu keyboard flow: open -> move to next option -> apply.
  dispatchKey(trigger, "Enter");
  await sleep(120);
  dispatchKey(trigger, "ArrowDown");
  await sleep(120);
  dispatchKey(trigger, "Enter");
  await sleep(550);

  const after = getCurrentResearchModeLabel();
  const switched = !!after && after !== currentModeLabel;
  await appendLog(switched ? "info" : "warn", "deep_switch_keyboard_fallback_result", {
    modeBeforeSwitch: currentModeLabel,
    modeAfterSwitch: after
  });
  return switched;
}

async function selectDeepFromResearchMenu() {
  const trigger = getResearchTriggerButton();
  if (!trigger) {
    await appendLog("error", "deep_switch_right_trigger_not_found");
    return false;
  }

  await appendLog("info", "deep_switch_step_open_menu_start", {
    currentModeLabel: getCurrentResearchModeLabel(),
    triggerClass: trigger.getAttribute("class") || ""
  });
  const opened = await openResearchMenu();
  if (!opened) {
    await appendLog("error", "deep_switch_step_open_menu_failed");
    return false;
  }

  const panel = getVisibleResearchMenuPanel(trigger);
  if (!panel) {
    await appendLog("error", "deep_switch_step_menu_panel_missing");
    return false;
  }

  const currentModeLabel = getCurrentResearchModeLabel();
  let deepItem = findMenuItemByText(panel, ["deep research", "глубокое исследование"]);
  if (!deepItem) deepItem = findDeepMenuItemFlexible(panel);
  if (!deepItem) deepItem = findBestAlternativeMenuItem(panel, currentModeLabel);
  if (!deepItem) {
    await appendLog("warn", "deep_menu_item_not_found_try_keyboard_fallback", {
      currentModeLabel,
      menuItems: collectMenuItemsText(panel)
    });
    return selectByKeyboardFallback(trigger, currentModeLabel);
  }

  await appendLog("info", "deep_menu_item_selected_candidate", {
    currentModeLabel,
    candidateText: textOf(deepItem).replace(/\s+/g, " ").trim(),
    menuItems: collectMenuItemsText(panel)
  });
  deepItem.click();
  await appendLog("info", "deep_switch_step_deep_item_clicked");
  await sleep(500);
  return true;
}

function isDeepSelectedGeneric() {
  const candidates = xAll("//*[self::button or @role or self::a or self::li or self::div or self::span]");
  const deepEl = findClickableByText(candidates, ["deep research", "глубокое исследование"]);
  if (!deepEl) return false;

  const selectedHolder = xClosest(
    deepEl,
    "@aria-selected='true' or @aria-checked='true' or @aria-pressed='true' or @data-selected='true' or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' selected ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' active ')"
  );
  return !!selectedHolder;
}

function collectResearchUiHints() {
  const nodes = xAll("//*[self::button or @role or self::a or self::li or self::div or self::span]");
  const hints = [];
  for (const el of nodes) {
    if (!visible(el)) continue;
    const t = textOf(el);
    if (!t || t.length < 3 || t.length > 80) continue;
    if (/(deep|fast|research|source|sources|web|исслед|источник)/i.test(t)) {
      hints.push(t.replace(/\s+/g, " "));
    }
    if (hints.length >= 30) break;
  }
  return Array.from(new Set(hints));
}

function isNotebookWorkspaceReady() {
  const trigger = getResearchTriggerButton();
  if (trigger && visible(trigger)) return true;
  const input = getInputBox();
  return !!input;
}

function clickCreateNotebookBySelectors() {
  const nodes = xAll(
    "//button[" +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'new notebook') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create notebook') or " +
      "contains(translate(@mattooltip,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'new notebook') or " +
      "contains(translate(@mattooltip,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create notebook')" +
    "] | //a[" +
      "contains(translate(@href,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'/new') or " +
      "contains(translate(@href,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')" +
    "]"
  );

  for (const el of nodes) {
    if (el && visible(el)) {
      el.click();
      return true;
    }
  }
  return false;
}

async function ensureNotebookWorkspace(timeoutMs = 25000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (isNotebookWorkspaceReady()) return true;

    const bySelector = clickCreateNotebookBySelectors();
    if (bySelector) {
      await appendLog("info", "new_notebook_click_by_selector");
      await sleep(900);
      if (isNotebookWorkspaceReady()) return true;
    }

    const byText = await clickByText(
      [
        "new notebook",
        "create notebook",
        "create new",
        "new",
        "создать блокнот",
        "создать"
      ],
      { timeoutMs: 1800, logOnTimeout: false }
    );
    if (byText) {
      await appendLog("info", "new_notebook_click_by_text");
      await sleep(900);
      if (isNotebookWorkspaceReady()) return true;
    }

    await sleep(350);
  }

  await appendLog("error", "new_notebook_open_timeout", {
    timeoutMs,
    uiHints: collectResearchUiHints()
  });
  return false;
}

async function ensureDeepResearchMode(timeoutMs = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const currentMode = getCurrentResearchModeLabel();
    if (isDeepLabel(currentMode)) {
      return true;
    }

    const trigger = getResearchTriggerButton();
    if (!trigger || !visible(trigger)) {
      await sleep(350);
      continue;
    }

    if (isFastLabel(currentMode) || currentMode) {
      const switchedViaMenu = await selectDeepFromResearchMenu();
      if (switchedViaMenu) {
        const modeAfterSwitch = getCurrentResearchModeLabel();
        if (isDeepLabel(modeAfterSwitch)) {
          await appendLog("info", "deep_mode_selected_via_research_menu", { modeAfterSwitch });
          return true;
        }
        await appendLog("warn", "deep_mode_click_no_label_change", {
          modeBeforeSwitch: currentMode,
          modeAfterSwitch
        });
      }
    }

    if (isDeepSelectedGeneric()) {
      return true;
    }

    await sleep(300);
  }
  await appendLog("error", "deep_research_mode_timeout", {
    timeoutMs,
    currentModeLabel: getCurrentResearchModeLabel(),
    uiHints: collectResearchUiHints()
  });
  return false;
}

function getInputBox() {
  const root = getActiveInteractionRoot();
  const scoped = xFirst(
    ".//textarea[" +
      "contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ask') or " +
      "contains(translate(@placeholder,'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'спрос')" +
    "] | .//textarea[" +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ask') or " +
      "contains(translate(@aria-label,'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'спрос')" +
    "] | .//*[@role='textbox' and @contenteditable='true'] | .//div[@contenteditable='true'] | .//textarea",
    root
  );
  if (scoped && visible(scoped)) return scoped;

  const box = xFirst(
    "//textarea[" +
      "contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ask') or " +
      "contains(translate(@placeholder,'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'спрос')" +
    "] | //textarea[" +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ask') or " +
      "contains(translate(@aria-label,'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'спрос')" +
    "] | //*[@role='textbox' and @contenteditable='true'] | //div[@contenteditable='true'] | //textarea"
  );
  return box && visible(box) ? box : null;
}

function getSendButton() {
  const root = getActiveInteractionRoot();
  const scoped = xFirst(
    ".//button[" +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send') or " +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or " +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'run') or " +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'run') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start') or " +
      ".//*[self::mat-icon or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send')]" +
      "] | .//button[@type='submit'] | .//*[@role='button' and (" +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'run') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start')" +
      ")] | .//*[@role='button']//*[self::mat-icon or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send')]/ancestor::*[@role='button'][1] | .//button[" +
      "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'отправ') or " +
      "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'запуст')" +
    "]",
    root
  );
  if (scoped && visible(scoped)) return scoped;

  return xFirst(
    "//button[" +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send') or " +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or " +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'run') or " +
      "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'run') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start') or " +
      ".//*[self::mat-icon or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send')]" +
      "] | //button[@type='submit'] | //*[@role='button' and (" +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'run') or " +
      "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start')" +
      ")] | //*[@role='button']//*[self::mat-icon or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send')]/ancestor::*[@role='button'][1] | //button[" +
      "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'отправ') or " +
      "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'запуст')" +
    "]"
  );
}

async function fillPromptOnly(prompt, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const box = getInputBox();
    if (box) {
      box.focus();
      if ((box.tagName || "").toLowerCase() === "textarea") {
        box.value = prompt;
        box.dispatchEvent(new Event("input", { bubbles: true }));
      } else {
        box.textContent = prompt;
        box.dispatchEvent(new InputEvent("input", { bubbles: true, data: prompt, inputType: "insertText" }));
      }
      await appendLog("info", "prompt_placed", { promptLength: prompt.length });
      return true;
    }
    await sleep(300);
  }
  await appendLog("error", "prompt_place_timeout", { timeoutMs });
  return false;
}

async function submitPrompt(timeoutMs = 8000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const sendButton = getSendButton();
    if (sendButton && visible(sendButton)) {
      sendButton.click();
      await appendLog("info", "research_started_by_send_button");
      return true;
    }
    const box = getInputBox();
    if (box) {
      box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", which: 13, keyCode: 13, bubbles: true }));
      box.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", code: "Enter", which: 13, keyCode: 13, bubbles: true }));
      await appendLog("info", "research_started_by_enter");
      return true;
    }
    await sleep(250);
  }
  await appendLog("error", "research_submit_timeout", { timeoutMs });
  return false;
}

function hasResearchInProgressSignals() {
  const progressNodes = xAll(
    "//*[@role='progressbar' or contains(concat(' ', normalize-space(@class), ' '), ' spinner ') or " +
      "contains(concat(' ', normalize-space(@class), ' '), ' loading ') or contains(@aria-busy,'true')]"
  );
  if (progressNodes.some((el) => visible(el))) return true;
  return pageHasText(["researching", "generating", "processing", "thinking", "остановить", "прервать"]);
}

async function waitForResearchStart(timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (hasResearchInProgressSignals()) {
      await appendLog("info", "research_in_progress_detected");
      return true;
    }
    await sleep(500);
  }
  await appendLog("error", "research_start_wait_timeout", { timeoutMs });
  return false;
}

async function waitForResearchCompletion(timeoutMs = 8 * 60 * 1000) {
  const started = Date.now();
  let stableSince = 0;
  while (Date.now() - started < timeoutMs) {
    const inProgress = hasResearchInProgressSignals();
    if (!inProgress) {
      if (!stableSince) stableSince = Date.now();
      if (Date.now() - stableSince > 7000) {
        await appendLog("info", "research_completion_detected");
        return true;
      }
    } else {
      stableSince = 0;
    }
    await sleep(1000);
  }
  await appendLog("error", "research_completion_timeout", { timeoutMs });
  return false;
}

async function addSourcesStep(timeoutMs = 25000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const openedSources = await clickByText(["sources", "source", "источники", "источник"], { timeoutMs: 1200, logOnTimeout: false });
    const addedSource = await clickByText(
      ["add source", "add sources", "new source", "web", "website", "url", "добавить источник", "добавить"],
      { timeoutMs: 1600, logOnTimeout: false }
    );
    if (openedSources || addedSource) {
      await appendLog("info", "sources_add_step_done", { openedSources, addedSource });
      return true;
    }
    await sleep(500);
  }
  await appendLog("error", "sources_add_step_timeout", { timeoutMs });
  return false;
}

async function clickImportPlusStep(timeoutMs = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const root = getActiveInteractionRoot();
    const importBtn = xFirst(
      ".//button[" +
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'import') or " +
        "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'import') or " +
        "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'импорт')" +
      "][.//*[self::mat-icon or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'add') or " +
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'plus') or normalize-space(.)='+']] | " +
      ".//button[" +
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'import') or " +
        "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'import') or " +
        "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'импорт')" +
      "]",
      root
    ) || xFirst(
      "//button[" +
        "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'import') or " +
        "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'import') or " +
        "contains(translate(normalize-space(.),'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ','абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),'импорт')" +
      "]"
    );

    if (importBtn && visible(importBtn)) {
      importBtn.click();
      await appendLog("info", "import_plus_clicked");
      return true;
    }
    await sleep(300);
  }
  await appendLog("error", "import_plus_click_timeout", { timeoutMs });
  return false;
}

async function startVideoGenerationStep(timeoutMs = 30000) {
  const ok = await clickByText(["video overview", "generate video", "create video", "видео"], { timeoutMs, logOnTimeout: false });
  if (!ok) {
    await appendLog("error", "video_generation_start_failed", { timeoutMs });
    return false;
  }
  await appendLog("info", "video_generation_started");
  return true;
}

async function startAudioGenerationStep(timeoutMs = 30000) {
  const ok = await clickByText(["audio overview", "generate audio", "create audio", "аудио"], { timeoutMs, logOnTimeout: false });
  if (!ok) {
    await appendLog("error", "audio_generation_start_failed", { timeoutMs });
    return false;
  }
  await appendLog("info", "audio_generation_started");
  return true;
}

async function executeStep(stepName, fn) {
  await appendLog("info", "step_start", { stepName });
  const ok = await fn();
  await appendLog(ok ? "info" : "error", "step_end", { stepName, ok });
  return ok;
}

async function stepOpenNotebookLM() {
  const ok = location.href.startsWith("https://notebooklm.google.com/");
  if (!ok) {
    await appendLog("error", "notebooklm_not_opened_in_current_tab", { href: location.href });
    return false;
  }
  await appendLog("info", "notebooklm_opened", { href: location.href });
  return true;
}

async function stepCreateNewNotebook() {
  const workspaceReady = await ensureNotebookWorkspace(30000);
  if (!workspaceReady) {
    await appendLog("error", "run_interrupted_notebook_not_opened");
    return false;
  }
  await appendLog("info", "notebook_workspace_ready");
  return true;
}

async function stepSelectDeepResearchMode() {
  const deepReady = await ensureDeepResearchMode(25000);
  if (!deepReady) {
    await appendLog("error", "run_interrupted_deep_mode_not_ready");
    return false;
  }
  return true;
}

async function stepPlacePrompt(cfg) {
  return fillPromptOnly(cfg.researchPrompt || "", 50000);
}

async function stepLaunchResearch() {
  return submitPrompt(10000);
}

async function stepWaitResearch() {
  const started = await waitForResearchStart(30000);
  if (!started) return false;
  return waitForResearchCompletion(8 * 60 * 1000);
}

async function launchResearchWithRetries(cfg, attempts = 3) {
  for (let i = 1; i <= attempts; i += 1) {
    await appendLog("info", "launch_attempt_start", { attempt: i, attempts });

    const deepReady = await ensureDeepResearchMode(12000);
    if (!deepReady) {
      await appendLog("warn", "launch_attempt_deep_not_ready", { attempt: i });
      continue;
    }

    const placed = await stepPlacePrompt(cfg);
    if (!placed) {
      await appendLog("warn", "launch_attempt_prompt_not_placed", { attempt: i });
      continue;
    }

    const submitted = await stepLaunchResearch();
    if (!submitted) {
      await appendLog("warn", "launch_attempt_submit_failed", { attempt: i });
      continue;
    }

    const started = await waitForResearchStart(20000);
    if (started) {
      await appendLog("info", "launch_attempt_started", { attempt: i });
      return true;
    }

    await appendLog("warn", "launch_attempt_no_progress_signal", { attempt: i });
    await sleep(1200);
  }

  await appendLog("error", "launch_attempts_exhausted", { attempts });
  return false;
}

async function stepAddSources() {
  const importClicked = await clickImportPlusStep(20000);
  if (!importClicked) return false;
  return addSourcesStep(25000);
}

async function stepLaunchVideo(cfg) {
  if (!cfg.triggerVideo) return true;
  return startVideoGenerationStep(30000);
}

async function stepLaunchAudio(cfg) {
  if (!cfg.triggerAudio) return true;
  return startAudioGenerationStep(30000);
}

async function runFlow(cfg) {
  await appendLog("info", "run_flow_started", {
    autoRun: !!cfg.autoRun,
    triggerAudio: !!cfg.triggerAudio,
    triggerVideo: !!cfg.triggerVideo
  });
  await sleep(2500);

  if (!cfg.autoRun) {
    await appendLog("warn", "run_interrupted_auto_run_disabled");
    return false;
  }

  if (!(await executeStep("open_notebooklm", stepOpenNotebookLM))) return false;
  if (!(await executeStep("create_new_notebook", stepCreateNewNotebook))) return false;
  if (!(await executeStep("select_deep_research_mode", stepSelectDeepResearchMode))) return false;
  if (!(await executeStep("launch_research", () => launchResearchWithRetries(cfg, 3)))) return false;
  if (!(await executeStep("wait_research", () => waitForResearchCompletion(8 * 60 * 1000)))) return false;
  if (!(await executeStep("add_sources", stepAddSources))) return false;
  if (!(await executeStep("launch_video_generation", () => stepLaunchVideo(cfg)))) return false;
  if (!(await executeStep("launch_audio_generation", () => stepLaunchAudio(cfg)))) return false;

  await appendLog("info", "run_flow_finished_success");
  return true;
}

let runInProgress = false;

async function startRun(cfg) {
  if (runInProgress) {
    await appendLog("warn", "run_interrupted_already_in_progress");
    return false;
  }
  runInProgress = true;
  const runCfg = { ...DEFAULT_RUN_CFG, ...(cfg || {}) };
  try {
    const ok = await runFlow(runCfg);
    await appendLog(ok ? "info" : "warn", "run_completed", { ok });
    return ok;
  } catch (err) {
    await appendLog("error", "run_failed_with_exception", { error: errorToObject(err) });
    return false;
  } finally {
    runInProgress = false;
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "runDeepResearchNow") return false;
  appendLog("info", "run_requested_by_background");

  startRun(msg.pendingRun || {}).then(
    (ok) => sendResponse({ ok }),
    async (err) => {
      await appendLog("error", "run_request_handler_failed", { error: errorToObject(err) });
      sendResponse({ ok: false });
    }
  );
  return true;
});

(async () => {
  if (!location.href.startsWith("https://notebooklm.google.com/")) return;

  await appendLog("info", "content_loaded_on_notebook_page");
  const resp = await chrome.runtime.sendMessage({ type: "consumePendingRun" }).catch(() => null);
  const pending = resp?.pendingRun;
  if (!pending) {
    await appendLog("info", "no_pending_run_found");
    return;
  }

  // Ignore stale runs older than 3 minutes.
  if (!pending.createdAt || Date.now() - pending.createdAt > 3 * 60 * 1000) {
    await appendLog("warn", "run_interrupted_pending_stale");
    return;
  }

  startRun(pending).catch(() => {
    appendLog("error", "initial_pending_run_failed");
  });
})();

window.addEventListener("error", (event) => {
  appendLog("error", "global_error", {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno
  });
});

window.addEventListener("unhandledrejection", (event) => {
  appendLog("error", "global_unhandled_rejection", {
    reason: event.reason?.message || String(event.reason)
  });
});

window.addEventListener("beforeunload", () => {
  if (runInProgress) {
    appendLog("warn", "run_interrupted_page_unload");
  }
});
