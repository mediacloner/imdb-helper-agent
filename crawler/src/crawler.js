/**
 * crawler.js
 * Main crawl orchestrator. Navigates IMDB pages using Playwright, extracts
 * page state nodes and interaction edges, and returns a knowledge graph.
 */

import { chromium } from 'playwright';
import { v4 as uuidv4 } from 'uuid';
import { randomDelay, getRandomUserAgent } from './humanBehavior.js';
import { extractState } from './stateExtractor.js';

/**
 * Classifies a URL into a structural page-type bucket.
 * Used to prevent BFS from flooding the queue with pages that are
 * structurally identical (e.g. 50 different /title/ttXXXX pages).
 * @param {string} url
 * @returns {string}
 */
function getPageType(url) {
  try {
    const p = new URL(url).pathname.replace(/\/$/, '');
    if (/^\/title\/tt\d+\/fullcredits/.test(p))    return 'title_cast';
    if (/^\/title\/tt\d+\/reviews/.test(p))         return 'title_reviews';
    if (/^\/title\/tt\d+\/episodes/.test(p))        return 'title_episodes';
    if (/^\/title\/tt\d+\/trivia/.test(p))          return 'title_trivia';
    if (/^\/title\/tt\d+\/awards/.test(p))          return 'title_awards';
    if (/^\/title\/tt\d+\/technical/.test(p))       return 'title_technical';
    if (/^\/title\/tt\d+\/releaseinfo/.test(p))     return 'title_release';
    if (/^\/title\/tt\d+\/parentalguide/.test(p))   return 'title_parental';
    if (/^\/title\/tt\d+\/soundtrack/.test(p))      return 'title_soundtrack';
    if (/^\/title\/tt\d+\/plotsummary/.test(p))     return 'title_plot';
    if (/^\/title\/tt\d+\/companycredits/.test(p))  return 'title_companies';
    if (/^\/title\/tt\d+\/.+/.test(p))              return 'title_sub';
    if (/^\/title\/tt\d+/.test(p))                  return 'title_main';
    if (/^\/name\/nm\d+\/.+/.test(p))               return 'person_sub';
    if (/^\/name\/nm\d+/.test(p))                   return 'person_main';
    if (/^\/find/.test(p))                          return 'search';
    if (/^\/chart\//.test(p))                       return 'chart';
    if (/^\/search\/title/.test(p))                 return 'browse';
    if (/^\/search\/name/.test(p))                  return 'browse_names';
    if (/^\/news\//.test(p))                        return 'news';
    if (/^\/awards-central|\/oscars/.test(p))       return 'awards_central';
    if (/^\/calendar/.test(p))                      return 'calendar';
    if (/^\/interest\//.test(p))                    return 'interest';
    if (p === '' || p === '/')                      return 'home';

    // Auto-discover: extract a structural type from the URL shape so unknown
    // sub-pages get their own quota instead of all sharing 'other'.
    const titleSub = p.match(/^\/title\/tt\d+\/([^/]+)/);
    if (titleSub) return `title_${titleSub[1].toLowerCase()}`;

    const personSub = p.match(/^\/name\/nm\d+\/([^/]+)/);
    if (personSub) return `person_${personSub[1].toLowerCase()}`;

    // Fall back to the first path segment (e.g. /user/ → 'user', /genre/ → 'genre')
    const topSegment = p.match(/^\/([^/]+)/);
    if (topSegment) return `top_${topSegment[1].toLowerCase()}`;

    return 'other';
  } catch {
    return 'other';
  }
}


/**
 * Converts a URL into a safe slug for use in node IDs.
 * @param {string} url
 * @returns {string}
 */
function urlToSlug(url) {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/^\/|\/$/g, '') || 'home';
    return path
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 50);
  } catch {
    return 'unknown';
  }
}

/**
 * Attempts to dismiss cookie consent / GDPR banners by clicking known selectors.
 * Errors are silently swallowed since banners may not be present on every page.
 * @param {import('playwright').Page} page
 */
async function dismissCookieBanner(page) {
  const bannerSelectors = [
    '#onetrust-accept-btn-handler',
    'button[id*="accept"]',
    'button[class*="accept"]',
    'button[aria-label*="Accept"]',
    '[data-testid="accept-button"]',
    'button:has-text("Accept All")',
    'button:has-text("Accept Cookies")',
    'button:has-text("I Accept")',
    'button:has-text("Accept")',
  ];

  for (const selector of bannerSelectors) {
    try {
      const btn = await page.$(selector);
      if (btn) {
        await btn.click({ timeout: 3000 });
        await randomDelay(400, 800);
        break;
      }
    } catch {
      // Banner not found or click failed — move on
    }
  }
}

/**
 * Extracts all same-domain anchor hrefs from the current page.
 * @param {import('playwright').Page} page
 * @param {string} baseDomain - The hostname to restrict links to (e.g. "www.imdb.com").
 * @returns {Promise<string[]>} Deduplicated list of absolute URLs on the same domain.
 */
async function extractSameDomainLinks(page, baseDomain) {
  const hrefs = await page.evaluate(() =>
    Array.from(document.querySelectorAll('a[href]')).map((a) => a.href)
  );

  const unique = new Set();
  for (const href of hrefs) {
    try {
      const parsed = new URL(href);
      // Same hostname only, no hash-only links, no mailto/tel
      if (
        parsed.hostname === baseDomain &&
        parsed.protocol === 'https:' &&
        !href.includes('#') &&
        parsed.pathname !== '/'
      ) {
        // Skip low-value editorial / media-viewer pages
        if (SKIP_URL_PATTERNS.some(p => parsed.pathname.includes(p) || href.includes(p))) continue;

        // Preserve query strings for episode season pages and filtered searches
        // (so ?season=1 and ?season=2 are treated as separate pages)
        const keepQuery =
          (parsed.pathname.includes('/episodes/') && parsed.searchParams.has('season')) ||
          (parsed.pathname.includes('/search/title') && parsed.search);
        const normalized = keepQuery
          ? `${parsed.origin}${parsed.pathname}${parsed.search}`
          : `${parsed.origin}${parsed.pathname}`.replace(/\/$/, '');
        unique.add(normalized);
      }
    } catch {
      // Malformed href — skip
    }
  }

  return Array.from(unique);
}

/**
 * Visits the homepage and extracts unique same-domain links found inside
 * header/nav and footer elements. These represent the site's own declared
 * structure and are used as high-priority seeds before BFS begins.
 * @param {import('playwright').Page} page
 * @param {string} baseDomain
 * @returns {Promise<string[]>}
 */
async function discoverNavEntryPoints(page, baseDomain) {
  try {
    await page.goto(`https://${baseDomain}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    await dismissCookieBanner(page);
  } catch {
    return [];
  }

  const hrefs = await page.evaluate(() => {
    const areas = [
      ...document.querySelectorAll('header a[href], nav a[href], [role="navigation"] a[href]'),
      ...document.querySelectorAll('footer a[href], [role="contentinfo"] a[href]'),
    ];
    return areas.map(a => a.href);
  });

  const unique = new Set();
  for (const href of hrefs) {
    try {
      const parsed = new URL(href);
      if (
        parsed.hostname === baseDomain &&
        parsed.protocol === 'https:' &&
        !href.includes('#') &&
        parsed.pathname !== '/'
      ) {
        if (SKIP_URL_PATTERNS.some(p => parsed.pathname.includes(p) || href.includes(p))) continue;
        unique.add(`${parsed.origin}${parsed.pathname}`.replace(/\/$/, ''));
      }
    } catch { /* skip malformed */ }
  }

  const discovered = Array.from(unique);
  console.log(`[crawler] Discovered ${discovered.length} entry points from nav/footer`);
  return discovered;
}

/**
 * Crawls a website starting from `startUrl`, building a knowledge graph of
 * page-state nodes and interaction edges.
 *
 * @param {string} startUrl - The URL to begin crawling from.
 * @param {number} [maxPages=10] - Maximum number of pages to visit.
 * @returns {Promise<{ nodes: Object[], edges: Object[] }>}
 */
// Key IMDB page types that users commonly ask about.
// These are seeded directly so the graph covers important states
// regardless of which links BFS happens to follow first.
const IMDB_SEED_PAGES = [
  // ── Core navigation ────────────────────────────────────────────────
  'https://www.imdb.com',
  'https://www.imdb.com/find/?q=inception&s=tt',

  // ── Movie pages ────────────────────────────────────────────────────
  'https://www.imdb.com/title/tt1375666/',                   // Inception
  'https://www.imdb.com/title/tt1375666/fullcredits',        // Inception cast
  'https://www.imdb.com/title/tt1375666/reviews',            // Inception reviews
  'https://www.imdb.com/title/tt1375666/trivia',             // Inception trivia
  'https://www.imdb.com/title/tt1375666/awards',             // Inception awards
  'https://www.imdb.com/title/tt1375666/technical',          // Inception technical specs
  'https://www.imdb.com/title/tt1375666/releaseinfo',        // Inception release dates
  'https://www.imdb.com/title/tt1375666/parentalguide',      // Inception parental guide
  'https://www.imdb.com/title/tt1375666/soundtrack',         // Inception soundtrack
  'https://www.imdb.com/title/tt1375666/plotsummary',        // Inception plot summaries
  'https://www.imdb.com/title/tt1375666/companycredits',     // Inception company credits
  'https://www.imdb.com/title/tt0133093/',                   // The Matrix
  'https://www.imdb.com/title/tt0133093/fullcredits',        // Matrix cast
  'https://www.imdb.com/title/tt0468569/',                   // The Dark Knight
  'https://www.imdb.com/title/tt0068646/',                   // The Godfather
  'https://www.imdb.com/title/tt0111161/',                   // The Shawshank Redemption

  // ── TV show pages ──────────────────────────────────────────────────
  'https://www.imdb.com/title/tt0106004/',                   // Frasier
  'https://www.imdb.com/title/tt0106004/episodes/?season=1', // Frasier S1
  'https://www.imdb.com/title/tt0106004/episodes/?season=2', // Frasier S2
  'https://www.imdb.com/title/tt0106004/fullcredits',        // Frasier cast
  'https://www.imdb.com/title/tt0903747/',                   // Breaking Bad
  'https://www.imdb.com/title/tt0903747/episodes/?season=1', // Breaking Bad S1
  'https://www.imdb.com/title/tt0903747/fullcredits',        // Breaking Bad cast
  'https://www.imdb.com/title/tt0944947/',                   // Game of Thrones
  'https://www.imdb.com/title/tt0944947/episodes/?season=1', // GoT S1
  'https://www.imdb.com/title/tt0098904/',                   // Seinfeld
  'https://www.imdb.com/title/tt0098904/episodes/?season=1', // Seinfeld S1
  'https://www.imdb.com/title/tt0108778/',                   // Friends
  'https://www.imdb.com/title/tt0108778/episodes/?season=1', // Friends S1
  'https://www.imdb.com/title/tt4574334/',                   // Stranger Things
  'https://www.imdb.com/title/tt4574334/episodes/?season=1', // Stranger Things S1

  // ── Person pages ───────────────────────────────────────────────────
  'https://www.imdb.com/name/nm0000206/',                    // Keanu Reeves
  'https://www.imdb.com/name/nm0000206/bio',                 // Keanu Reeves bio
  'https://www.imdb.com/name/nm0000138/',                    // Leonardo DiCaprio
  'https://www.imdb.com/name/nm0634240/',                    // Christopher Nolan
  'https://www.imdb.com/search/name/?birth_monthday=06-11', // Name search (browse)

  // ── Charts ─────────────────────────────────────────────────────────
  'https://www.imdb.com/chart/top/',
  'https://www.imdb.com/chart/toptv/',
  'https://www.imdb.com/chart/moviemeter/',
  'https://www.imdb.com/chart/tvmeter/',
  'https://www.imdb.com/chart/boxoffice/',
  'https://www.imdb.com/chart/starmeter/',

  // ── Browse & language search ───────────────────────────────────────
  'https://www.imdb.com/search/title/',
  'https://www.imdb.com/search/title/?languages=es&sort=year,desc',
  'https://www.imdb.com/search/title/?languages=fr&sort=year,desc',
  'https://www.imdb.com/interest/all/',

  // ── News, Calendar, Awards ─────────────────────────────────────────
  'https://www.imdb.com/news/movie/',
  'https://www.imdb.com/news/tv/',
  'https://www.imdb.com/calendar',
  'https://www.imdb.com/awards-central/',
  'https://www.imdb.com/oscars/',
];

// URL path prefixes / substrings to skip — these are low-value editorial /
// media-viewer pages that waste crawl slots and add no navigation signal.
const SKIP_URL_PATTERNS = [
  '/mediaviewer/', '/gallery/',
  '/sxsw/', '/festival-central/', '/starmeterawards/',
  '/imdbpicks/', '/spotlight/', '/originals/',
  '/what-to-watch/', '/whats-on-tv/',
  '/family-entertainment-guide/', '/india/',
  '/showtimes/', '/trailers',
  '/video/',       // individual clip pages
  '/event/',
  '/poll/',
  '/list/',        // user-created lists (thousands of permutations)
];

export async function crawl(startUrl, maxPages = 10) {
  const userAgent = getRandomUserAgent();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent,
    viewport: { width: 1280, height: 800 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
  });

  const page = await context.newPage();

  const nodes = [];
  const edges = [];

  // Maps URL -> node_id for edge construction
  const urlToNodeId = new Map();

  let baseDomain;
  try {
    baseDomain = new URL(startUrl).hostname;
  } catch {
    baseDomain = '';
  }

  const visited = new Set();
  let pageIndex = 0;

  // Phase 0: discover entry points from the site's own nav and footer.
  // These go at the front of the queue so structurally unique sections
  // found by IMDB itself are visited before generic BFS exploration.
  console.log('[crawler] Phase 0: discovering nav/footer entry points…');
  const navEntryPoints = await discoverNavEntryPoints(page, baseDomain);
  // The homepage was already navigated during discovery — extract its state now
  // so BFS doesn't waste a slot re-fetching it.
  try {
    const homeNodeId = 'state_home_0';
    const homeNode = await extractState(page, homeNodeId);
    nodes.push(homeNode);
    urlToNodeId.set(`https://${baseDomain}`, homeNodeId);
    visited.add(`https://${baseDomain}`);
    visited.add(`https://${baseDomain}/`);
    pageIndex++;
    console.log(`[crawler] Captured homepage node with ${homeNode.available_elements.length} elements`);
  } catch (e) {
    console.warn(`[crawler] Could not capture homepage state after discovery: ${e.message}`);
  }

  // Merge: nav/footer discoveries first, then hardcoded seeds, then startUrl
  const seedSet = new Set([
    ...navEntryPoints,
    ...IMDB_SEED_PAGES.map(u => u.replace(/\/$/, '')),
  ]);
  const queue = [...seedSet];
  if (!seedSet.has(startUrl.replace(/\/$/, ''))) queue.push(startUrl);

  // Track source+target pairs to avoid duplicate edges
  const edgeSignatures = new Set();
  // Max outgoing edges per node — prevents list pages (full cast, charts) exploding the graph
  const MAX_EDGES_PER_NODE = 30;
  // Tracks how many BFS-discovered (non-seed) pages have been enqueued per type.
  // Budget is split evenly across ~20 discoverable types so BFS fills the
  // remaining slots after seeds regardless of maxPages.
  const bfsTypeCount = new Map();
  const ESTIMATED_TYPES = 20;
  const MAX_BFS_PAGES_PER_TYPE = Math.max(2, Math.ceil((maxPages - queue.length) / ESTIMATED_TYPES));
  // Tracks which structural types have been fully visited (at least one page seen)
  const visitedTypes = new Set();

  try {
    while (queue.length > 0 && pageIndex < maxPages) {
      const url = queue.shift();

      if (visited.has(url)) continue;
      visited.add(url);

      const currentType = getPageType(url);
      visitedTypes.add(currentType);
      console.log(`[crawler] Visiting (${pageIndex + 1}/${maxPages}) [${currentType}]: ${url}`);

      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        // Give JS-heavy pages extra time to settle after initial load
        await page.waitForTimeout(3000);
      } catch (navErr) {
        console.warn(`[crawler] Navigation failed for ${url}: ${navErr.message}`);
        continue;
      }

      await randomDelay(1000, 3000);
      await dismissCookieBanner(page);

      const slug = urlToSlug(url);
      const nodeId = `state_${slug}_${pageIndex}`;
      urlToNodeId.set(url, nodeId);

      let node;
      try {
        node = await extractState(page, nodeId);
      } catch (extractErr) {
        console.warn(`[crawler] State extraction failed for ${url}: ${extractErr.message}`);
        pageIndex++;
        continue;
      }

      nodes.push(node);
      console.log(`[crawler] Extracted node "${nodeId}" with ${node.available_elements.length} elements`);

      // Gather same-domain links to enqueue and build edges
      let links = [];
      try {
        links = await extractSameDomainLinks(page, baseDomain);
      } catch (linkErr) {
        console.warn(`[crawler] Link extraction failed for ${url}: ${linkErr.message}`);
      }

      for (const link of links) {
        // Pre-assign node IDs for targets we haven't visited yet so edges are consistent
        if (!urlToNodeId.has(link)) {
          const targetSlug = urlToSlug(link);
          const targetIndex = visited.size + queue.indexOf(link);
          urlToNodeId.set(link, `state_${targetSlug}_${targetIndex}`);
        }

        // Enqueue unvisited BFS links.
        // - Unseen types always get enqueued (bypass page cap) so every structural
        //   type is covered at least once regardless of maxPages.
        // - Already-seen types are capped at MAX_BFS_PAGES_PER_TYPE and respect maxPages.
        if (!visited.has(link) && !queue.includes(link)) {
          const linkType = getPageType(link);
          const typeCount = bfsTypeCount.get(linkType) || 0;
          const typeUnseen = !visitedTypes.has(linkType);
          if (typeUnseen || (typeCount < MAX_BFS_PAGES_PER_TYPE && pageIndex + queue.length < maxPages)) {
            queue.push(link);
            bfsTypeCount.set(linkType, typeCount + 1);
          }
        }

        const targetNodeId = urlToNodeId.get(link);

        // Skip duplicate edges (same source → target)
        const edgeSig = `${nodeId}→${targetNodeId}`;
        if (edgeSignatures.has(edgeSig)) continue;
        edgeSignatures.add(edgeSig);

        // Cap outgoing edges per node to keep the graph manageable
        const currentNodeEdges = edges.filter(e => e.source_node === nodeId).length;
        if (currentNodeEdges >= MAX_EDGES_PER_NODE) continue;

        // Find the specific element on the source page whose href points to this link.
        // Only match elements that actually link to this URL — no fallback to random elements,
        // which previously caused "Watchlist" to appear as the label for unrelated links.
        const linkPath = (() => { try { return new URL(link).pathname.replace(/\/$/, ''); } catch { return ''; } })();
        const matchingElement = node.available_elements.find(el =>
          el.href && (el.href === link || el.href.startsWith(link) ||
            (linkPath && el.href.includes(linkPath)))
        );

        // Use human-readable label (text or aria-label) as the target so the recorder
        // and LLM can understand what to click — NOT the internal element_id slug.
        const targetElementId = matchingElement
          ? (matchingElement.text || matchingElement.aria_label || matchingElement.css_selector || null)
          : null;

        edges.push({
          edge_id: `edge_${uuidv4()}`,
          source_node: nodeId,
          target_node: targetNodeId,
          interaction_type: 'click',
          target_element_id: targetElementId,
        });
      }

      // ── Search-query edges ──────────────────────────────────────────────────
      // For any page that has the IMDb search bar, add an explicit search_query
      // edge pointing to the /find/ results state. This lets the graph represent
      // "type a query in the search box" as a real navigable step — not just a
      // link click — so the RAG can build proper search instructions.
      if (node.capabilities.can_search) {
        const searchUrl = 'https://www.imdb.com/find/';
        // Ensure the search-results node exists in the map
        if (!urlToNodeId.has(searchUrl)) {
          urlToNodeId.set(searchUrl, `state_find_0`);
        }
        const searchTargetId = urlToNodeId.get(searchUrl);
        const searchEdgeSig = `${nodeId}→${searchTargetId}__search`;
        if (!edgeSignatures.has(searchEdgeSig)) {
          edgeSignatures.add(searchEdgeSig);
          // Find the search input element for its CSS selector
          const searchEl = node.available_elements.find(el =>
            el.css_selector === '#suggestion-search' ||
            (el.aria_label || '').toLowerCase().includes('search imdb') ||
            (el.aria_label || '').toLowerCase().includes('search')
          );
          edges.push({
            edge_id: `edge_${uuidv4()}`,
            source_node: nodeId,
            target_node: searchTargetId,
            interaction_type: 'search_query',
            target_element_id: searchEl ? (searchEl.css_selector || '#suggestion-search') : '#suggestion-search',
          });
        }
      }

      pageIndex++;
    }
  } finally {
    await browser.close();
  }

  console.log(`[crawler] Crawl complete. Nodes: ${nodes.length}, Edges: ${edges.length}`);
  console.log(`[crawler] Page types covered (${visitedTypes.size}): ${[...visitedTypes].sort().join(', ')}`);

  return { nodes, edges, visitedTypes: [...visitedTypes].sort() };
}
