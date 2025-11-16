// --- START: Interfaces for Tab Tracking (from your Plasmo project) ---
interface TabInfo {
  id?: number;
  url?: string;
  title?: string;
  favIconUrl?: string;
}

interface TabsData {
  allTabs: TabInfo[];
  activeTab: TabInfo;
  totalTabs: number;
  lastUpdated: string;
}
// --- END: Interfaces for Tab Tracking ---

export default defineBackground(() => {
  console.log("Background service worker started");

  // Track which tabs have the AI frame active
  const activeFrameTabs = new Set<number>();

  // --- START: Logic from WXT AI Assistant (Your Friend's Code) ---
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log("Background received message:", message);

    if (message.type === "ACTIVATE_AI_FRAME") {
      handleActivateAIFrame(message.tabId)
        .then(sendResponse)
        .catch((err) => {
          console.error("ACTIVATE_AI_FRAME error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true;
    }

    if (message.type === "DEACTIVATE_AI_FRAME") {
      handleDeactivateAIFrame(message.tabId)
        .then(sendResponse)
        .catch((err) => {
          console.error("DEACTIVATE_AI_FRAME error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true;
    }

    if (message.type === "GET_ACTIVE_TAB") {
      handleGetActiveTab()
        .then(sendResponse)
        .catch((err) => {
          console.error("GET_ACTIVE_TAB error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true; // Keep channel open for async response
    }

    if (message.type === "GET_ALL_TABS") {
      handleGetAllTabs()
        .then(sendResponse)
        .catch((err) => {
          console.error("GET_ALL_TABS error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true;
    }

    if (message.type === "EXECUTE_ACTION") {
      handleExecuteAction(message.payload)
        .then(sendResponse)
        .catch((err) => {
          console.error("EXECUTE_ACTION error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true;
    }

    if (message.type === "GEMINI_REQUEST") {
      handleGeminiRequest(message.payload)
        .then(sendResponse)
        .catch((err) => {
          console.error("GEMINI_REQUEST error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true;
    }

    if (message.type === "RUN_GENERATED_AGENT") {
      handleRunGeneratedAgent(message.payload)
        .then(sendResponse)
        .catch((err) => {
          console.error("RUN_GENERATED_AGENT error:", err);
          sendResponse({ success: false, error: err.message });
        });
      return true;
    }

    // If no handler matched, send error response
    console.warn("Unknown message type:", message.type);
    sendResponse({ success: false, error: "Unknown message type" });
    return false;
  });
  // --- END: Logic from WXT AI Assistant ---

  // --- START: Tab Tracking Logic (from your Plasmo Project) ---
  // These listeners update the storage for the new Popup
  console.log("Tab tracking for popup is now active");

  browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === "complete") {
      storeTabsInfo();
    }
  });

  browser.tabs.onActivated.addListener(() => {
    storeTabsInfo();
  });

  browser.tabs.onCreated.addListener(() => {
    storeTabsInfo();
  });

  browser.tabs.onRemoved.addListener(() => {
    storeTabsInfo();
  });

  // Initial store on load
  storeTabsInfo();
  // --- END: Tab Tracking Logic ---
});

// =================================================================
// HELPER FUNCTIONS
// =================================================================

// --- START: Helpers from WXT AI Assistant ---

async function handleActivateAIFrame(tabId?: number) {
  try {
    if (!tabId) {
      const [tab] = await browser.tabs.query({
        active: true,
        currentWindow: true,
      });
      tabId = tab.id;
    }

    if (!tabId) {
      return { success: false, error: "No tab ID found" };
    }

    console.log("Activating AI frame on tab:", tabId);

    // Inject the AI frame directly
    await browser.scripting.executeScript({
      target: { tabId },
      func: () => {
        // Remove existing frame if any
        const existing = document.getElementById("ai-extension-frame-overlay");
        if (existing) existing.remove();

        // Create frame overlay
        const frame = document.createElement("div");
        frame.id = "ai-extension-frame-overlay";
        frame.style.cssText = `
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          width: 100vw !important;
          height: 100vh !important;
          pointer-events: none !important;
          z-index: 2147483647 !important;
          border: 8px solid rgba(66, 133, 244, 0.9) !important;
          box-shadow: inset 0 0 40px rgba(66, 133, 244, 0.4),
                      0 0 60px rgba(66, 133, 244, 0.6) !important;
          animation: ai-pulse-animation 2s ease-in-out infinite !important;
        `;

        // Add keyframe animation
        const styleId = "ai-frame-styles";
        if (!document.getElementById(styleId)) {
          const style = document.createElement("style");
          style.id = styleId;
          style.textContent = `
            @keyframes ai-pulse-animation {
              0%, 100% {
                border-color: rgba(66, 133, 244, 0.8);
                box-shadow: inset 0 0 40px rgba(66, 133, 244, 0.3),
                            0 0 60px rgba(66, 133, 244, 0.5);
              }
              50% {
                border-color: rgba(66, 133, 244, 1);
                box-shadow: inset 0 0 60px rgba(66, 133, 244, 0.5),
                            0 0 80px rgba(66, 133, 244, 0.8);
              }
            }
          `;
          document.head.appendChild(style);
        }

        document.body.appendChild(frame);
        console.log("✅ AI frame activated");
      },
    });

    return { success: true, tabId };
  } catch (error) {
    console.error("Error activating AI frame:", error);
    return { success: false, error: (error as Error).message };
  }
}

async function handleDeactivateAIFrame(tabId?: number) {
  try {
    if (!tabId) {
      const [tab] = await browser.tabs.query({
        active: true,
        currentWindow: true,
      });
      tabId = tab.id;
    }

    if (!tabId) {
      return { success: false, error: "No tab ID found" };
    }

    console.log("Deactivating AI frame on tab:", tabId);

    await browser.scripting.executeScript({
      target: { tabId },
      func: () => {
        const frame = document.getElementById("ai-extension-frame-overlay");
        if (frame) {
          frame.remove();
          console.log("✅ AI frame deactivated");
        }
      },
    });

    return { success: true, tabId };
  } catch (error) {
    console.error("Error deactivating AI frame:", error);
    return { success: false, error: (error as Error).message };
  }
}

async function handleGetActiveTab() {
  try {
    const [tab] = await browser.tabs.query({
      active: true,
      currentWindow: true,
    });
    return { success: true, tab };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}

async function handleGetAllTabs() {
  try {
    const tabs = await browser.tabs.query({});
    return { success: true, tabs };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}

async function handleExecuteAction(payload: any) {
  try {
    const { action, tabId } = payload;

    // Inject content script if needed
    // Note: Make sure this file path is correct in the WXT project
    await browser.scripting.executeScript({
      target: { tabId },
      files: ["/content-scripts/content.js"],
    });

    // Send action to content script
    const response = await browser.tabs.sendMessage(tabId, {
      type: "PERFORM_ACTION",
      action,
    });

    return { success: true, response };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}

async function handleGeminiRequest(payload: any) {
  try {
    const { prompt, apiKey } = payload;

    // Import Gemini dynamically
    const { GoogleGenerativeAI } = await import("@google/generative-ai");
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();

    return { success: true, text };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}

async function handleRunGeneratedAgent(payload: any) {
  try {
    const { action_plan, tabId } = payload;

    if (!action_plan) {
      return { success: false, error: "No action plan provided" };
    }

    if (!tabId) {
      return { success: false, error: "No tab ID provided" };
    }

    console.log("Executing action plan for tab:", tabId, action_plan);

    const actions = action_plan.actions || [];
    const results = [];

    for (let i = 0; i < actions.length; i++) {
      const action = actions[i];
      console.log(`Executing action ${i + 1}/${actions.length}:`, action.type);

      try {
        const result = await executeAction(tabId, action);
        results.push({ success: true, action: action.type, result });
      } catch (error) {
        const errorMsg = (error as Error).message;
        console.error(`Action ${i + 1} failed:`, errorMsg);
        results.push({ success: false, action: action.type, error: errorMsg });
        // Continue with next action even if one fails
      }
    }

    const allSucceeded = results.every((r) => r.success);
    return {
      success: allSucceeded,
      message: allSucceeded
        ? "All actions executed successfully"
        : "Some actions failed",
      results,
    };
  } catch (error) {
    console.error("Error executing action plan:", error);
    return { success: false, error: (error as Error).message };
  }
}

async function executeAction(tabId: number, action: any) {
  console.log("Executing action:", action.type, "with params:", action);

  // ============ TAB/WINDOW CONTROL ACTIONS ============
  // These operate at browser level, not DOM level

  switch (action.type) {
    case "OPEN_TAB": {
      const url = action.url || "about:blank";
      const active = action.active !== false; // default true

      const newTab = await browser.tabs.create({
        url: url,
        active: active,
      });

      // If active, wait for it to load before continuing
      if (active && url !== "about:blank") {
        await new Promise((resolve) => {
          const listener = (
            updatedTabId: number,
            changeInfo: chrome.tabs.TabChangeInfo
          ) => {
            if (
              updatedTabId === newTab.id &&
              changeInfo.status === "complete"
            ) {
              browser.tabs.onUpdated.removeListener(listener);
              resolve(null);
            }
          };
          browser.tabs.onUpdated.addListener(listener);

          // Timeout fallback
          setTimeout(resolve, 10000);
        });
      }

      return {
        message: `Opened new tab: ${url}`,
        tabId: newTab.id,
        url: newTab.url,
      };
    }

    case "CLOSE_TAB": {
      const targetTabId = action.tabId || tabId;
      await browser.tabs.remove(targetTabId);
      return { message: `Closed tab ${targetTabId}` };
    }

    case "SWITCH_TAB": {
      if (action.tabId) {
        await browser.tabs.update(action.tabId, { active: true });
        return { message: `Switched to tab ${action.tabId}` };
      } else if (action.direction) {
        // Switch to next/previous tab
        const allTabs = await browser.tabs.query({ currentWindow: true });
        const currentIndex = allTabs.findIndex((t) => t.id === tabId);

        let newIndex;
        if (action.direction === "next") {
          newIndex = (currentIndex + 1) % allTabs.length;
        } else {
          newIndex = (currentIndex - 1 + allTabs.length) % allTabs.length;
        }

        const targetTab = allTabs[newIndex];
        if (targetTab.id) {
          await browser.tabs.update(targetTab.id, { active: true });
          return { message: `Switched to ${action.direction} tab` };
        }
      }
      throw new Error("SWITCH_TAB requires tabId or direction");
    }

    case "NAVIGATE": {
      const targetTabId = action.tabId || tabId;
      const url = action.url;

      if (!url) {
        throw new Error("NAVIGATE requires url");
      }

      await browser.tabs.update(targetTabId, { url: url });

      // Wait for navigation to complete
      await new Promise((resolve) => {
        const listener = (
          updatedTabId: number,
          changeInfo: chrome.tabs.TabChangeInfo
        ) => {
          if (
            updatedTabId === targetTabId &&
            changeInfo.status === "complete"
          ) {
            browser.tabs.onUpdated.removeListener(listener);
            resolve(null);
          }
        };
        browser.tabs.onUpdated.addListener(listener);

        // Timeout fallback
        setTimeout(resolve, 10000);
      });

      return { message: `Navigated to ${url}`, tabId: targetTabId };
    }

    case "RELOAD_TAB": {
      const targetTabId = action.tabId || tabId;
      const bypassCache = action.bypassCache || false;

      await browser.tabs.reload(targetTabId, { bypassCache: bypassCache });

      // Wait for reload to complete
      await new Promise((resolve) => {
        const listener = (
          updatedTabId: number,
          changeInfo: chrome.tabs.TabChangeInfo
        ) => {
          if (
            updatedTabId === targetTabId &&
            changeInfo.status === "complete"
          ) {
            browser.tabs.onUpdated.removeListener(listener);
            resolve(null);
          }
        };
        browser.tabs.onUpdated.addListener(listener);

        // Timeout fallback
        setTimeout(resolve, 5000);
      });

      return { message: `Reloaded tab ${targetTabId}` };
    }

    case "DUPLICATE_TAB": {
      const targetTabId = action.tabId || tabId;
      const duplicatedTab = await browser.tabs.duplicate(targetTabId);
      return {
        message: `Duplicated tab ${targetTabId}`,
        newTabId: duplicatedTab.id,
      };
    }

    // ============ DOM MANIPULATION ACTIONS ============
    // These require injecting scripts into the page

    case "CLICK":
      console.log("Attempting CLICK on:", action.selector);
      return await browser.scripting.executeScript({
        target: { tabId },
        func: (selector: string) => {
          console.log("In page context - looking for:", selector);
          const el = document.querySelector(selector);
          if (!el) {
            console.error("Element not found:", selector);
            throw new Error(`Element not found: ${selector}`);
          }
          console.log("Found element:", el);
          (el as HTMLElement).click();
          return `Clicked: ${selector}`;
        },
        args: [action.selector],
      });

    case "TYPE":
      console.log(
        "Attempting TYPE on:",
        action.selector,
        "with value:",
        action.value
      );
      return await browser.scripting.executeScript({
        target: { tabId },
        func: (selector: string, text: string) => {
          console.log("In page context - looking for:", selector);
          const el = document.querySelector(selector);
          if (!el) {
            console.error("Element not found:", selector);
            throw new Error(`Element not found: ${selector}`);
          }

          console.log(
            "Found element:",
            el,
            "isContentEditable:",
            (el as HTMLElement).isContentEditable
          );

          // Handle contenteditable elements (like ChatGPT input)
          if (
            (el as HTMLElement).isContentEditable ||
            el.getAttribute("contenteditable") === "true"
          ) {
            // For contenteditable, we need to focus and set the text properly
            (el as HTMLElement).focus();

            // Try multiple methods for contenteditable
            if ((el as any).innerText !== undefined) {
              (el as HTMLElement).innerText = text;
            } else {
              (el as HTMLElement).textContent = text;
            }

            // Trigger events
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));

            // For some sites, we need to trigger keyboard events
            el.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true }));
            el.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
          } else if (
            el.tagName === "TEXTAREA" ||
            (el.tagName === "INPUT" && (el as HTMLInputElement).type === "text")
          ) {
            // Standard input/textarea
            (el as HTMLInputElement).focus();
            (el as HTMLInputElement).value = text;

            // Trigger all the events that frameworks listen to
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
            el.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true }));
            el.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
          } else {
            // Fallback for other elements
            (el as HTMLInputElement).value = text;
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
          }

          return `Typed "${text.substring(0, 50)}${
            text.length > 50 ? "..." : ""
          }" into: ${selector}`;
        },
        args: [action.selector, action.value],
      });

    case "SCROLL":
      return await browser.scripting.executeScript({
        target: { tabId },
        func: (direction: string, amount: number) => {
          if (direction === "down") {
            window.scrollBy(0, amount || 500);
          } else if (direction === "up") {
            window.scrollBy(0, -(amount || 500));
          } else if (direction === "top") {
            window.scrollTo(0, 0);
          } else if (direction === "bottom") {
            window.scrollTo(0, document.body.scrollHeight);
          }
          return `Scrolled ${direction}`;
        },
        args: [action.direction || "down", action.amount],
      });

    case "WAIT":
      const waitTime = action.time || 1000;
      await new Promise((resolve) => setTimeout(resolve, waitTime));
      return `Waited ${waitTime}ms`;

    case "SELECT":
      return await browser.scripting.executeScript({
        target: { tabId },
        func: (selector: string, value: string) => {
          const el = document.querySelector(selector) as HTMLSelectElement;
          if (!el) throw new Error(`Element not found: ${selector}`);
          el.value = value;
          el.dispatchEvent(new Event("change", { bubbles: true }));
          return `Selected: ${value}`;
        },
        args: [action.selector, action.value],
      });

    case "EXECUTE_SCRIPT":
      return await browser.scripting.executeScript({
        target: { tabId },
        func: new Function(action.script) as any,
      });

    default:
      throw new Error(`Unknown action type: ${action.type}`);
  }
}

// --- END: Helpers from WXT AI Assistant ---

// --- START: Helpers for Tab Tracking (from your Plasmo Project) ---
// These functions write to storage for the popup

async function getAllTabsInfo(): Promise<TabsData | null> {
  try {
    const allTabs = await browser.tabs.query({});
    const [activeTab] = await browser.tabs.query({
      active: true,
      currentWindow: true,
    });

    const allTabsUrls: TabInfo[] = allTabs.map((tab) => ({
      id: tab.id,
      url: tab.url,
      title: tab.title,
      favIconUrl: tab.favIconUrl,
    }));

    const activeTabInfo: TabInfo = {
      id: activeTab?.id,
      url: activeTab?.url,
      title: activeTab?.title,
      favIconUrl: activeTab?.favIconUrl,
    };

    return {
      allTabs: allTabsUrls,
      activeTab: activeTabInfo,
      totalTabs: allTabsUrls.length,
      lastUpdated: new Date().toISOString(),
    };
  } catch (error) {
    console.error("Error fetching tabs for popup:", error);
    return null;
  }
}

async function storeTabsInfo(): Promise<TabsData | null> {
  const tabsInfo = await getAllTabsInfo();
  if (tabsInfo) {
    // Use standard browser.storage.local.set
    await browser.storage.local.set({
      tabsData: tabsInfo,
      allTabsUrls: tabsInfo.allTabs,
      activeTabUrl: tabsInfo.activeTab,
      totalTabs: tabsInfo.totalTabs,
      lastUpdated: tabsInfo.lastUpdated,
    });
    // console.log("Tabs info stored for popup:", tabsInfo);
    return tabsInfo;
  }
  return null;
}
// --- END: Helpers for Tab Tracking ---
