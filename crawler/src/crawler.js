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
  const hrefs = await page.evaluate(() => {
    const urls = [];

    // Standard anchor links
    for (const a of document.querySelectorAll('a[href]')) {
      urls.push(a.href);
    }

    // Form actions — captures /search/title/ and /find/ submission targets
    for (const form of document.querySelectorAll('form[action]')) {
      try {
        const action = new URL(form.action, location.href);
        // Only plain GET forms whose action is a same-domain path
        if ((!form.method || form.method.toLowerCase() === 'get') && action.hostname === location.hostname) {
          urls.push(action.href.split('?')[0]); // path only; params come from selects below
        }
      } catch { /* ignore malformed */ }
    }

    // Elements with data-href or data-url attributes (some IMDB widgets use these)
    for (const el of document.querySelectorAll('[data-href], [data-url]')) {
      const val = el.getAttribute('data-href') || el.getAttribute('data-url') || '';
      if (val.startsWith('/') || val.startsWith('http')) urls.push(val);
    }

    return urls;
  });

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
// Known title IDs that are safe to crawl and include in the graph.
// BFS-discovered pages for any OTHER title are skipped to prevent the graph
// from being flooded with hundreds of random upcoming-movie pages.
const KNOWN_TITLE_IDS = new Set([
  // Movies
  'tt1375666', 'tt0133093', 'tt0234215', 'tt0242653', 'tt0468569',
  'tt0816692', 'tt0068646', 'tt0111161', 'tt0110912', 'tt0109830',
  'tt4154796', 'tt0499549', 'tt0120338', 'tt0099685', 'tt0137523',
  'tt0102926', 'tt0108052', 'tt0088247', 'tt0103064', 'tt0078748',
  'tt0090605', 'tt0107290', 'tt0076759', 'tt0110357', 'tt0088763',
  // TV shows
  'tt0098904', 'tt0903747', 'tt0944947', 'tt0108778', 'tt0141842',
  'tt4574334', 'tt0386676', 'tt0306414', 'tt0106004', 'tt0096697',
  'tt0106179', 'tt0411008', 'tt0412142', 'tt4786824', 'tt7660850',
]);

// Key IMDB page types that users commonly ask about.
// These are seeded directly so the graph covers important states
// regardless of which links BFS happens to follow first.
const IMDB_SEED_PAGES = [
  // ── Core navigation ────────────────────────────────────────────────
  'https://www.imdb.com',
  'https://www.imdb.com/find/?q=inception&s=tt',

  // ── Inception (full sub-page coverage) ────────────────────────────
  'https://www.imdb.com/title/tt1375666/',
  'https://www.imdb.com/title/tt1375666/fullcredits',
  'https://www.imdb.com/title/tt1375666/reviews',
  'https://www.imdb.com/title/tt1375666/trivia',
  'https://www.imdb.com/title/tt1375666/goofs',
  'https://www.imdb.com/title/tt1375666/quotes',
  'https://www.imdb.com/title/tt1375666/awards',
  'https://www.imdb.com/title/tt1375666/technical',
  'https://www.imdb.com/title/tt1375666/releaseinfo',
  'https://www.imdb.com/title/tt1375666/parentalguide',
  'https://www.imdb.com/title/tt1375666/soundtrack',
  'https://www.imdb.com/title/tt1375666/plotsummary',
  'https://www.imdb.com/title/tt1375666/companycredits',
  'https://www.imdb.com/title/tt1375666/locations',
  'https://www.imdb.com/title/tt1375666/business',
  'https://www.imdb.com/title/tt1375666/faq',
  'https://www.imdb.com/title/tt1375666/keywords',
  'https://www.imdb.com/title/tt1375666/movieconnections',

  // ── The Matrix ────────────────────────────────────────────────────
  'https://www.imdb.com/title/tt0133093/',
  'https://www.imdb.com/title/tt0133093/fullcredits',
  'https://www.imdb.com/title/tt0133093/reviews',
  'https://www.imdb.com/title/tt0133093/trivia',
  'https://www.imdb.com/title/tt0133093/awards',

  // ── The Dark Knight ───────────────────────────────────────────────
  'https://www.imdb.com/title/tt0468569/',
  'https://www.imdb.com/title/tt0468569/fullcredits',
  'https://www.imdb.com/title/tt0468569/reviews',
  'https://www.imdb.com/title/tt0468569/awards',

  // ── The Godfather ─────────────────────────────────────────────────
  'https://www.imdb.com/title/tt0068646/',
  'https://www.imdb.com/title/tt0068646/fullcredits',
  'https://www.imdb.com/title/tt0068646/awards',

  // ── The Shawshank Redemption ──────────────────────────────────────
  'https://www.imdb.com/title/tt0111161/',
  'https://www.imdb.com/title/tt0111161/reviews',
  'https://www.imdb.com/title/tt0111161/awards',

  // ── TV show pages ──────────────────────────────────────────────────
  'https://www.imdb.com/title/tt0903747/',                   // Breaking Bad
  'https://www.imdb.com/title/tt0903747/episodes/?season=1',
  'https://www.imdb.com/title/tt0903747/episodes/?season=2',
  'https://www.imdb.com/title/tt0903747/fullcredits',
  'https://www.imdb.com/title/tt0903747/reviews',
  'https://www.imdb.com/title/tt0903747/awards',
  'https://www.imdb.com/title/tt0944947/',                   // Game of Thrones
  'https://www.imdb.com/title/tt0944947/episodes/?season=1',
  'https://www.imdb.com/title/tt0944947/fullcredits',
  'https://www.imdb.com/title/tt0098904/',                   // Seinfeld
  'https://www.imdb.com/title/tt0098904/episodes/?season=1',
  'https://www.imdb.com/title/tt0108778/',                   // Friends
  'https://www.imdb.com/title/tt0108778/episodes/?season=1',
  'https://www.imdb.com/title/tt4574334/',                   // Stranger Things
  'https://www.imdb.com/title/tt4574334/episodes/?season=1',
  'https://www.imdb.com/title/tt0141842/',                   // The Sopranos
  'https://www.imdb.com/title/tt0141842/episodes/?season=1',
  'https://www.imdb.com/title/tt0306414/',                   // The Wire
  'https://www.imdb.com/title/tt0106004/',                   // Frasier
  'https://www.imdb.com/title/tt0106004/episodes/?season=1',

  // ── Person pages ───────────────────────────────────────────────────
  'https://www.imdb.com/name/nm0000206/',                    // Keanu Reeves
  'https://www.imdb.com/name/nm0000206/bio',
  'https://www.imdb.com/name/nm0000206/awards',
  'https://www.imdb.com/name/nm0000138/',                    // Leonardo DiCaprio
  'https://www.imdb.com/name/nm0000138/bio',
  'https://www.imdb.com/name/nm0000138/awards',
  'https://www.imdb.com/name/nm0634240/',                    // Christopher Nolan
  'https://www.imdb.com/name/nm0634240/awards',
  'https://www.imdb.com/name/nm0000158/',                    // Tom Hanks
  'https://www.imdb.com/name/nm0000158/bio',
  'https://www.imdb.com/name/nm0000093/',                    // Brad Pitt
  'https://www.imdb.com/name/nm0000093/awards',

  // ── Charts ─────────────────────────────────────────────────────────
  'https://www.imdb.com/chart/top/',
  'https://www.imdb.com/chart/bottom/',                      // Bottom 100
  'https://www.imdb.com/chart/toptv/',
  'https://www.imdb.com/chart/moviemeter/',
  'https://www.imdb.com/chart/tvmeter/',
  'https://www.imdb.com/chart/boxoffice/',
  'https://www.imdb.com/chart/starmeter/',

  // ── Advanced search / filter pages ────────────────────────────────
  'https://www.imdb.com/search/title/',
  'https://www.imdb.com/search/title/?title_type=feature',
  'https://www.imdb.com/search/title/?title_type=short',
  'https://www.imdb.com/search/title/?title_type=tv_movie',
  'https://www.imdb.com/search/title/?title_type=tv_miniseries',
  // Genre filters
  'https://www.imdb.com/search/title/?genres=horror',
  'https://www.imdb.com/search/title/?genres=horror&release_date=1980-01-01,1989-12-31&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?genres=comedy',
  'https://www.imdb.com/search/title/?genres=documentary',
  'https://www.imdb.com/search/title/?genres=animation',
  'https://www.imdb.com/search/title/?genres=war&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?genres=biography&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?genres=biography&keywords=musician&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?genres=crime&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?genres=sci-fi&sort=user_rating,desc',
  // Language filters — key world cinema languages
  'https://www.imdb.com/search/title/?languages=es&sort=year,desc',
  'https://www.imdb.com/search/title/?languages=fr&sort=year,desc',
  'https://www.imdb.com/search/title/?languages=it&sort=year,desc',
  'https://www.imdb.com/search/title/?languages=ja&sort=year,desc',
  'https://www.imdb.com/search/title/?languages=hi&sort=user_rating,desc',   // Hindi / Bollywood
  'https://www.imdb.com/search/title/?languages=ko&sort=user_rating,desc',   // Korean
  'https://www.imdb.com/search/title/?languages=de&sort=year,desc',          // German
  // Keyword / topic searches
  'https://www.imdb.com/search/title/?keywords=artificial-intelligence&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?keywords=based-on-novel&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?keywords=stephen-king',
  // Rating and decade combos
  'https://www.imdb.com/search/title/?user_rating=8.0,10&sort=user_rating,desc',
  'https://www.imdb.com/search/title/?release_date=2020-01-01,2025-12-31&sort=user_rating,desc',
  // Black-and-white filter
  'https://www.imdb.com/search/title/?colors=black_and_white&sort=user_rating,desc',
  // Multi-person co-appearance pattern
  'https://www.imdb.com/search/title/?role=nm0000206&role=nm0000158',
  'https://www.imdb.com/search/name/',
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
  // NOTE: We do NOT capture the homepage node here — BFS will visit it from
  // IMDB_SEED_PAGES and build edges from it normally. Capturing it in Phase 0
  // would create a node with no outgoing edges since edge-building only happens
  // inside the BFS loop.
  console.log('[crawler] Phase 0: discovering nav/footer entry points…');
  const navEntryPoints = await discoverNavEntryPoints(page, baseDomain);

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
      // Preserve any pre-assigned ID so edges that already reference this URL
      // continue to point to the correct node.  Only assign a new ID if this
      // URL was never seen as a link target before visiting it.
      if (!urlToNodeId.has(url)) {
        urlToNodeId.set(url, `state_${slug}_${pageIndex}`);
      }
      const nodeId = urlToNodeId.get(url);

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
        // Pre-assign a stable node ID for targets not yet visited.
        // Use a sequential counter so the ID is deterministic and won't conflict
        // with any future pageIndex-based ID (both share the slug prefix but the
        // counter uses a "p" prefix to distinguish them).
        if (!urlToNodeId.has(link)) {
          const targetSlug = urlToSlug(link);
          urlToNodeId.set(link, `state_${targetSlug}_p${urlToNodeId.size}`);
        }

        // Enqueue unvisited BFS links.
        // - Unseen types always get enqueued (bypass page cap) so every structural
        //   type is covered at least once regardless of maxPages.
        // - Already-seen types are capped at MAX_BFS_PAGES_PER_TYPE and respect maxPages.
        if (!visited.has(link) && !queue.includes(link)) {
          const linkType = getPageType(link);
          // Skip BFS-discovered pages for unknown movie/TV titles — they flood the
          // graph with hundreds of upcoming-movie pages that provide no navigation
          // signal. Only title pages for IDs in KNOWN_TITLE_IDS are allowed.
          const linkTtMatch = link.match(/\/title\/(tt\d+)/);
          if (linkTtMatch && !KNOWN_TITLE_IDS.has(linkTtMatch[1])) continue;
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
            // Use the human-readable aria-label if found; fall back to null.
          // '#suggestion-search' is an internal CSS selector — it doesn't belong
          // here as a target_element_id since that field should be a human-readable
          // label (or null) so the recorder and LLM can understand it.
          target_element_id: searchEl ? (searchEl.aria_label || searchEl.text || null) : null,
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
