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
        // Normalize: strip query strings and trailing slashes for deduplication
        const normalized = `${parsed.origin}${parsed.pathname}`.replace(/\/$/, '');
        unique.add(normalized);
      }
    } catch {
      // Malformed href — skip
    }
  }

  return Array.from(unique);
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
  'https://www.imdb.com',
  'https://www.imdb.com/find/?q=inception&s=tt',          // search results
  'https://www.imdb.com/title/tt1375666/',                 // movie page (Inception)
  'https://www.imdb.com/title/tt1375666/fullcredits',      // full cast
  'https://www.imdb.com/title/tt1375666/reviews',          // user reviews
  'https://www.imdb.com/name/nm0634240/',                  // person page (Nolan)
  'https://www.imdb.com/chart/top/',                       // top 250
  'https://www.imdb.com/chart/moviemeter/',                // most popular
  'https://www.imdb.com/watchlist',                        // watchlist
  'https://www.imdb.com/news/movie/',                      // movie news
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

  const visited = new Set();
  // Seed with important IMDB pages first, then fall back to BFS from startUrl
  const seedSet = new Set(IMDB_SEED_PAGES.map(u => u.replace(/\/$/, '')));
  const queue = [...IMDB_SEED_PAGES];
  if (!seedSet.has(startUrl.replace(/\/$/, ''))) queue.push(startUrl);

  // Track source+target pairs to avoid duplicate edges
  const edgeSignatures = new Set();

  let pageIndex = 0;

  let baseDomain;
  try {
    baseDomain = new URL(startUrl).hostname;
  } catch {
    baseDomain = '';
  }

  try {
    while (queue.length > 0 && pageIndex < maxPages) {
      const url = queue.shift();

      if (visited.has(url)) continue;
      visited.add(url);

      console.log(`[crawler] Visiting (${pageIndex + 1}/${maxPages}): ${url}`);

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

        const targetNodeId = urlToNodeId.get(link);

        // Skip duplicate edges (same source → target)
        const edgeSig = `${nodeId}→${targetNodeId}`;
        if (edgeSignatures.has(edgeSig)) continue;
        edgeSignatures.add(edgeSig);

        // Find the element_id of the matching anchor on the current node, if any
        const matchingElement = node.available_elements.find(
          (el) => el.role === 'a' && el.text
        );
        const targetElementId = matchingElement ? matchingElement.element_id : 'link';

        edges.push({
          edge_id: `edge_${uuidv4()}`,
          source_node: nodeId,
          target_node: targetNodeId,
          interaction_type: 'click',
          target_element_id: targetElementId,
        });

        if (!visited.has(link) && !queue.includes(link) && pageIndex + queue.length < maxPages) {
          queue.push(link);
        }
      }

      pageIndex++;
    }
  } finally {
    await browser.close();
  }

  console.log(`[crawler] Crawl complete. Nodes: ${nodes.length}, Edges: ${edges.length}`);

  return { nodes, edges };
}
