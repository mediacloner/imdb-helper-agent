import asyncio
import math
import os
import random
import re
import shutil
import uuid
from typing import Any
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, Page, BrowserContext
from request_logger import log_entry, now_ms

VIDEOS_DIR = "/app/videos"
HOME_URL = "https://www.imdb.com"

# Inject a larger SVG arrow cursor + click ripple effect.
_CURSOR_SCRIPT = """
(() => {
    const SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24">
        <polygon points="2,2 2,20 7,15 11,22 13,21 9,14 16,14"
            fill="white" stroke="black" stroke-width="1.4" stroke-linejoin="round"/>
    </svg>`;

    const RIPPLE_CSS =
        '@keyframes pw-ripple {' +
        '  0%   { transform: translate(-50%,-50%) scale(0); opacity: 0.85; }' +
        '  60%  { transform: translate(-50%,-50%) scale(1);  opacity: 0.5; }' +
        '  100% { transform: translate(-50%,-50%) scale(1.4); opacity: 0; }' +
        '}' +
        '.pw-ripple {' +
        '  position: fixed;' +
        '  width: 72px; height: 72px;' +
        '  border-radius: 50%;' +
        '  background: radial-gradient(circle, rgba(255,220,50,0.55) 0%, rgba(80,160,255,0.35) 60%, transparent 100%);' +
        '  border: 3px solid rgba(255,220,50,0.9);' +
        '  pointer-events: none;' +
        '  z-index: 2147483646;' +
        '  animation: pw-ripple 0.55s ease-out forwards;' +
        '}';

    function spawnRipple(x, y) {
        const r = document.createElement('div');
        r.className = 'pw-ripple';
        r.style.left = x + 'px';
        r.style.top  = y + 'px';
        document.body.appendChild(r);
        setTimeout(function() { r.remove(); }, 480);
    }

    function inject() {
        if (document.getElementById('pw-cursor')) return;

        const style = document.createElement('style');
        style.textContent =
            '* { cursor: none !important; }' +
            '#pw-cursor {' +
            '  position: fixed;' +
            '  left: 640px; top: 360px;' +
            '  width: 36px; height: 36px;' +
            '  pointer-events: none;' +
            '  z-index: 2147483647;' +
            '  filter: drop-shadow(1px 2px 3px rgba(0,0,0,0.75));' +
            '}' +
            RIPPLE_CSS;
        document.head.appendChild(style);

        const el = document.createElement('div');
        el.id = 'pw-cursor';
        el.innerHTML = SVG;
        document.body.appendChild(el);

        document.addEventListener('mousemove', function(e) {
            el.style.left = e.clientX + 'px';
            el.style.top  = e.clientY + 'px';
        }, { passive: true });

        document.addEventListener('mousedown', function(e) {
            spawnRipple(e.clientX, e.clientY);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
"""


async def _human_move(page: Page, x: float, y: float) -> None:
    """
    Move the mouse from its current position to (x, y) along a slightly curved
    path with eased speed, simulating human hand movement.
    """
    # Get current mouse position via JS (stored on window by previous moves)
    pos = await page.evaluate("() => ({ x: window._pwX || 640, y: window._pwY || 360 })")
    x0, y0 = pos["x"], pos["y"]

    dist = math.hypot(x - x0, y - y0)
    if dist < 2:
        return

    # Number of steps scales with distance; more steps = smoother
    steps = max(12, int(dist / 8))
    # Mid-point offset for a slight curve (perpendicular deviation)
    dev = random.uniform(-dist * 0.08, dist * 0.08)
    mx = (x0 + x) / 2 + dev * (y - y0) / (dist + 1)
    my = (y0 + y) / 2 - dev * (x - x0) / (dist + 1)

    for i in range(1, steps + 1):
        t = i / steps
        # Ease in-out
        e = t * t * (3 - 2 * t)
        # Quadratic bezier through mid-point
        bx = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * mx + e ** 2 * x
        by = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * my + e ** 2 * y
        # Small jitter
        bx += random.uniform(-0.6, 0.6)
        by += random.uniform(-0.6, 0.6)
        await page.mouse.move(bx, by)
        await asyncio.sleep(random.uniform(0.003, 0.007))

    # Store final position on window for next call
    await page.evaluate(f"() => {{ window._pwX = {x}; window._pwY = {y}; }}")


async def _move_and_click(page: Page, locator, pause_ms: int = 500) -> None:
    """Scroll the element into view, move the mouse humanly to its center, pause, then click."""
    try:
        await locator.scroll_into_view_if_needed(timeout=2000)
        await page.wait_for_timeout(300)
    except Exception:
        pass
    box = await locator.bounding_box()
    if box:
        tx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
        ty = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
        await _human_move(page, tx, ty)
        await page.wait_for_timeout(pause_ms + random.randint(-80, 80))
    await locator.click()


async def _get_aria_state(page: Page, css_selector: str) -> dict:
    """
    Read live ARIA state attributes of an element from the DOM.
    Returns a dict with aria_expanded / aria_selected / aria_checked as strings
    ("true"/"false") or None when the attribute is absent.
    """
    try:
        return await page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (!el) return {};
                return {
                    aria_expanded: el.getAttribute('aria-expanded'),
                    aria_selected: el.getAttribute('aria-selected'),
                    aria_checked:  el.getAttribute('aria-checked'),
                    is_visible:    el.offsetParent !== null,
                    react_component: (() => {
                        try {
                            const k = Object.keys(el).find(
                                k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
                            );
                            if (!k) return null;
                            let f = el[k];
                            for (let d = 0; d < 15 && f; d++) {
                                const t = f.type;
                                if (t && typeof t === 'function') {
                                    const n = t.displayName || t.name;
                                    if (n && n.length > 2 && !/^(t\d|_|Memo|ForwardRef|Fragment|Provider|Consumer)/.test(n))
                                        return n;
                                }
                                f = f.return;
                            }
                        } catch(_) {}
                        return null;
                    })(),
                };
            }""",
            css_selector,
        )
    except Exception:
        return {}


async def _navigate_via_menu(page: Page, target_url: str, use_hamburger: bool = True) -> bool:
    """
    Reach target_url by clicking through on-page links/menu instead of
    navigating directly. Returns True if navigation succeeded.
    When use_hamburger=False, only tries already-visible links (Step 1) and
    skips opening the hamburger menu — use this for click-failure fallbacks so
    the video never shows the jarring "cursor resets to menu" pattern.
    """
    path = urlparse(target_url).path.rstrip("/")

    # Step 1: link already visible on page (no need to open menu)
    try:
        link = page.locator(f'a[href*="{path}"]').first
        if await link.is_visible(timeout=1500):
            await _move_and_click(page, link, pause_ms=600)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2500)
            return True
    except Exception:
        pass

    if not use_hamburger:
        return False

    # Step 2: open hamburger / Menu button — but only if not already expanded.
    # Using aria-expanded guard prevents double-opens when two consecutive steps
    # both fall back to menu navigation on different pages.
    # Selectors are deliberately specific to avoid matching non-hamburger menus
    # (e.g. data-testid="title-cast-item-menu" or "user-menu-nav").
    _HAMBURGER_SELS = [
        'button[aria-label*="Open Navigation"]',
        'button[aria-label="Menu"]',
        'button[aria-label*="Menu"][aria-expanded]',
        'label[for="imdb-header-responsive-nav-toggle"]',
        'label[for*="sidebar"]',
        '.ipc-responsive-button:has-text("Menu")',
        # Broader fallbacks for IMDb header nav button variants
        '[data-testid="ipc-responsive-button"]',
        'button.ipc-responsive-button',
        'button[class*="nav-toggle"]',
        'button[class*="hamburger"]',
    ]
    for sel in _HAMBURGER_SELS:
        try:
            btn = page.locator(sel).first
            if not await btn.is_visible(timeout=1200):
                continue
            # Guard: skip click if the menu is already expanded
            expanded = await btn.get_attribute('aria-expanded')
            if expanded == 'true':
                break  # already open — go straight to Step 3
            await _move_and_click(page, btn, pause_ms=400)
            await page.wait_for_timeout(700)
            break
        except Exception:
            continue

    # Step 3: link after menu opened
    try:
        link = page.locator(f'a[href*="{path}"]').first
        if await link.is_visible(timeout=2000):
            await _move_and_click(page, link, pause_ms=600)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2500)
            return True
    except Exception:
        pass

    return False


async def _dismiss_cookie_banner(page: Page) -> None:
    """Silently dismiss the IMDb cookie/consent banner if present."""
    for sel in [
        'button[data-testid="accept-button"]',
        'button:has-text("Accept All")',
        'button:has-text("Accept all")',
        'button:has-text("Accept")',
        '[class*="consent"] button',
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                await page.wait_for_timeout(600)
                log_entry("record_cookie_dismissed", {"selector": sel, "phase": "recording"})
                return
        except Exception:
            continue


async def _goto(page: Page, url: str) -> None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500)
        await _dismiss_cookie_banner(page)
        await page.wait_for_timeout(1000)
    except Exception:
        pass


async def _mouse_wander(page: Page) -> None:
    """Sweep the mouse gently across the content area after a page load.
    Keeps the cursor visibly moving on navigate-only steps where no element
    is clicked (Top 250, chart pages, direct URL navigation, etc.).
    """
    try:
        x1 = random.uniform(200, 640)
        y1 = random.uniform(120, 300)
        x2 = random.uniform(600, 1050)
        y2 = random.uniform(280, 520)
        await _human_move(page, x1, y1)
        await page.wait_for_timeout(random.randint(250, 500))
        await _human_move(page, x2, y2)
        await page.wait_for_timeout(random.randint(150, 350))
    except Exception:
        pass


async def _click_first_find_result(page: Page) -> bool:
    """
    After a search lands on /find/, click the first title result so the recorder
    navigates to the actual movie/show page rather than staying on the find page.
    Only called when the next step needs a specific title page.
    """
    if "/find" not in page.url:
        return False
    for sel in [
        # Modern IMDb (2024-2025) data-testid patterns
        '[data-testid="find-result-item"] a[href*="/title/"]',
        '[data-testid="find-title-result"] a[href*="/title/"]',
        'section[data-testid^="find-results"] a[href*="/title/"]',
        # IPC component class patterns
        'li.ipc-metadata-list-summary-item a[href*="/title/tt"]',
        '.ipc-metadata-list-summary-item a[href*="/title/"]',
        '.ipc-metadata-list-summary-item__t',
        # Legacy patterns
        'a.result_text',
        'td.result_text a',
        # Broad fallback: first anchor pointing to any title page on the /find/ page
        'a[href^="/title/tt"]',
    ]:
        try:
            link = page.locator(sel).first
            if await link.is_visible(timeout=4000):
                await _move_and_click(page, link, pause_ms=500)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


async def _perform_search(page: Page, search_term: str) -> bool:
    """Type a search term into the IMDb search bar and submit."""
    for sel in ["#suggestion-search", 'input[type="search"]', 'input[placeholder*="Search"]']:
        try:
            inp = page.locator(sel).first
            if not await inp.is_visible(timeout=3000):
                continue
            await _move_and_click(page, inp, pause_ms=300)
            await page.keyboard.press("Control+a")
            await page.wait_for_timeout(150)
            for char in search_term:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.13))
            await page.wait_for_timeout(700)
            # Click submit button
            try:
                btn = page.locator("#suggestion-search-button").first
                if await btn.is_visible(timeout=1000):
                    await _move_and_click(page, btn, pause_ms=300)
                else:
                    await page.keyboard.press("Enter")
            except Exception:
                await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2500)
            return True
        except Exception:
            continue
    return False


async def _ensure_accordion_open(page: Page, accordion_testid: str) -> None:
    """
    Open an IMDb filter accordion if it is currently collapsed.
    Targets the button[aria-expanded] child of the accordion item so the click
    lands on the actual toggle, not the outer container. Skips the click when
    aria-expanded is already "true" (avoids collapsing an already-open panel).
    """
    # The clickable toggle is the button (or element with aria-expanded) inside the item
    header_sel = f'[data-testid="{accordion_testid}"] [aria-expanded]'
    try:
        header = page.locator(header_sel).first
        if not await header.is_visible(timeout=3000):
            return
        # Read live state from DOM — "false" or absent means collapsed
        state = await _get_aria_state(page, header_sel)
        if state.get("aria_expanded") == "true":
            return  # already open, touching it would close it
        await _move_and_click(page, header, pause_ms=400)
        await page.wait_for_timeout(600)
        # Verify it actually opened
        state_after = await _get_aria_state(page, header_sel)
        if state_after.get("aria_expanded") != "true":
            # One retry — some accordions need a moment before responding
            await page.wait_for_timeout(300)
            await _move_and_click(page, header, pause_ms=400)
            await page.wait_for_timeout(600)
    except Exception:
        pass


async def _apply_search_filters(page: Page, filter_url: str) -> list[dict]:
    """
    Navigate to /search/title/ and apply filters by interacting with the UI accordions
    (clicking headers, selecting genre chips, filling year fields, then clicking See results).
    Falls back to _goto(filter_url) if UI interaction fails or no recognised params found.

    Returns a list of sub-step dicts that callers should extend into actual_steps so the
    judge can see each individual UI interaction rather than one opaque 'filter_ui' entry.
    """
    sub_steps: list[dict] = []

    async def _rec(method: str) -> None:
        sub_steps.append({
            "actual_url": page.url,
            "actual_title": await page.title(),
            "method": method,
        })

    parsed = urlparse(filter_url)
    params = parse_qs(parsed.query)

    # Navigate to the base search page first so the filter panel is visible
    await _goto(page, "https://www.imdb.com/search/title/")
    await page.wait_for_timeout(800)
    await _rec("opened_advanced_search")

    applied_any = False

    # URL param values differ from IMDb's chip data-testid values.
    _TITLE_TYPE_CHIP = {
        "feature":       "movie",
        "tv_series":     "tvSeries",
        "tv_miniseries": "tvMiniSeries",
        "tv_movie":      "tvMovie",
        "short":         "short",
        "tv_episode":    "tvEpisode",
        "tv_special":    "tvSpecial",
        "documentary":   "documentary",
        "video":         "video",
        "video_game":    "videoGame",
    }

    try:
        # ── Genres ──────────────────────────────────────────────────────────
        genres_param = params.get("genres", [])
        if genres_param:
            genre_list = [g.strip() for g in genres_param[0].split(",") if g.strip()]
            if genre_list:
                await _ensure_accordion_open(page, "accordion-item-genreAccordion")
                await _rec("expanded_genre_filter")
                for genre in genre_list:
                    # Capitalise first letter; handle Sci-Fi / Film-Noir special cases
                    if genre.lower() == "sci-fi":
                        chip_id = "Sci-Fi"
                    elif genre.lower() == "film-noir":
                        chip_id = "Film-Noir"
                    else:
                        chip_id = genre.capitalize()
                    chip = page.locator(f'[data-testid="test-chip-id-{chip_id}"]').first
                    try:
                        if await chip.is_visible(timeout=2000):
                            chip_state = await _get_aria_state(
                                page, f'[data-testid="test-chip-id-{chip_id}"]'
                            )
                            if chip_state.get("aria_selected") != "true":
                                await _move_and_click(page, chip, pause_ms=400)
                                await page.wait_for_timeout(400)
                            applied_any = True
                            await _rec(f"selected_{genre.lower()}_genre")
                    except Exception:
                        pass

        # ── Release date ─────────────────────────────────────────────────────
        release_param = params.get("release_date", [])
        if release_param:
            date_str = release_param[0]
            parts = date_str.split(",")
            from_year = parts[0][:4] if parts and parts[0] else ""
            to_year = parts[1][:4] if len(parts) > 1 and parts[1] else ""
            if from_year or to_year:
                await _ensure_accordion_open(page, "accordion-item-releaseDateAccordion")
                await _rec("expanded_release_date_filter")
                inputs = page.locator('[data-testid="accordion-item-releaseDateAccordion"] input')
                if from_year:
                    try:
                        inp = inputs.first
                        if await inp.is_visible(timeout=2000):
                            await _move_and_click(page, inp, pause_ms=300)
                            await page.keyboard.press("Control+a")
                            for ch in from_year:
                                await page.keyboard.type(ch)
                                await asyncio.sleep(0.06)
                            await page.wait_for_timeout(300)
                            applied_any = True
                            await _rec(f"entered_year_from_{from_year}")
                    except Exception:
                        pass
                if to_year:
                    try:
                        inp = inputs.nth(1)
                        if await inp.is_visible(timeout=2000):
                            await _move_and_click(page, inp, pause_ms=300)
                            await page.keyboard.press("Control+a")
                            for ch in to_year:
                                await page.keyboard.type(ch)
                                await asyncio.sleep(0.06)
                            await page.wait_for_timeout(300)
                            applied_any = True
                            await _rec(f"entered_year_to_{to_year}")
                    except Exception:
                        pass

        # ── User rating ───────────────────────────────────────────────────────
        rating_param = params.get("user_rating", [])
        if rating_param:
            parts = rating_param[0].split(",")
            min_r = parts[0].strip() if parts else ""
            max_r = parts[1].strip() if len(parts) > 1 else ""
            if min_r or max_r:
                await _ensure_accordion_open(page, "accordion-item-ratingsAccordion")
                await _rec("expanded_ratings_filter")
                inputs = page.locator('[data-testid="accordion-item-ratingsAccordion"] input')
                if min_r:
                    try:
                        inp = inputs.first
                        if await inp.is_visible(timeout=2000):
                            await _move_and_click(page, inp, pause_ms=300)
                            await page.keyboard.press("Control+a")
                            await page.keyboard.type(min_r)
                            await page.wait_for_timeout(300)
                            applied_any = True
                            await _rec(f"entered_min_rating_{min_r}")
                    except Exception:
                        pass
                if max_r:
                    try:
                        inp = inputs.nth(1)
                        if await inp.is_visible(timeout=2000):
                            await _move_and_click(page, inp, pause_ms=300)
                            await page.keyboard.press("Control+a")
                            await page.keyboard.type(max_r)
                            await page.wait_for_timeout(300)
                            applied_any = True
                            await _rec(f"entered_max_rating_{max_r}")
                    except Exception:
                        pass

        # ── Title type ────────────────────────────────────────────────────────
        type_param = params.get("title_type", [])
        if type_param:
            type_list = [t.strip() for t in type_param[0].split(",") if t.strip()]
            if type_list:
                await _ensure_accordion_open(page, "accordion-item-titleTypeAccordion")
                await _rec("expanded_title_type_filter")
                for ttype in type_list:
                    chip_id = _TITLE_TYPE_CHIP.get(ttype, ttype)
                    chip = page.locator(f'[data-testid="test-chip-id-{chip_id}"]').first
                    try:
                        if await chip.is_visible(timeout=2000):
                            chip_state = await _get_aria_state(
                                page, f'[data-testid="test-chip-id-{chip_id}"]'
                            )
                            if chip_state.get("aria_selected") != "true":
                                await _move_and_click(page, chip, pause_ms=400)
                                await page.wait_for_timeout(400)
                            applied_any = True
                            await _rec(f"selected_{ttype}_type")
                    except Exception:
                        pass

        if applied_any:
            # Click "See results" to submit the filters
            see_results = page.locator('[data-testid="adv-search-get-results"]').first
            try:
                if await see_results.is_visible(timeout=3000):
                    await _move_and_click(page, see_results, pause_ms=600)
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)
                    await _rec("clicked_see_results")
                    # Correction: if the landed URL is missing params (e.g. sort= was
                    # not applied via UI), navigate directly to get the full filter URL.
                    landed = page.url
                    intended_params = set(parse_qs(urlparse(filter_url).query).keys())
                    landed_params = set(parse_qs(urlparse(landed).query).keys())
                    if intended_params - landed_params:
                        await _goto(page, filter_url)
                    await _rec("filter_results_loaded")
                    return sub_steps
            except Exception:
                pass

    except Exception:
        pass

    # Fallback: navigate directly to the final filter URL
    await _goto(page, filter_url)
    await _rec("filter_results_loaded")
    return sub_steps


async def record_navigation(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Record a tutorial video starting from IMDb home page.
    Returns {"path": str|None, "actual_steps": [{step, actual_url, method}]}
    so callers can compare intended vs actual URLs for judge evaluation.
    """
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    video_id = uuid.uuid4().hex
    video_dir = f"/tmp/pw_video_{video_id}"
    os.makedirs(video_dir, exist_ok=True)
    actual_steps: list[dict] = []

    _BROWSER_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]
    _CONTEXT_OPTS: dict = dict(
        viewport={"width": 1280, "height": 720},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=_BROWSER_ARGS)

            # ── Phase 1: dismiss cookies WITHOUT recording ──────────────────
            # Playwright's storage_state() captures cookies + localStorage
            # per origin — the reliable way to transfer full consent state.
            prep_ctx: BrowserContext = await browser.new_context(**_CONTEXT_OPTS)
            prep_page = await prep_ctx.new_page()
            await _goto(prep_page, HOME_URL)
            dismissed = False
            for sel in [
                'button[data-testid="accept-button"]',
                'button:has-text("Accept All")',
                'button:has-text("Accept all")',
                'button:has-text("Accept")',
            ]:
                try:
                    btn = prep_page.locator(sel).first
                    if await btn.is_visible(timeout=4000):
                        await btn.click()
                        await prep_page.wait_for_timeout(1000)
                        dismissed = True
                        log_entry("record_cookie", {"selector": sel, "dismissed": True})
                        break
                except Exception:
                    continue
            if not dismissed:
                log_entry("record_cookie", {"dismissed": False})
            await prep_page.wait_for_timeout(800)
            # Capture full storage state (cookies + localStorage per origin)
            storage = await prep_ctx.storage_state()
            await prep_ctx.close()

            # ── Phase 2: recording starts with consent already applied ──────
            context: BrowserContext = await browser.new_context(
                **_CONTEXT_OPTS,
                storage_state=storage,
                record_video_dir=video_dir,
                record_video_size={"width": 1280, "height": 720},
            )
            await context.add_init_script(_CURSOR_SCRIPT)
            page = await context.new_page()

            # Navigate to home — no cookie banner should appear.
            # No cursor movement here: the first real step will move the cursor
            # purposefully toward its target.
            await _goto(page, HOME_URL)
            await page.wait_for_timeout(800)

            # Navigate each step, dispatching on interaction_type
            for i, step in enumerate(steps):
                url = step.get("url", "") or ""
                action = step.get("action") or {}
                interaction = action.get("interaction_type")
                target = action.get("target_element_id") or ""
                description = step.get("description", f"Step {i + 1}")
                t0 = now_ms()

                if url == HOME_URL:
                    log_entry("record_step", {"step": i, "description": description, "skipped": "home_url"})
                    continue

                # Strip placeholder URLs that contain template tokens like <user_id>
                if url and ("<" in url or ">" in url):
                    log_entry("record_step", {"step": i, "description": description, "skipped": "placeholder_url"})
                    url = ""

                log_entry("record_step_start", {
                    "step": i, "description": description,
                    "interaction": interaction, "target": target, "url": url,
                })

                if interaction == "search_query" and target:
                    # Distinguish between:
                    #   - Filter URL   → URL has query params (not /find/) → goto URL directly
                    #                    Do NOT use _navigate_via_menu — it strips query params
                    #   - Real search  → target has spaces or starts uppercase → type in search bar
                    #   - Param value  → target like "short","feature","runtime,asc", no URL → skip
                    is_filter_url = url and "?" in url and "/find" not in url
                    is_real_search = " " in target or (target and target[0].isupper())

                    if is_filter_url:
                        if "/search/title/" in url:
                            sub = await _apply_search_filters(page, url)
                            for s in sub:
                                s["step"] = i
                            actual_steps.extend(sub)
                            method_str = "filter_ui"
                        else:
                            await _goto(page, url)
                            await _dismiss_cookie_banner(page)
                            method_str = "navigated"
                            actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": method_str})
                        log_entry("record_step", {
                            "step": i, "description": description,
                            "method": method_str, "success": True,
                        }, duration_ms=now_ms() - t0)

                    elif is_real_search or url:
                        success = await _perform_search(page, target)
                        if not success and url:
                            await _goto(page, url)
                        await _dismiss_cookie_banner(page)
                        actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": "searched"})
                        log_entry("record_step", {
                            "step": i, "description": description,
                            "method": "searched", "success": success or bool(url),
                        }, duration_ms=now_ms() - t0)

                    else:
                        # Pure parameter step (no URL, no real navigation) — skip trace entry
                        log_entry("record_step", {
                            "step": i, "description": description,
                            "method": "skipped_param_no_url", "success": False,
                        }, duration_ms=now_ms() - t0)

                elif interaction == "click" and target and not target.startswith("state_"):
                    clicked = False
                    method_used = None
                    # If we're stuck on a /find/ results page, clicking the first title
                    # result is almost always the right move — do it before other attempts.
                    if "/find" in page.url:
                        if await _click_first_find_result(page):
                            clicked = True
                            method_used = "clicked_search_result"
                    # Build list of locator strategies: text match first, then CSS.
                    # Only treat target as a CSS selector when it starts with a CSS
                    # sigil (#, ., [, >).  Single-word labels like "Trivia" or "Awards"
                    # are text targets, not selectors — the old " " check caused them to
                    # skip the text-match path and fail silently.
                    is_css = target.startswith(("#", ".", "[", ">"))
                    locator_attempts = []
                    if not clicked:
                        if not is_css:
                            locator_attempts += [
                                ("clicked", page.get_by_text(target, exact=False).first),
                                ("clicked", page.locator(f"a:has-text('{target}')").first),
                            ]
                        locator_attempts.append(("clicked", page.locator(target).first))
                    for strategy, locator in locator_attempts:
                        try:
                            if await locator.is_visible(timeout=2000):
                                await _move_and_click(page, locator, pause_ms=500)
                                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                                await page.wait_for_timeout(1500)
                                await _dismiss_cookie_banner(page)
                                await page.wait_for_timeout(1000)
                                clicked = True
                                method_used = strategy
                                break
                        except Exception:
                            continue
                    filter_sub_steps: list[dict] = []
                    if not clicked:
                        if url:
                            if "?" in url:
                                # Filter URL — never use _navigate_via_menu here.
                                # Its path-only href match (a[href*="/search/title"]) hits any
                                # /search/title link in the menu, most visibly podcast_series.
                                if "/search/title/" in url:
                                    filter_sub_steps = await _apply_search_filters(page, url)
                                    method_used = "applied_search_filters"
                                else:
                                    await _goto(page, url)
                                    method_used = "navigated"
                            else:
                                # Failed click: try via menu (including hamburger) so the video
                                # shows the cursor navigating through the menu rather than the
                                # page just jumping to the destination silently.
                                nav_ok = await _navigate_via_menu(page, url, use_hamburger=True)
                                if not nav_ok:
                                    await _goto(page, url)
                                    method_used = "navigated"
                                else:
                                    method_used = "clicked_link"
                        else:
                            # No URL fallback — but if the target smells like a title subpage
                            # (e.g. "User reviews", "Trivia", "Awards") and the recorder is
                            # already on an IMDb title page, derive the URL from the live
                            # page.url so we can still navigate (e.g. Amelie's /reviews/).
                            _cur = page.url
                            _tt_m = re.search(r"/title/(tt\d+)", _cur)
                            _SUBPAGE_KEYWORDS = {
                                "user reviews": "/reviews/",
                                "reviews": "/reviews/",
                                "trivia": "/trivia/",
                                "awards": "/awards/",
                                "episodes": "/episodes/",
                                "full cast": "/fullcredits/",
                                "cast": "/fullcredits/",
                                "crew": "/fullcredits/",
                                "goofs": "/trivia/?tab=gf",
                                "quotes": "/trivia/?tab=qt",
                                "soundtrack": "/soundtrack/",
                                "filming locations": "/locations/",
                                "parents guide": "/parentalguide/",
                            }
                            _tgt_lower = target.lower()
                            _derived_suffix = next(
                                (sfx for kw, sfx in _SUBPAGE_KEYWORDS.items() if kw in _tgt_lower), None
                            )
                            if _tt_m and _derived_suffix:
                                _derived_url = f"https://www.imdb.com/title/{_tt_m.group(1)}{_derived_suffix}"
                                nav_ok = await _navigate_via_menu(page, _derived_url, use_hamburger=False)
                                if not nav_ok:
                                    await _goto(page, _derived_url)
                                method_used = "navigated"
                                url = _derived_url  # so the step is logged
                    if filter_sub_steps:
                        for s in filter_sub_steps:
                            s["step"] = i
                        actual_steps.extend(filter_sub_steps)
                    elif url or clicked:
                        actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": method_used or "navigated"})
                    log_entry("record_step", {
                        "step": i, "description": description,
                        "method": method_used or "navigated", "success": clicked or bool(url),
                    }, duration_ms=now_ms() - t0)

                elif url:
                    if interaction == "navigate" or "?" in url:
                        # navigate steps and filter URLs: go directly — avoids _navigate_via_menu
                        # matching wrong links (e.g. podcast pages that contain "search/title"
                        # in their href) and preserves query params on filter URLs.
                        is_search_filter = "?" in url and "/search/title/" in url
                        if is_search_filter:
                            sub = await _apply_search_filters(page, url)
                            for s in sub:
                                s["step"] = i
                            actual_steps.extend(sub)
                            method = "applied_search_filters"
                        else:
                            await _goto(page, url)
                            method = "navigated"
                            actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": method})
                    else:
                        # click steps with only a fallback URL: try clicking on-page link first
                        # so the video shows mouse movement; fall back to goto.
                        # use_hamburger=False avoids the jarring "cursor resets to menu" pattern.
                        nav_ok = await _navigate_via_menu(page, url, use_hamburger=False)
                        if not nav_ok:
                            await _goto(page, url)
                            method = "navigated"
                        else:
                            method = "clicked_link"
                        actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": method})
                    log_entry("record_step", {
                        "step": i, "description": description,
                        "method": method, "success": True,
                    }, duration_ms=now_ms() - t0)

                else:
                    # No URL and no actionable target — skip trace entry entirely
                    # (adds noise with no useful URL for the judge to evaluate)
                    log_entry("record_step", {
                        "step": i, "description": description,
                        "method": "skipped_no_url_no_target", "success": False,
                    }, duration_ms=now_ms() - t0)

            # Final pause — give the viewer time to see the last state
            await page.wait_for_timeout(2500)
            await context.close()
            await browser.close()

        video_files = [f for f in os.listdir(video_dir) if f.endswith(".webm")]
        dest = None
        if video_files:
            raw = os.path.join(video_dir, video_files[0])
            # Convert to MP4 (H.264 + AAC) with -movflags +faststart so the moov
            # atom is at the front of the file.  This gives reliable seek support in
            # all browsers without needing HTTP range requests to the end of the file.
            # WebM with Cues-at-end (Playwright default) breaks seeking in Chrome.
            dest_mp4 = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")
            try:
                import subprocess
                result = subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", raw,
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                        "-c:a", "aac", "-b:a", "96k",
                        "-movflags", "+faststart",
                        dest_mp4,
                    ],
                    capture_output=True, timeout=120,
                )
                if result.returncode == 0:
                    dest = dest_mp4
                else:
                    # ffmpeg encode failed — fall back to WebM remux (at least adds Cues)
                    dest_webm = os.path.join(VIDEOS_DIR, f"{video_id}.webm")
                    tmp = dest_webm + ".tmp.webm"
                    r2 = subprocess.run(
                        ["ffmpeg", "-y", "-i", raw, "-c", "copy", tmp],
                        capture_output=True, timeout=60,
                    )
                    if r2.returncode == 0:
                        os.replace(tmp, dest_webm)
                    else:
                        shutil.move(raw, dest_webm)
                    dest = dest_webm
            except Exception:
                dest_webm = os.path.join(VIDEOS_DIR, f"{video_id}.webm")
                shutil.move(raw, dest_webm)
                dest = dest_webm
        return {"path": dest, "actual_steps": actual_steps}

    finally:
        shutil.rmtree(video_dir, ignore_errors=True)
