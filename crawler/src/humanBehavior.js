/**
 * humanBehavior.js
 * Utilities to simulate human-like browser interactions to reduce bot detection.
 */

/**
 * Returns a Promise that resolves after a random delay between min and max milliseconds.
 * @param {number} min - Minimum delay in milliseconds.
 * @param {number} max - Maximum delay in milliseconds.
 * @returns {Promise<void>}
 */
export function randomDelay(min, max) {
  const delay = Math.floor(Math.random() * (max - min + 1)) + min;
  return new Promise((resolve) => setTimeout(resolve, delay));
}

/**
 * Types text into a page element character by character with random delays between keystrokes.
 * @param {import('playwright').Page} page - Playwright page object.
 * @param {string} selector - CSS selector for the target input element.
 * @param {string} text - Text to type.
 * @returns {Promise<void>}
 */
export async function humanType(page, selector, text) {
  await page.click(selector);
  for (const char of text) {
    await page.keyboard.type(char);
    await randomDelay(40, 160);
  }
}

/**
 * Returns a randomly chosen realistic desktop browser user-agent string.
 * @returns {string}
 */
export function getRandomUserAgent() {
  const userAgents = [
    // Chrome 124 on Windows 11
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    // Chrome 124 on macOS Sonoma
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    // Firefox 125 on Windows 11
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    // Safari 17 on macOS Sonoma
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
    // Edge 124 on Windows 11
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
  ];

  return userAgents[Math.floor(Math.random() * userAgents.length)];
}
