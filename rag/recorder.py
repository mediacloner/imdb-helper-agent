import asyncio
import math
import os
import random
import shutil
import uuid
from typing import Any
from urllib.parse import urlparse

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
    """Move the mouse humanly to a locator's center, pause, then click."""
    box = await locator.bounding_box()
    if box:
        tx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
        ty = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
        await _human_move(page, tx, ty)
        await page.wait_for_timeout(pause_ms + random.randint(-80, 80))
    await locator.click()


async def _navigate_via_menu(page: Page, target_url: str) -> bool:
    """
    Reach target_url by clicking through on-page links/menu instead of
    navigating directly. Returns True if navigation succeeded.
    """
    path = urlparse(target_url).path.rstrip("/")

    # Step 1: link already visible on page
    try:
        link = page.locator(f'a[href*="{path}"]').first
        if await link.is_visible(timeout=1500):
            await _move_and_click(page, link, pause_ms=600)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2500)
            return True
    except Exception:
        pass

    # Step 2: open hamburger / Menu button
    for sel in [
        'button[aria-label*="Menu"]',
        '[data-testid*="menu"]',
        'label[for*="sidebar"]',
        '.ipc-responsive-button:has-text("Menu")',
        'span:has-text("Menu")',
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1500):
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

            # Navigate to home — no cookie banner should appear
            await _goto(page, HOME_URL)
            await _human_move(page, 640, 360)
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
                        # Navigate directly with full URL (preserves query params)
                        await _goto(page, url)
                        await _dismiss_cookie_banner(page)
                        actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": "goto_filter"})
                        log_entry("record_step", {
                            "step": i, "description": description,
                            "method": "goto_filter", "success": True,
                        }, duration_ms=now_ms() - t0)

                    elif is_real_search or url:
                        success = await _perform_search(page, target)
                        if not success and url:
                            await _goto(page, url)
                        await _dismiss_cookie_banner(page)
                        actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": "search"})
                        log_entry("record_step", {
                            "step": i, "description": description,
                            "method": "search", "success": success or bool(url),
                        }, duration_ms=now_ms() - t0)

                    else:
                        actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": "skipped_param_no_url"})
                        log_entry("record_step", {
                            "step": i, "description": description,
                            "method": "skipped_param_no_url", "success": False,
                        }, duration_ms=now_ms() - t0)

                elif interaction == "click" and target and not target.startswith("state_"):
                    clicked = False
                    method_used = None
                    # Build list of locator strategies: text match first, then CSS
                    is_css = target.startswith(("#", ".", "[", ">")) or " " not in target.strip()
                    locator_attempts = []
                    if not is_css:
                        locator_attempts += [
                            ("get_by_text", page.get_by_text(target, exact=False).first),
                            ("a:has-text", page.locator(f"a:has-text('{target}')").first),
                        ]
                    locator_attempts.append(("css", page.locator(target).first))
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
                    if not clicked:
                        if url:
                            navigated = await _navigate_via_menu(page, url)
                            if not navigated:
                                await _goto(page, url)
                                method_used = "goto_fallback"
                            else:
                                method_used = "menu_fallback"
                    actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": method_used or "click_failed"})
                    log_entry("record_step", {
                        "step": i, "description": description,
                        "method": method_used or "click_failed", "success": clicked or bool(url),
                    }, duration_ms=now_ms() - t0)

                elif url:
                    # "navigate" interaction type means go directly to the URL.
                    # _navigate_via_menu uses only the path component and can match
                    # the wrong link (e.g. /search/title/ matches podcast pages).
                    # Only use menu navigation as a fallback for non-navigate steps.
                    if interaction == "navigate" or "?" in url:
                        await _goto(page, url)
                        method = "goto_filter" if "?" in url else "goto"
                    else:
                        navigated = await _navigate_via_menu(page, url)
                        if not navigated:
                            await _goto(page, url)
                            method = "goto"
                        else:
                            method = "menu_link"
                    actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": method})
                    log_entry("record_step", {
                        "step": i, "description": description,
                        "method": method, "success": True,
                    }, duration_ms=now_ms() - t0)

                else:
                    actual_steps.append({"step": i, "actual_url": page.url, "actual_title": await page.title(), "method": "skipped"})
                    log_entry("record_step", {
                        "step": i, "description": description,
                        "method": "skipped_no_url_no_target", "success": False,
                    }, duration_ms=now_ms() - t0)

            await page.wait_for_timeout(2500)
            await context.close()
            await browser.close()

        video_files = [f for f in os.listdir(video_dir) if f.endswith(".webm")]
        dest = None
        if video_files:
            dest = os.path.join(VIDEOS_DIR, f"{video_id}.webm")
            shutil.move(os.path.join(video_dir, video_files[0]), dest)
        return {"path": dest, "actual_steps": actual_steps}

    finally:
        shutil.rmtree(video_dir, ignore_errors=True)
