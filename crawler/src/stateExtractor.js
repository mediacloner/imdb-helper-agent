/**
 * stateExtractor.js
 * Extracts structured page state by querying interactive DOM elements
 * and mapping them to the knowledge graph node schema.
 */

const INTERACTIVE_SELECTORS = [
  'a[href]',
  'button',
  'input',
  'select',
  '[role="button"]',
  '[role="link"]',
  '[role="tab"]',
  '[role="menuitem"]',
];

const MAX_ELEMENTS = 50;
const MAX_TEXT_LENGTH = 80;

/**
 * Converts a raw string into a URL/CSS-safe slug.
 * @param {string} str
 * @returns {string}
 */
function toSlug(str) {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
}

/**
 * Extracts the page state as a knowledge-graph node from a Playwright page.
 * @param {import('playwright').Page} page - The current Playwright page.
 * @param {string} nodeId - The unique node identifier for this page state.
 * @returns {Promise<Object>} A node object conforming to the knowledge graph schema.
 */
export async function extractState(page, nodeId) {
  const url = page.url();
  const title = await page.title();

  // Evaluate inside the browser context to gather element data efficiently.
  const elements = await page.evaluate(
    ({ selectors, maxElements, maxTextLength }) => {
      const combined = selectors.join(',');
      const allNodes = Array.from(document.querySelectorAll(combined));
      const results = [];

      for (const el of allNodes) {
        if (results.length >= maxElements) break;

        // Skip hidden elements
        const style = window.getComputedStyle(el);
        if (
          style.display === 'none' ||
          style.visibility === 'hidden' ||
          style.opacity === '0' ||
          el.offsetParent === null
        ) {
          continue;
        }

        // Determine ARIA role or fall back to tag name
        const role =
          el.getAttribute('role') ||
          el.tagName.toLowerCase();

        // Extract text content (trimmed, capped)
        const rawText = (el.innerText || el.value || el.placeholder || '').trim();
        const text = rawText.length > maxTextLength
          ? rawText.slice(0, maxTextLength)
          : rawText;

        const ariaLabel = el.getAttribute('aria-label') || '';

        // Build a reasonably unique CSS selector using id, class, or positional index
        let cssSelector = el.tagName.toLowerCase();
        if (el.id) {
          cssSelector = `#${el.id}`;
        } else if (el.className && typeof el.className === 'string' && el.className.trim()) {
          const firstClass = el.className.trim().split(/\s+/)[0];
          cssSelector = `${el.tagName.toLowerCase()}.${firstClass}`;
        }

        results.push({ role, text, ariaLabel, cssSelector });
      }

      return results;
    },
    { selectors: INTERACTIVE_SELECTORS, maxElements: MAX_ELEMENTS, maxTextLength: MAX_TEXT_LENGTH }
  );

  // Build element objects with generated IDs outside the browser context
  const available_elements = elements.map((el, index) => {
    const labelSource = el.ariaLabel || el.text || el.role || 'el';
    const slug = toSlug(labelSource) || el.role;
    const element_id = `${slug}_${index}`;

    return {
      element_id,
      role: el.role,
      css_selector: el.cssSelector,
      text: el.text,
      aria_label: el.ariaLabel,
    };
  });

  return {
    node_id: nodeId,
    type: 'page',
    url,
    description: title,
    capabilities: {},
    available_elements,
  };
}
