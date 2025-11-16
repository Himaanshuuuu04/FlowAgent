export default defineContentScript({
  matches: ["<all_urls>"],
  main() {
    console.log("Content script loaded on:", window.location.href);

    // Create and manage AI frame overlay
    let aiFrame: HTMLElement | null = null;

    function createAIFrame() {
      if (aiFrame) return; // Already exists

      aiFrame = document.createElement("div");
      aiFrame.id = "ai-extension-frame";
      aiFrame.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
        z-index: 2147483647;
        border: 8px solid rgba(66, 133, 244, 0.8);
        box-shadow: inset 0 0 40px rgba(66, 133, 244, 0.3),
                    0 0 60px rgba(66, 133, 244, 0.5);
        animation: ai-pulse 2s ease-in-out infinite;
      `;

      // Add keyframe animation
      const style = document.createElement("style");
      style.textContent = `
        @keyframes ai-pulse {
          0%, 100% {
            border-color: rgba(66, 133, 244, 0.8);
            box-shadow: inset 0 0 40px rgba(66, 133, 244, 0.3),
                        0 0 60px rgba(66, 133, 244, 0.5);
          }
          50% {
            border-color: rgba(66, 133, 244, 1);
            box-shadow: inset 0 0 60px rgba(66, 133, 244, 0.5),
                        0 0 80px rgba(66, 133, 244, 0.7);
          }
        }
      `;
      document.head.appendChild(style);
      document.body.appendChild(aiFrame);
      console.log("AI frame activated");
    }

    function removeAIFrame() {
      if (aiFrame) {
        aiFrame.remove();
        aiFrame = null;
        console.log("AI frame deactivated");
      }
    }

    // Listen for messages from background script
    browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type === "PERFORM_ACTION") {
        performAction(message.action).then(sendResponse);
        return true; // Keep channel open for async response
      }

      if (message.type === "TOGGLE_AI_FRAME") {
        if (message.active) {
          createAIFrame();
        } else {
          removeAIFrame();
        }
        sendResponse({ success: true });
        return true;
      }
    });

    // Helper function to find elements
    function findElement(selector: string): HTMLElement | null {
      return document.querySelector(selector);
    }

    async function performAction(action: string): Promise<any> {
      console.log("Performing action:", action);

      // Parse action with AI or use simple keyword matching
      const actionLower = action.toLowerCase();

      try {
        // Play video action
        if (actionLower.includes("play") && actionLower.includes("video")) {
          const video = document.querySelector("video") as HTMLVideoElement;
          if (video) {
            video.play();
            return { success: true, message: "Video started playing" };
          }
          return { success: false, message: "No video found on page" };
        }

        // Pause video action
        if (actionLower.includes("pause") && actionLower.includes("video")) {
          const video = document.querySelector("video") as HTMLVideoElement;
          if (video) {
            video.pause();
            return { success: true, message: "Video paused" };
          }
          return { success: false, message: "No video found on page" };
        }

        // Click button action
        if (actionLower.includes("click")) {
          const buttons = Array.from(
            document.querySelectorAll('button, a, [role="button"]')
          );

          // Try to find button with matching text
          const matchingButton = buttons.find((btn) => {
            const text = btn.textContent?.toLowerCase() || "";
            return actionLower.split(" ").some((word) => text.includes(word));
          }) as HTMLElement;

          if (matchingButton) {
            matchingButton.click();
            return {
              success: true,
              message: `Clicked: ${matchingButton.textContent}`,
            };
          }
          return { success: false, message: "No matching button found" };
        }

        // Fill form action
        if (actionLower.includes("fill") || actionLower.includes("type")) {
          const input = document.querySelector(
            'input[type="text"], textarea'
          ) as HTMLInputElement;
          if (input) {
            const textToFill =
              action.split(/fill|type/i)[1]?.trim() || "Sample text";
            input.value = textToFill;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            return {
              success: true,
              message: `Filled input with: ${textToFill}`,
            };
          }
          return { success: false, message: "No input field found" };
        }

        // Scroll action
        if (actionLower.includes("scroll")) {
          if (actionLower.includes("down")) {
            window.scrollBy({ top: 500, behavior: "smooth" });
            return { success: true, message: "Scrolled down" };
          }
          if (actionLower.includes("up")) {
            window.scrollBy({ top: -500, behavior: "smooth" });
            return { success: true, message: "Scrolled up" };
          }
          window.scrollTo({ top: 0, behavior: "smooth" });
          return { success: true, message: "Scrolled to top" };
        }

        // Get page info
        if (
          actionLower.includes("info") ||
          actionLower.includes("tell me about")
        ) {
          return {
            success: true,
            message: "Page information",
            data: {
              title: document.title,
              url: window.location.href,
              hasVideo: !!document.querySelector("video"),
              hasForm: !!document.querySelector("form"),
              images: document.querySelectorAll("img").length,
            },
          };
        }

        return { success: false, message: "Action not recognized" };
      } catch (error) {
        return { success: false, message: (error as Error).message };
      }
    }
  },
});
