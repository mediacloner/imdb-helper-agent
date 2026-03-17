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

  if (allText.includes('filter') || allText.includes('genre'))
    caps.can_filter = true;

  if (allText.includes('sort') || allText.includes('ascending') || allText.includes('descending') || allText.includes('sort order'))
    caps.can_sort = true;

  if (allText.includes('detailed view') || allText.includes('grid view') || allText.includes('compact view'))
    caps.can_change_view = true;

  if (allText.includes('rate') || allText.includes('your rating') || allText.includes('star'))
    caps.can_rate = true;

  if (allText.includes('mark as watched') || allText.includes('watched'))
    caps.can_mark_watched = true;

  if (allText.includes('review') || allText.includes('write review') || allText.includes('user review'))
    caps.can_review = true;

  if (allText.includes('full cast') || allText.includes('cast & crew'))
    caps.can_view_full_cast = true;

  if (allText.includes('trailer') || allText.includes('watch trailer') || allText.includes('play trailer'))
    caps.can_watch_trailer = true;

  if (allText.includes('browse trailers') || allText.includes('browse trailer'))
    caps.can_browse_trailers = true;

  if (allText.includes('episode') || allText.includes('season'))
    caps.can_browse_episodes = true;

  if (allText.includes('share') || allText.includes('copy link') || allText.includes('share on social'))
    caps.can_share = true;

  if (allText.includes('trivia') || allText.includes('goofs') || allText.includes('quotes'))
    caps.can_view_trivia = true;

  if (allText.includes('photo') || allText.includes('gallery') || allText.includes('poster') || allText.includes('image'))
    caps.can_view_photos = true;

  if (allText.includes('award') || allText.includes('oscar') || allText.includes('won') || allText.includes('nominated'))
    caps.can_view_awards = true;

  if (allText.includes('metascore') || allText.includes('critic review') || allText.includes('/10') || allText.includes('rating'))
    caps.can_view_rating_details = true;

  if (allText.includes('add to list') || allText.includes('add name to') || allText.includes('another list'))
    caps.can_add_to_list = true;

  if (allText.includes('favorite') || allText.includes('favourite'))
    caps.can_add_to_favorites = true;

  if (allText.includes('agent info') || allText.includes('resume') || allText.includes('imdbpro'))
    caps.can_view_pro_info = true;

  if (allText.includes('poll') || allText.includes('vote'))
    caps.can_vote_poll = true;

  if (allText.includes('create account') || allText.includes('create an account') || allText.includes('register'))
    caps.can_create_account = true;

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
      // ── React fiber: walk up to find the nearest meaningful component name ──
      function getReactComponentName(el) {
        try {
          const fiberKey = Object.keys(el).find(
            k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
          );
          if (!fiberKey) return null;
          let fiber = el[fiberKey];
          for (let depth = 0; depth < 15 && fiber; depth++) {
            const type = fiber.type;
            if (type && typeof type === 'function') {
              const name = type.displayName || type.name;
              // Skip React internals and single-letter wrappers
              if (
                name && name.length > 2 &&
                !/^(t\d|_|Memo|ForwardRef|Fragment|Provider|Consumer|Suspense|StrictMode|Profiler)/.test(name)
              ) return name;
            }
            fiber = fiber.return;
          }
        } catch (_) {}
        return null;
      }

      // ── IMDb IPC component library + ARIA role heuristics ───────────────────
      function detectComponentType(el) {
        try {
          const cls = typeof el.className === 'string' ? el.className : '';
          const role = el.getAttribute('role') || '';
          const tag = el.tagName.toLowerCase();
          const hasExpanded = el.hasAttribute('aria-expanded');
          const hasPopup   = el.hasAttribute('aria-haspopup');
          const hasChecked = el.hasAttribute('aria-checked');

          // IPC accordion: outer container vs clickable header
          if (cls.includes('ipc-accordion')) return hasExpanded ? 'accordion_header' : 'accordion_container';
          // Any element with aria-expanded that lives inside an accordion = its header button
          if (hasExpanded && el.closest('[class*="ipc-accordion"]')) return 'accordion_header';
          // Genre / filter chip toggles
          if (cls.includes('ipc-chip')) return 'chip_toggle';
          // Star rating widget
          if (cls.includes('ipc-rating-star') || cls.includes('ipc-starbar')) return 'star_rating';
          // Hamburger / nav drawer triggers have both aria-expanded and aria-haspopup
          if (hasExpanded && hasPopup) return 'menu_trigger';
          // Generic disclosure buttons (tab headers, dropdowns, etc.)
          if (hasExpanded && (tag === 'button' || role === 'button')) return 'disclosure_button';
          // Toggle switches (e.g. "Include adult titles")
          if (hasChecked || role === 'switch') return 'toggle_switch';
          // Tabs, menuitems, combos
          if (role === 'tab') return 'tab';
          if (role === 'menuitem') return 'menu_item';
          if (role === 'combobox' || role === 'listbox') return 'dropdown';
        } catch (_) {}
        return null;
      }

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

        // Build unique CSS selector — priority: id > data-testid > full positional path
        let cssSelector;
        if (el.id) {
          cssSelector = `#${el.id}`;
        } else if (dataTestId) {
          cssSelector = `[data-testid="${dataTestId}"]`;
        } else {
          // Walk up to nearest ancestor with an id or data-testid to anchor the selector
          const tag = el.tagName.toLowerCase();
          const firstClass = (typeof el.className === 'string' && el.className.trim())
            ? `.${el.className.trim().split(/\s+/)[0]}`
            : '';

          let anchor = '';
          let ancestor = el.parentElement;
          while (ancestor) {
            if (ancestor.id) { anchor = `#${ancestor.id} `; break; }
            if (ancestor.getAttribute('data-testid')) { anchor = `[data-testid="${ancestor.getAttribute('data-testid')}"] `; break; }
            ancestor = ancestor.parentElement;
          }

          // nth-child within the whole document for uniqueness
          const allSame = Array.from(document.querySelectorAll(tag + firstClass));
          const idx = allSame.indexOf(el) + 1;
          cssSelector = `${anchor}${tag}${firstClass}:nth-of-type(${idx})`;
        }

        const href = (el.tagName.toLowerCase() === 'a') ? (el.getAttribute('href') || '') : '';

        // ARIA state snapshot (null = attribute absent, string = current value)
        const ariaExpanded = el.getAttribute('aria-expanded');
        const ariaSelected = el.getAttribute('aria-selected');
        const ariaChecked  = el.getAttribute('aria-checked');
        const ariaControls = el.getAttribute('aria-controls');

        // Component semantics
        const componentType   = detectComponentType(el);
        const reactComponent  = getReactComponentName(el);

        results.push({
          role, text, ariaLabel, cssSelector, dataTestId, href,
          ariaExpanded, ariaSelected, ariaChecked, ariaControls,
          componentType, reactComponent,
        });
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
      href: el.href || undefined,
      // ARIA state at crawl time (tells recorder the initial component state)
      ...(el.ariaExpanded !== null && { aria_expanded: el.ariaExpanded }),
      ...(el.ariaSelected !== null && { aria_selected: el.ariaSelected }),
      ...(el.ariaChecked  !== null && { aria_checked:  el.ariaChecked }),
      ...(el.ariaControls             && { aria_controls: el.ariaControls }),
      // Semantic component type (drives interaction strategy in recorder)
      ...(el.componentType            && { component_type: el.componentType }),
      // React component name from fiber tree (richer than HTML tag alone)
      ...(el.reactComponent           && { react_component: el.reactComponent }),
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
