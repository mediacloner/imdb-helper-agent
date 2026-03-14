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

// Max meaningful elements per page (after filtering noise)
const MAX_ELEMENTS = 60;
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
 * Infers a capabilities map from the set of extracted elements.
 * @param {Array} elements
 * @returns {Object}
 */
function inferCapabilities(elements) {
  const caps = {};
  const allText = elements.map(e => `${e.text} ${e.ariaLabel} ${e.cssSelector}`).join(' ').toLowerCase();

  if (elements.some(e => e.cssSelector.includes('suggestion-search') || (e.ariaLabel || '').toLowerCase().includes('search imdb')))
    caps.can_search = true;

  if (allText.includes('watchlist') || allText.includes('add to watchlist'))
    caps.can_add_to_watchlist = true;

  if (allText.includes('sign in') || allText.includes('log in'))
    caps.can_sign_in = true;

  if (allText.includes('filter') || allText.includes('sort by') || allText.includes('genre'))
    caps.can_filter = true;

  if (allText.includes('rate') || allText.includes('your rating') || allText.includes('star'))
    caps.can_rate = true;

  if (allText.includes('review') || allText.includes('write review') || allText.includes('user review'))
    caps.can_review = true;

  if (allText.includes('full cast') || allText.includes('cast & crew'))
    caps.can_view_full_cast = true;

  if (allText.includes('trailer') || allText.includes('watch trailer') || allText.includes('video'))
    caps.can_watch_trailer = true;

  if (allText.includes('episode') || allText.includes('season'))
    caps.can_browse_episodes = true;

  if (allText.includes('share') || allText.includes('copy link'))
    caps.can_share = true;

  if (allText.includes('trivia') || allText.includes('goofs') || allText.includes('quotes'))
    caps.can_view_trivia = true;

  if (elements.some(e => e.role === 'input' && (e.ariaLabel || '').toLowerCase().includes('location')))
    caps.can_search_showtimes = true;

  return caps;
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

  const elements = await page.evaluate(
    ({ selectors, maxElements, maxTextLength }) => {
      const combined = selectors.join(',');
      const allNodes = Array.from(document.querySelectorAll(combined));
      const results = [];
      // Track seen (text+role) combos to skip pure duplicates (e.g. 51x watchlist buttons)
      const seenSignatures = new Set();

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

        const role = el.getAttribute('role') || el.tagName.toLowerCase();
        const rawText = (el.innerText || el.value || el.placeholder || '').trim();
        const text = rawText.length > maxTextLength ? rawText.slice(0, maxTextLength) : rawText;
        const ariaLabel = el.getAttribute('aria-label') || '';
        const dataTestId = el.getAttribute('data-testid') || '';

        // Dedup: skip elements that have identical role+text+ariaLabel (pure nav/footer repeats)
        const signature = `${role}|${text}|${ariaLabel}`;
        if (seenSignatures.has(signature) && !el.id && !dataTestId) continue;
        seenSignatures.add(signature);

        // Build unique CSS selector — priority: id > data-testid > nth-of-type fallback
        let cssSelector;
        if (el.id) {
          cssSelector = `#${el.id}`;
        } else if (dataTestId) {
          cssSelector = `[data-testid="${dataTestId}"]`;
        } else {
          // Count siblings of same tag to build nth-of-type selector
          const parent = el.parentElement;
          const tag = el.tagName.toLowerCase();
          if (parent) {
            const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            const idx = siblings.indexOf(el) + 1;
            const parentId = parent.id ? `#${parent.id} ` : '';
            const firstClass = (typeof el.className === 'string' && el.className.trim())
              ? `.${el.className.trim().split(/\s+/)[0]}`
              : '';
            cssSelector = `${parentId}${tag}${firstClass}:nth-of-type(${idx})`;
          } else {
            cssSelector = tag;
          }
        }

        results.push({ role, text, ariaLabel, cssSelector, dataTestId });
      }

      return results;
    },
    { selectors: INTERACTIVE_SELECTORS, maxElements: MAX_ELEMENTS, maxTextLength: MAX_TEXT_LENGTH }
  );

  const capabilities = inferCapabilities(elements);

  // Build element objects with globally unique IDs (prefixed with nodeId)
  const available_elements = elements.map((el, index) => {
    const labelSource = el.ariaLabel || el.text || el.role || 'el';
    const slug = toSlug(labelSource) || el.role;
    const element_id = `${nodeId}__${slug}_${index}`;

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
    capabilities,
    available_elements,
  };
}
