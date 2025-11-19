/**
 * Semantic DOM Extractor
 * Extracts only meaningful, actionable elements from the page
 * Reduces DOM from 50k+ nodes to ~100-300 semantic elements
 */

export interface SemanticElement {
  id: string;
  role: string;
  tag: string;
  text?: string;
  placeholder?: string;
  ariaLabel?: string;
  value?: string;
  href?: string;
  src?: string;
  bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  selector: string;
  isVisible: boolean;
  isInViewport: boolean;
}

export interface SemanticDOM {
  title: string;
  url: string;
  viewport: {
    width: number;
    height: number;
    scrollX: number;
    scrollY: number;
  };
  elements: SemanticElement[];
  timestamp: number;
}

// Generate unique, stable ID for elements
let elementIdCounter = 0;
const elementIdMap = new WeakMap<Element, string>();

function getElementId(element: Element): string {
  if (elementIdMap.has(element)) {
    return elementIdMap.get(element)!;
  }
  const id = `e${++elementIdCounter}`;
  elementIdMap.set(element, id);
  return id;
}

// Check if element is visible
function isElementVisible(element: Element): boolean {
  const style = window.getComputedStyle(element);
  return (
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    style.opacity !== "0" &&
    (element as HTMLElement).offsetParent !== null
  );
}

// Check if element is in viewport
function isInViewport(
  rect: DOMRect,
  scrollX: number,
  scrollY: number
): boolean {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  return (
    rect.bottom > scrollY &&
    rect.top < scrollY + viewportHeight &&
    rect.right > scrollX &&
    rect.left < scrollX + viewportWidth
  );
}

// Generate CSS selector for element
function generateSelector(element: Element): string {
  // Try ID first
  if (element.id) {
    return `#${element.id}`;
  }

  // Try unique attribute combinations
  const testId =
    element.getAttribute("data-testid") || element.getAttribute("data-test");
  if (testId) {
    return `[data-testid="${testId}"]`;
  }

  // Try aria-label
  const ariaLabel = element.getAttribute("aria-label");
  if (ariaLabel && ariaLabel.length < 30) {
    return `${element.tagName.toLowerCase()}[aria-label="${ariaLabel}"]`;
  }

  // Use nth-child as fallback
  const parent = element.parentElement;
  if (parent) {
    const siblings = Array.from(parent.children);
    const index = siblings.indexOf(element);
    const tag = element.tagName.toLowerCase();
    const parentSelector = parent.id
      ? `#${parent.id}`
      : parent.tagName.toLowerCase();
    return `${parentSelector} > ${tag}:nth-child(${index + 1})`;
  }

  return element.tagName.toLowerCase();
}

// Determine element role
function getElementRole(element: Element): string {
  const tag = element.tagName.toLowerCase();
  const role = element.getAttribute("role");

  if (role) return role;

  // Map HTML tags to roles
  const roleMap: Record<string, string> = {
    button: "button",
    a: "link",
    input: "input",
    textarea: "textarea",
    select: "select",
    form: "form",
    img: "image",
    video: "video",
    h1: "heading",
    h2: "heading",
    h3: "heading",
    h4: "heading",
    h5: "heading",
    h6: "heading",
    nav: "navigation",
    main: "main",
    header: "header",
    footer: "footer",
  };

  if (roleMap[tag]) return roleMap[tag];

  // Check if it's a clickable div/span
  const onclick = element.getAttribute("onclick");
  const cursor = window.getComputedStyle(element).cursor;
  if (onclick || cursor === "pointer") {
    return "button";
  }

  return "generic";
}

// Extract semantic information from element
function extractSemanticElement(element: Element): SemanticElement | null {
  if (!isElementVisible(element)) {
    return null;
  }

  const rect = element.getBoundingClientRect();
  const scrollX = window.scrollX;
  const scrollY = window.scrollY;

  // Skip elements with no size
  if (rect.width === 0 || rect.height === 0) {
    return null;
  }

  const htmlElement = element as HTMLElement;
  const role = getElementRole(element);

  // Extract text (max 100 chars)
  const text = htmlElement.innerText?.trim().substring(0, 100) || undefined;

  // Skip generic elements without text or meaningful attributes
  if (role === "generic" && !text && !element.id) {
    return null;
  }

  const semanticElement: SemanticElement = {
    id: getElementId(element),
    role,
    tag: element.tagName.toLowerCase(),
    text,
    placeholder: (element as HTMLInputElement).placeholder || undefined,
    ariaLabel: element.getAttribute("aria-label") || undefined,
    value: (element as HTMLInputElement).value || undefined,
    href: (element as HTMLAnchorElement).href || undefined,
    src: (element as HTMLImageElement).src || undefined,
    bounds: {
      x: Math.round(rect.left + scrollX),
      y: Math.round(rect.top + scrollY),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    },
    selector: generateSelector(element),
    isVisible: true,
    isInViewport: isInViewport(rect, scrollX, scrollY),
  };

  return semanticElement;
}

/**
 * Extract semantic DOM from the current page
 * @param viewportOnly - Only extract elements in viewport (default: true)
 * @returns Structured semantic DOM
 */
export function extractSemanticDOM(viewportOnly: boolean = true): SemanticDOM {
  const startTime = performance.now();

  // Interactive element selectors
  const semanticSelectors = [
    "button",
    "a[href]",
    "input",
    "textarea",
    "select",
    "form",
    '[role="button"]',
    '[role="link"]',
    '[role="textbox"]',
    "[onclick]",
    '[contenteditable="true"]',
    "h1, h2, h3, h4, h5, h6",
    "img[alt]",
    "video",
    "[data-testid]",
    "[aria-label]",
    "nav a",
    "main",
    "header",
    "footer",
  ];

  const elements: SemanticElement[] = [];
  const seenElements = new Set<Element>();

  // Extract elements matching semantic selectors
  for (const selector of semanticSelectors) {
    try {
      const matches = document.querySelectorAll(selector);
      matches.forEach((element) => {
        if (seenElements.has(element)) return;
        seenElements.add(element);

        const semantic = extractSemanticElement(element);
        if (semantic && (!viewportOnly || semantic.isInViewport)) {
          elements.push(semantic);
        }
      });
    } catch (e) {
      // Invalid selector, skip
    }
  }

  const endTime = performance.now();
  console.log(
    `🔍 Semantic DOM extraction: ${elements.length} elements in ${(
      endTime - startTime
    ).toFixed(2)}ms`
  );

  return {
    title: document.title,
    url: window.location.href,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
    },
    elements: elements.slice(0, 300), // Limit to 300 elements max
    timestamp: Date.now(),
  };
}

/**
 * Query elements by selector
 */
export function querySelector(selector: string): SemanticElement[] {
  try {
    const matches = document.querySelectorAll(selector);
    const elements: SemanticElement[] = [];

    matches.forEach((element) => {
      const semantic = extractSemanticElement(element);
      if (semantic) {
        elements.push(semantic);
      }
    });

    return elements;
  } catch (e) {
    console.error("Invalid selector:", selector, e);
    return [];
  }
}

/**
 * Get element by semantic ID
 */
export function getElementBySemanticId(id: string): Element | null {
  for (const [element, elementId] of elementIdMap.entries()) {
    if (elementId === id) {
      return element;
    }
  }
  return null;
}

/**
 * Get text content of element by selector
 */
export function getTextContent(selector: string): string | null {
  try {
    const element = document.querySelector(selector);
    return element?.textContent?.trim() || null;
  } catch (e) {
    return null;
  }
}

/**
 * Get visible elements in current viewport
 */
export function getVisibleElements(): SemanticElement[] {
  return extractSemanticDOM(true).elements;
}

/**
 * Calculate DOM diff between two states
 */
export function calculateDOMDiff(
  oldDOM: SemanticDOM,
  newDOM: SemanticDOM
): {
  added: SemanticElement[];
  removed: string[];
  modified: Array<{ id: string; changes: Partial<SemanticElement> }>;
} {
  const oldMap = new Map(oldDOM.elements.map((e) => [e.id, e]));
  const newMap = new Map(newDOM.elements.map((e) => [e.id, e]));

  const added: SemanticElement[] = [];
  const removed: string[] = [];
  const modified: Array<{ id: string; changes: Partial<SemanticElement> }> = [];

  // Find added elements
  for (const [id, element] of newMap) {
    if (!oldMap.has(id)) {
      added.push(element);
    }
  }

  // Find removed elements
  for (const [id] of oldMap) {
    if (!newMap.has(id)) {
      removed.push(id);
    }
  }

  // Find modified elements
  for (const [id, newElement] of newMap) {
    const oldElement = oldMap.get(id);
    if (oldElement) {
      const changes: Partial<SemanticElement> = {};

      if (oldElement.text !== newElement.text) changes.text = newElement.text;
      if (oldElement.value !== newElement.value)
        changes.value = newElement.value;
      if (oldElement.isVisible !== newElement.isVisible)
        changes.isVisible = newElement.isVisible;
      if (oldElement.isInViewport !== newElement.isInViewport)
        changes.isInViewport = newElement.isInViewport;

      if (Object.keys(changes).length > 0) {
        modified.push({ id, changes });
      }
    }
  }

  return { added, removed, modified };
}
